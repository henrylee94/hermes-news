#!/usr/bin/env python3
"""
Hermes News — RSS Fetcher (no LLM)
Fetches RSS feeds + live market data, outputs raw candidates as JSON.
The agent (mimo) does the LLM work.
"""
import json, os, re, sys, time, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser
import httpx

# ── Config ──
MYT = timezone(timedelta(hours=8), "MYT")
HTTP_TIMEOUT = 15
MAX_WORKERS = 8
CATEGORIES = ["us_stocks", "my_stocks", "ai", "macro"]

BASE_DIR = Path(os.environ.get("HERMES_WORKSPACE", os.path.expanduser("~/geewoni-workspace")))
VAULT_DIR = BASE_DIR / "vault"
CONFIG_DIR = Path(os.environ.get("NEWS_CONFIG_DIR", VAULT_DIR / "Config"))
CACHE_DIR = BASE_DIR / "data" / "hermes" / "news_cache"
NEWS_DIR = Path(os.environ.get("NEWS_OUTPUT_DIR", VAULT_DIR / "News"))

# ── Finnhub (optional) ──
_finnhub = None
try:
    import finnhub as _finnhub_mod
    env_file = Path.home() / ".hermes" / "firecrawl.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("FINNHUB_API_KEY="):
                key = line.split("=", 1)[1].strip()
                if key:
                    _finnhub = _finnhub_mod.Client(api_key=key)
                    break
except ImportError:
    pass

# ── KLSE ticker map ──
KLSE_TICKER_MAP = {
    "MAYBANK": "1155.KL", "CIMB": "1023.KL", "PBBANK": "1295.KL",
    "RHBBANK": "1066.KL", "HLBANK": "5819.KL", "TENAGA": "5347.KL",
    "GENTING": "3182.KL", "KLK": "2445.KL", "IOICORP": "1961.KL",
    "SIMEPROP": "5288.KL", "YTL": "4677.KL", "OCK": "0172.KL",
    "OSK": "5053.KL", "KUALA": "5858.KL"
}
_KLSE_SKIP = {'2605','DFJSP','RULER','FBMKLCI','FBM','KLSE','CNBC','CIMB','MAYBANK',
              'ACL','CCT','CORS','LLM','ML','SVG','TDRC','URIEL','URL','FMT','OCK'}

# ── Base watchlists ──
BASE_TICKERS = {
    "us_stocks": ["NVDA","INTC","PLTR","SOFI","BMNR","MU","RKLB","OKLO","MSFT","AAPL","GOOGL","AMZN","META","TSLA","AMD","AVGO"],
    "my_stocks": list(KLSE_TICKER_MAP.values()),
    "ai": ["NVDA","AMD","MSFT","GOOGL","META","AMZN","AVGO","ARM","CRWD","PLTR"],
    "macro": [],
}

# ── Helpers ──
def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

def _is_within_24h(pub_date):
    if pub_date is None:
        return True
    return pub_date.replace(tzinfo=timezone.utc) > (
        datetime.now(MYT) - timedelta(hours=24)
    ).replace(tzinfo=MYT)

def _load_sources():
    """Load RSS sources from Reliable-Sources-Reference.md + supplements."""
    sources_ref = CONFIG_DIR / "Reliable-Sources-Reference.md"
    if not (CONFIG_DIR / "sources.md").exists() and not sources_ref.exists():
        return _default_sources()

    ref_path = sources_ref if sources_ref.exists() else CONFIG_DIR / "sources.md"
    text = ref_path.read_text(encoding="utf-8")
    cat_map = {"美股": "us_stocks", "马": "my_stocks", "AI": "ai", "人工智能": "ai"}
    sources = []
    current_cat = None
    name = None

    for line in text.splitlines():
        if line.startswith("# "):
            for kw, cat in cat_map.items():
                if kw in line:
                    current_cat = cat
                    break
            else:
                if "宏观" in line or "Macro" in line:
                    current_cat = "macro"
            continue
        if line.startswith("## "):
            m = re.search(r'\*\*(.+?)\*\*', line)
            name = m.group(1) if m else line[3:].strip().split("**")[0]
            continue
        m = re.search(r'RSS:\s*`?(https?://[^\s`]+)', line)
        if m and current_cat and name:
            url = m.group(1).rstrip('`')
            if 'headline?s=' in url or 'feedx.net' in url:
                continue
            max_e = 30 if current_cat in ("us_stocks", "my_stocks") else 15
            sources.append((name, url, current_cat, "rss", max_e))
            name = None

    # Supplement AI + Macro
    have = {s[1] for s in sources}
    supplement = [
        ("HuggingFace Papers", "https://huggingface.co/papers", "ai", "rss", 10),
        ("Simon Willison", "https://simonwillison.net/atom/everything/", "ai", "rss", 10),
        ("Import AI", "https://jack-clark.net/feed/", "ai", "rss", 10),
        ("Arxiv ML", "https://rss.arxiv.org/rss/cs.AI", "ai", "rss", 10),
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "ai", "rss", 15),
        ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "ai", "rss", 15),
        ("MIT Tech Review", "https://www.technologyreview.com/feed/", "ai", "rss", 10),
        ("The Batch (Andrew Ng)", "https://www.deeplearning.ai/the-batch/feed/", "ai", "rss", 10),
        ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "macro", "rss", 20),
        ("FT World", "https://www.ft.com/rss/world", "macro", "rss", 20),
        ("WSJ World", "https://feeds.a.dj.com/rss/RSSWorldNews.xml", "macro", "rss", 20),
        ("CNBC Politics", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000113", "macro", "rss", 20),
    ]
    for s in supplement:
        if s[1] not in have:
            sources.append(s)
    return sources or _default_sources()

def _default_sources():
    return [
        ("WSJ Markets", "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "us_stocks", "rss", 30),
        ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain", "us_stocks", "rss", 20),
        ("FMT Business", "https://www.freemalaysiatoday.com/category/business/feed/", "my_stocks", "rss", 30),
        ("Simon Willison", "https://simonwillison.net/atom/everything/", "ai", "rss", 10),
        ("Arxiv ML", "https://rss.arxiv.org/rss/cs.AI", "ai", "rss", 10),
        ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "macro", "rss", 20),
        ("FT World", "https://www.ft.com/rss/world", "macro", "rss", 20),
    ]

def _parse_rss(name, url, category, mx=50):
    stories = []
    for entry in feedparser.parse(url).entries:
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        if not _is_within_24h(pub_date):
            continue
        link = entry.get("link", "")
        stories.append({
            "title": entry.get("title", "").strip(),
            "url": link, "source": name, "source_url": link,
            "category": category,
            "summary": entry.get("summary", "")[:500],
            "published": str(pub_date) if pub_date else ""
        })
    return stories

def _deduplicate(stories):
    from rapidfuzz import fuzz
    seen_urls, seen_titles, deduped = set(), [], []
    for s in stories:
        h = _url_hash(s["url"])
        if h in seen_urls:
            continue
        if any(fuzz.ratio(s["title"].lower(), t.lower()) >= 85 for t in seen_titles):
            continue
        seen_urls.add(h)
        seen_titles.append(s["title"])
        deduped.append(s)
    return deduped

def extract_tickers(text):
    us = re.findall(r'\b[A-Z]{2,5}\b', text)
    stop = {"THE","FOR","AND","NOT","YOU","ARE","ITS","HAS","WAS","HOW","WHY","WHO","WHAT",
            "THIS","THAT","WITH","FROM","YOUR","HAVE","WERE","BEEN","MORE","SOME","NEWS",
            "INC","ETF","CEO","CFO","IPO","AI","IT","IS","IN","ON","AT","TO","OF","BY",
            "BE","OR","AS","AN","DO","GO","NO","UP","DOWN","OUT","OFF","BIG","TOP","GET",
            "SET","MAY","JAN","FEB","MAR","APR","JUN","JUL","AUG","SEP","OCT","NOV","DEC",
            "USD","MYR","SGD","LTD","BHD","Q1","Q2","Q3","Q4","BUY","SELL","LOW","HIGH",
            "VIA","PER","ALL","OLD","DJI","IXIC","NYSE","NASDAQ","KLSE","FBMKLCI","FBM"}
    return sorted(set(t for t in us if t not in stop))

def _merge_tickers(items, category):
    text = " ".join(f"{s.get('title','')} {s.get('summary','')} {s.get('source','')}" for s in items)
    dynamic = extract_tickers(text)
    return sorted(set(BASE_TICKERS.get(category, []) + dynamic))

# ── Live market data ──
def fetch_live_data(items, category):
    tickers = _merge_tickers(items, category)
    tickers = [KLSE_TICKER_MAP.get(t, t) for t in tickers]
    live = {}
    now = datetime.now(MYT)

    us_tickers = [t for t in tickers if not t.endswith('.KL') and t not in _KLSE_SKIP]
    klse_tickers = [t for t in tickers if t.endswith('.KL')]

    if _finnhub and us_tickers:
        for t in us_tickers:
            try:
                q = _finnhub.quote(t)
                if q and q.get('c') and q['c'] > 0:
                    live[t] = {"price": q['c'], "change_pct": round(q.get('dp', 0), 2),
                               "prev_close": q.get('pc'), "open": q.get('o'),
                               "high": q.get('h'), "low": q.get('l'),
                               "_source": "finnhub", "_fetched_at": now.isoformat()}
            except Exception:
                pass

    if klse_tickers:
        try:
            import yfinance as yf
            for t in klse_tickers:
                try:
                    info = yf.Ticker(t).info or {}
                    if info.get('regularMarketPrice') is not None:
                        live[t] = {"price": info.get("regularMarketPrice"),
                                   "change_pct": info.get("regularMarketChangePercent"),
                                   "_source": "yfinance", "_fetched_at": now.isoformat()}
                except Exception:
                    pass
        except ImportError:
            pass

    return live

# ── Main ──
def collect(date_str=None):
    now = datetime.now(MYT)
    date_str = date_str or now.strftime("%Y-%m-%d")

    print(f"[{now.strftime('%H:%M')}] Fetching RSS feeds...", file=sys.stderr)
    sources = _load_sources()
    collected = {c: [] for c in CATEGORIES}

    def do_fetch(name, url, cat, typ, mx):
        try:
            stories = _parse_rss(name, url, cat, mx)
            return cat, stories[:mx]
        except Exception as e:
            print(f"  [{name}] failed: {e}", file=sys.stderr)
            return cat, []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futs = [pool.submit(do_fetch, *s) for s in sources]
        for fut in as_completed(futs):
            cat, stories = fut.result()
            collected[cat].extend(stories)

    for c in collected:
        collected[c] = _deduplicate(collected[c])
        print(f"  {c}: {len(collected[c])} candidates", file=sys.stderr)

    # Fetch live market data per category
    print(f"  Fetching live market data...", file=sys.stderr)
    live_data = {}
    for cat in CATEGORIES:
        if collected[cat]:
            live_data[cat] = fetch_live_data(collected[cat], cat)

    # Cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{date_str}.json"
    output = {"date": date_str, "collected": collected, "live_data": live_data}
    json.dump(output, open(cache_path, "w"), indent=2, ensure_ascii=False, default=str)

    # Also stdout
    print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
    print(f"  Cached to {cache_path}", file=sys.stderr)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Fetch RSS + live data (no LLM)")
    p.add_argument("--date", default=None, help="Override date YYYY-MM-DD")
    args = p.parse_args()
    collect(args.date)
