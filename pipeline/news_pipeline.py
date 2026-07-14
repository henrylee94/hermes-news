#!/usr/bin/env python3
"""
Hermes Daily News Pipeline v2
=============================
5-Layer architecture: Collect -> Rank -> Detail -> Render -> Deliver
4 categories: us_stocks, my_stocks, ai, macro

Usage:
    pip install -r requirements.txt
    export OPENROUTER_API_KEY=sk-...
    python pipeline/news_pipeline.py daily
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser
import httpx
from rapidfuzz import fuzz

# Finnhub (optional, for live market data)
try:
    import finnhub as _finnhub_mod
except ImportError:
    _finnhub_mod = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("news_pipeline")

BASE_DIR = Path(os.environ.get("HERMES_WORKSPACE", os.path.expanduser("~/geewoni-workspace")))
DATA_DIR = BASE_DIR / "data" / "hermes"
VAULT_DIR = BASE_DIR / "vault"
CONFIG_DIR = Path(os.environ.get("NEWS_CONFIG_DIR", VAULT_DIR / "Config"))
NEWS_DIR = Path(os.environ.get("NEWS_OUTPUT_DIR", VAULT_DIR / "News"))
CACHE_DIR = DATA_DIR / "news_cache"
MYT = timezone(timedelta(hours=8), "MYT")

def _daily_base(date_str: str) -> Path:
    """NEWS_DIR/YYYY/MM/DD base path (no extension) for a YYYY-MM-DD string."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return NEWS_DIR / dt.strftime("%Y") / dt.strftime("%m") / dt.strftime("%d")

def _scan_daily_dates() -> list[str]:
    """Scan year/month dirs and return sorted YYYY-MM-DD strings."""
    dates = []
    for year_dir in sorted(NEWS_DIR.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue
            for f in month_dir.glob("*.json"):
                dd = f.stem  # e.g. "15"
                try:
                    date_str = f"{year_dir.name}-{month_dir.name}-{dd.zfill(2)}"
                    datetime.strptime(date_str, "%Y-%m-%d")
                    dates.append(date_str)
                except ValueError:
                    pass
    return sorted(dates, reverse=True)

# ── Source Reference ──
SOURCES_REF = CONFIG_DIR / "Reliable-Sources-Reference.md"

def _load_sources_from_ref() -> list:
    """Load RSS sources from the Reliable-Sources-Reference.md file.
    Supplements AI/Macro categories since the ref file lacks RSS for those."""
    sources = []
    if SOURCES_REF.exists():
        text = SOURCES_REF.read_text(encoding="utf-8")
        cat_map = {"美股": "us_stocks", "马": "my_stocks", "AI": "ai", "人工智能": "ai"}
        current_cat = None
        name = None
        for line in text.splitlines():
            if line.startswith("# "):
                for kw, cat in cat_map.items():
                    if kw in line:
                        current_cat = cat; break
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
        log.info(f"Loaded {len(sources)} RSS sources from {SOURCES_REF.name}")
    else:
        log.warning(f"Source ref not found: {SOURCES_REF}")

    # Supplement AI + Macro (reference file has no RSS for these)
    have = {s[1] for s in sources}
    supplement = [
        # AI — reference file sources are mostly newsletters/web, add RSS equivalents
        ("HuggingFace Papers", "https://huggingface.co/papers", "ai", "rss", 10),
        ("Simon Willison", "https://simonwillison.net/atom/everything/", "ai", "rss", 10),
        ("Import AI", "https://jack-clark.net/feed/", "ai", "rss", 10),
        ("Arxiv ML", "https://rss.arxiv.org/rss/cs.AI", "ai", "rss", 10),
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "ai", "rss", 15),
        ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "ai", "rss", 15),
        ("MIT Tech Review", "https://www.technologyreview.com/feed/", "ai", "rss", 10),
        ("The Batch (Andrew Ng)", "https://www.deeplearning.ai/the-batch/feed/", "ai", "rss", 10),
        # Macro — not in reference file at all
        ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "macro", "rss", 20),
        ("FT World", "https://www.ft.com/rss/world", "macro", "rss", 20),
        ("WSJ World", "https://feeds.a.dj.com/rss/RSSWorldNews.xml", "macro", "rss", 20),
        ("CNBC Politics", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000113", "macro", "rss", 20),
    ]
    for s in supplement:
        if s[1] not in have:
            sources.append(s)
    log.info(f"Total sources: {len(sources)} (ref + supplement)")
    return sources or SOURCES_DEFAULT

# Hardcoded fallback
SOURCES_DEFAULT = [
    # US stocks — WSJ/MarketWatch only, Yahoo/CNBC/Reuters broken (2026-07)
    ("WSJ Markets", "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "us_stocks", "rss", 30),
    ("WSJ US Business", "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", "us_stocks", "rss", 20),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain", "us_stocks", "rss", 20),
    ("Google News US Stocks", "https://news.google.com/rss/search?q=US+stock+market+OR+S%26P+500+OR+Nasdaq&hl=en-US&gl=US&ceid=US:en", "us_stocks", "rss", 20),
    # MY stocks — Edge/Star Biz RSS dead, FMT + Google News only (2026-07)
    ("FMT Business", "https://www.freemalaysiatoday.com/category/business/feed/", "my_stocks", "rss", 30),
    ("Google News MY Stocks", "https://news.google.com/rss/search?q=Bursa+Malaysia+OR+KLCI+OR+malaysia+stock&hl=en-MY&gl=MY&ceid=MY:en", "my_stocks", "rss", 20),
    ("HuggingFace Papers", "https://huggingface.co/papers", "ai", "rss", 10),
    ("Simon Willison", "https://simonwillison.net/atom/everything/", "ai", "rss", 10),
    ("Import AI", "https://jack-clark.net/feed/", "ai", "rss", 10),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "macro", "rss", 20),
    ("FT World", "https://www.ft.com/rss/world", "macro", "rss", 20),
]

SOURCES = _load_sources_from_ref()

# ── Finnhub Client ──
def _init_finnhub():
    if not _finnhub_mod: return None
    env_file = Path.home() / ".hermes" / "firecrawl.env"
    if not env_file.exists(): return None
    for line in env_file.read_text().splitlines():
        if line.startswith("FINNHUB_API_KEY="):
            key = line.split("=", 1)[1].strip()
            if key: return _finnhub_mod.Client(api_key=key)
    return None

_finnhub = _init_finnhub()

HTTP_TIMEOUT = 15
MAX_WORKERS = 8
CATEGORIES = ["us_stocks", "my_stocks", "ai", "macro"]

OPENROUTER_BASE = os.environ.get("LLM_API_BASE", "https://openrouter.ai/api/v1")
RANK_MODEL = os.environ.get("LLM_MODEL", "deepseek/deepseek-v4-flash")
DETAIL_MODEL = os.environ.get("LLM_MODEL", "deepseek/deepseek-v4-flash")
RANK_MAX_INPUT = 8000
RANK_MAX_OUTPUT = 4000
DETAIL_MAX_INPUT = 10000
DETAIL_MAX_OUTPUT = 6000
COST_PER_INPUT_TOKEN = 0.20 / 1_000_000
COST_PER_OUTPUT_TOKEN = 0.40 / 1_000_000

_stats = {"llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0}

# KLSE ticker map: Bursa Malaysia needs .KL suffix for yfinance
KLSE_TICKER_MAP = {
    "MAYBANK": "1155.KL", "CIMB": "1023.KL", "PBBANK": "1295.KL",
    "RHBBANK": "1066.KL", "HLBANK": "5819.KL", "TENAGA": "5347.KL",
    "GENTING": "3182.KL", "KLK": "2445.KL", "IOICORP": "1961.KL",
    "SIMEPROP": "5288.KL", "YTL": "4677.KL", "OCK": "0172.KL",
    "OSK": "5053.KL", "KUALA": "5858.KL"
}

# Non-tradable identifiers to skip in live data fetch
_KLSE_SKIP = {'2605','DFJSP','RULER','FBMKLCI','FBM','KLSE','CNBC','CIMB','MAYBANK',
              'PBBANK','RHBBANK','GENTING','IOICORP','SIMEPROP','TENAGA','HLBANK',
              'HLIB','YTL','KUALA','NST','RHB','2022','2025','2026','2027',
              'ACL','CCT','CORS','LLM','ML','SVG','TDRC','URIEL','URL','FMT','OCK'}

def _load_openrouter_key() -> str:
    key = os.environ.get("LLM_API_KEY", os.environ.get("OPENROUTER_API_KEY", ""))
    if key: return key
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for line in open(env_path):
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY") and not line.startswith("#"):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("OPENROUTER_API_KEY not found (set env var or add to ~/.hermes/.env)")

def _load_telegram_token() -> tuple[str, int]:
    config_path = Path.home() / ".hermes" / "config.yaml"
    token = None
    chat_id = None
    for line in open(config_path):
        line = line.strip()
        if line.startswith("token:"):
            val = line.split(":", 1)[1].strip().strip('"').strip("'")
            if val and val != "***": token = val
        if line.startswith("- ") and chat_id is None:
            try: chat_id = int(line.strip().lstrip("- "))
            except: pass
    return token, chat_id or REDACTED

def _get_tailscale_host() -> str:
    config_path = Path.home() / ".hermes" / "config.yaml"
    try:
        for line in open(config_path):
            if "tailscale_host" in line and ":" in line:
                val = line.split(":", 1)[1].strip().strip('"').strip("'")
                if val: return val
    except: pass
    return "localhost"

def _llm_call(system: str, user: str, model: str, max_input: int, max_output: int) -> tuple[str, dict]:
    api_key = _load_openrouter_key()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
               "HTTP-Referer": "https://geewoni-news.local", "X-Title": "Hermes News Pipeline"}
    if len(user) > max_input * 4:
        user = user[: max_input * 4]
    payload = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
               "max_tokens": max_output, "temperature": 0.1}
    for attempt in range(2):
        try:
            resp = httpx.post(f"{OPENROUTER_BASE}/chat/completions", headers=headers, json=payload, timeout=120)
            if resp.status_code != 200: raise RuntimeError(f"API {resp.status_code}")
            data = resp.json()
            content = data["choices"][0]["message"]["content"] or ""
            usage = data.get("usage", {})
            in_tok, out_tok = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
            _stats["llm_calls"] += 1; _stats["input_tokens"] += in_tok; _stats["output_tokens"] += out_tok
            _stats["cost"] += in_tok * COST_PER_INPUT_TOKEN + out_tok * COST_PER_OUTPUT_TOKEN
            return content, {"input_tokens": in_tok, "output_tokens": out_tok}
        except Exception as e:
            if attempt == 0: time.sleep(2)
            else: raise RuntimeError(f"LLM call failed: {e}")
    raise RuntimeError("LLM call failed")

def _json_extract(text: str) -> str | None:
    if not text or not text.strip(): return None
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"): raw = raw[:-3].strip()
    start = -1
    for ch, pos in (("[", raw.find("[")), ("{", raw.find("{"))):
        if pos >= 0 and (start < 0 or pos < start): start = pos
    if start < 0: return None
    raw = raw[start:]
    fixed, in_str, esc = [], False, False
    for ch in raw:
        if esc: fixed.append(ch); esc = False; continue
        if ch == "\\": fixed.append(ch); esc = True; continue
        if ch == '"' and not esc: in_str = not in_str; fixed.append(ch); continue
        if in_str and ch == "\n": fixed.append("\\n"); continue
        if in_str and ch == "\r": continue
        fixed.append(ch)
    s = "".join(fixed)
    closer = "]" if s.startswith("[") else "}"
    opener = "[" if s.startswith("[") else "{"
    depth = trunc = 0
    for i, ch in enumerate(s):
        if ch == opener: depth += 1
        elif ch == closer: depth -= 1
        if depth == 0: trunc = i + 1; break
    if trunc > 0: s = s[:trunc]
    if depth > 0: s += closer * depth
    try: json.loads(s); return s
    except: return None

def _date_24h_ago() -> datetime: return datetime.now(MYT) - timedelta(hours=24)
def _is_within_24h(pub_date: datetime | None) -> bool:
    if pub_date is None: return True
    return pub_date.replace(tzinfo=timezone.utc) > _date_24h_ago().replace(tzinfo=MYT)
def _url_hash(url: str) -> str: return hashlib.md5(url.encode()).hexdigest()

def extract_tickers(text: str) -> list[str]:
    us = re.findall(r'\b[A-Z]{2,5}\b', text)
    stop = {"THE","FOR","AND","NOT","YOU","ARE","ITS","HAS","WAS","HOW","WHY","WHO","WHAT",
            "THIS","THAT","WITH","FROM","YOUR","HAVE","WERE","BEEN","MORE","SOME","NEWS",
            "INC","ETF","CEO","CFO","IPO","AI","IT","IS","IN","ON","AT","TO","OF","BY",
            "BE","OR","AS","AN","DO","GO","NO","UP","DOWN","OUT","OFF","BIG","TOP","GET",
            "SET","MAY","JAN","FEB","MAR","APR","JUN","JUL","AUG","SEP","OCT","NOV","DEC",
            "USD","MYR","SGD","LTD","BHD","Q1","Q2","Q3","Q4","BUY","SELL","LOW","HIGH",
            "VIA","PER","ALL","OLD","DJI","IXIC","NYSE","NASDAQ","KLSE","FBMKLCI","FBM"}
    return sorted(set(t for t in us if t not in stop))

def _merge_ticker_lists(items: list, category: str) -> list[str]:
    base_map = {
        "us_stocks": ["NVDA","INTC","PLTR","SOFI","BMNR","MU","RKLB","OKLO","MSFT","AAPL","GOOGL","AMZN","META","TSLA","AMD","AVGO"],
        "my_stocks": list(KLSE_TICKER_MAP.values()),
        "ai": ["NVDA","AMD","MSFT","GOOGL","META","AMZN","AVGO","ARM","CRWD","PLTR"],
        "macro": [],
    }
    text = " ".join(f"{s.get('title','')} {s.get('summary','')} {s.get('source','')}" for s in items)
    dynamic = extract_tickers(text)
    return sorted(set(base_map.get(category,[]) + dynamic))

# =====================================================================
# Layer 1
# =====================================================================
def layer1_collect(date_str: str) -> dict:
    cache_path = CACHE_DIR / f"{date_str}.json"
    if cache_path.exists():
        try: return json.load(open(cache_path))
        except: log.warning("Cache corrupt")
    collected = {c: [] for c in CATEGORIES}
    def fetch(name, url, cat, typ, mx):
        try:
            s = _parse_rss(name, url, cat, mx) if typ == "rss" else _parse_html(name, url, cat)
            return cat, s[:mx]
        except Exception as e:
            log.warning(f"[{name}] fetch failed: {e}")
            return cat, []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for fut in as_completed([pool.submit(fetch, *s) for s in SOURCES]):
            cat, s = fut.result(); collected[cat].extend(s)
    for c in collected: collected[c] = _deduplicate(collected[c])
    for c, items in collected.items(): log.info(f"  {c}: {len(items)} candidates")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    json.dump(collected, open(cache_path, "w"), indent=2, ensure_ascii=False, default=str)
    return collected

def _parse_rss(name: str, url: str, category: str, mx: int = 50) -> list:
    stories = []
    for entry in feedparser.parse(url).entries:
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        if not _is_within_24h(pub_date): continue
        link = entry.get("link", "")
        stories.append({"title": entry.get("title", "").strip(), "url": link, "source": name,
                        "source_url": link, "category": category,
                        "summary": entry.get("summary", "")[:500],
                        "published": str(pub_date) if pub_date else ""})
    return stories

def _parse_html(name, url, cat) -> list:
    stories = []
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = httpx.get(url, headers=headers, timeout=HTTP_TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    import selectolax
    tree = selectolax.parser.HTMLParser(resp.text)
    for a in tree.css("a[href]"):
        href = a.attributes.get("href","")
        if not href or href.startswith("#") or href.startswith("javascript:"): continue
        title = a.text(strip=True)
        if len(title) < 20: continue
        fu = href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/")
        stories.append({"title": title, "url": fu, "source": name, "source_url": fu,
                        "category": cat, "summary": "", "published": ""})
    return stories

def _deduplicate(stories):
    seen_urls, seen_titles, deduped = set(), [], []
    for s in stories:
        if _url_hash(s["url"]) in seen_urls: continue
        if any(fuzz.ratio(s["title"].lower(), t.lower()) >= 85 for t in seen_titles): continue
        seen_urls.add(_url_hash(s["url"])); seen_titles.append(s["title"]); deduped.append(s)
    return deduped

# =====================================================================
# Layer 2 - Concurrent (P1 + P4)
# =====================================================================
def layer2_rank(candidates: dict) -> dict:
    ranked = {c: [] for c in CATEGORIES}

    def _rank_one(cat):
        items = candidates.get(cat, [])
        if not items: return cat, []
        # P4: pre-filter to 30 most recent
        if len(items) > 30:
            items = sorted(items, key=lambda x: x.get("published", ""), reverse=True)[:30]
        system = _build_rank_system(cat)
        prompt = _build_rank_prompt(cat, items)
        try:
            result_json, meta = _llm_call(system, prompt, RANK_MODEL, RANK_MAX_INPUT, RANK_MAX_OUTPUT)
            return cat, _parse_rank_result(result_json, items)
        except Exception as e:
            log.warning(f"{cat}: rank failed ({e}), using pub time fallback")
            return cat, sorted(items, key=lambda x: x.get("published", ""), reverse=True)[:10]

    with ThreadPoolExecutor(max_workers=4) as pool:
        for cat, result in pool.map(_rank_one, CATEGORIES):
            ranked[cat] = result
            log.info(f"  {cat}: ranked {len(result)} stories")
    return ranked

def _build_rank_system(cat):
    ctx = {"us_stocks": "Henry holds INTC 200@$130, PLTR 100@$141, SOFI 250@$23.20, BMNR 100@$50. Watchlist: NVDA, MU, RKLB, OKLO.",
           "my_stocks": "KLSE investor. Bursa Malaysia stocks, MY macro.",
           "ai": "AI infrastructure, models, tooling, research.",
           "macro": "Macro economics: Fed/BNM rates, CPI/PCE, geopolitics, MYR/USD."}
    return f"You rank news for Henry (KL investor).\n{ctx.get(cat,'')}\nScore 0-10: portfolio relevance, macro impact, signal density, recency.\nReturn JSON array: [{{\"index\":i,\"score\":N,\"reason\":\"reason\"}}] No markdown."

def _build_rank_prompt(cat, items):
    return f"Score these {cat} stories:\n\n" + "\n".join(f"[{i}] {s['title']} | {s['source']}" for i, s in enumerate(items))

def _parse_rank_result(raw, all_items):
    parsed = _json_extract(raw)
    if parsed is None: return all_items[:10]
    try: scores = json.loads(parsed)
    except: return all_items[:10]
    if not isinstance(scores, list): return all_items[:10]
    scores.sort(key=lambda x: x.get("score",0), reverse=True)
    result = []
    for entry in scores[:10]:
        idx = entry.get("index",0)
        if isinstance(idx, int) and idx < len(all_items):
            s = dict(all_items[idx]); s["score"] = entry.get("score",0); s["reason"] = entry.get("reason","")
            result.append(s)
    return result or all_items[:10]

# =====================================================================
# Layer 3 - Concurrent (P1)
# =====================================================================
def layer3_detail(ranked: dict, skip_live_data: bool = False) -> dict:
    results = {c: [] for c in CATEGORIES}

    def _detail_one(cat):
        items = ranked.get(cat, [])
        if not items: return cat, []
        if skip_live_data:
            live_data = {s: {"_skipped": True} for s in _merge_ticker_lists(items, cat)}
        else:
            live_data = _fetch_live_data(items, cat)
        try:
            detail_json, meta = _llm_generate_details(cat, items, live_data)
            parsed = _parse_detail_result(detail_json, items, cat)
        except Exception as e:
            log.warning(f"{cat}: detail failed ({e}), degraded")
            parsed = _degraded_detail(items, cat, live_data)
        for s in parsed: s["_warnings"] = []
        return cat, parsed

    with ThreadPoolExecutor(max_workers=4) as pool:
        for cat, stories in pool.map(_detail_one, CATEGORIES):
            results[cat] = stories
            log.info(f"  {cat}: {len(stories)} stories detailed")
    return results

def _fetch_live_data(items: list, category: str) -> dict:
    tickers = _merge_ticker_lists(items, category)
    tickers = [KLSE_TICKER_MAP.get(t, t) for t in tickers]
    live = {}
    now = datetime.now(MYT)

    # Separate US vs KLSE tickers
    us_tickers = [t for t in tickers if not t.endswith('.KL') and t not in _KLSE_SKIP]
    klse_tickers = [t for t in tickers if t.endswith('.KL')]

    # Finnhub for US stocks (fast, 60 calls/min free tier)
    if _finnhub and us_tickers:
        for t in us_tickers:
            try:
                q = _finnhub.quote(t)
                if q and q.get('c') and q['c'] > 0:
                    live[t] = {"price": q['c'], "change_pct": round(q.get('dp', 0), 2),
                               "prev_close": q.get('pc'), "open": q.get('o'),
                               "high": q.get('h'), "low": q.get('l'),
                               "_source": "finnhub", "_fetched_at": now.isoformat()}
                else:
                    live[t] = {"_error": "no data", "_source": "finnhub", "_fetched_at": now.isoformat()}
            except Exception as e:
                live[t] = {"_error": str(e)[:60], "_source": "finnhub", "_fetched_at": now.isoformat()}
        fh_ok = sum(1 for v in live.values() if "_error" not in v and v.get("_source") == "finnhub")
        log.info(f"  Finnhub: {fh_ok}/{len(us_tickers)} US tickers")

    # yfinance for KLSE tickers (Finnhub doesn't support Bursa)
    if klse_tickers:
        import yfinance as yf
        for t in klse_tickers:
            try:
                info = yf.Ticker(t).info or {}
                if info.get('regularMarketPrice') is not None:
                    live[t] = {"price": info.get("regularMarketPrice"), "change_pct": info.get("regularMarketChangePercent"),
                               "volume": info.get("regularMarketVolume"), "market_cap": info.get("marketCap"),
                               "_source": "yfinance", "_fetched_at": now.isoformat()}
                else:
                    live[t] = {"_error": "no data", "_source": "yfinance", "_fetched_at": now.isoformat()}
            except Exception as e:
                live[t] = {"_error": str(e)[:60], "_source": "yfinance", "_fetched_at": now.isoformat()}
        yf_ok = sum(1 for v in live.values() if "_error" not in v and v.get("_source") == "yfinance")
        log.info(f"  yfinance: {yf_ok}/{len(klse_tickers)} KLSE tickers")

    # Fallback: yfinance for US if Finnhub failed or unavailable
    missing_us = [t for t in us_tickers if t not in live or "_error" in live.get(t, {})]
    if missing_us and not _finnhub:
        import yfinance as yf
        for t in missing_us:
            try:
                info = yf.Ticker(t).info or {}
                if info.get('regularMarketPrice') is not None:
                    live[t] = {"price": info.get("regularMarketPrice"), "change_pct": info.get("regularMarketChangePercent"),
                               "volume": info.get("regularMarketVolume"), "market_cap": info.get("marketCap"),
                               "_source": "yfinance", "_fetched_at": now.isoformat()}
            except: pass

    ok = sum(1 for v in live.values() if "_error" not in v)
    log.info(f"  Total: {ok}/{len(tickers)} tickers verified")
    return live

def _llm_generate_details(cat, items, live_data):
    now = datetime.now(MYT)
    ts = now.strftime("%H:%M MYT")
    ds = now.strftime("%Y-%m-%d")
    system = f"""Write Chinese financial summaries.

ABSOLUTE RULES:
1. Use ONLY numbers from <live_data>
2. If not in <live_data> -> write "数据未验证"
3. EACH number MUST have [source @ time] within 80 chars
4. BAD: '[CNBC URL]' '[source]' '[link]' '[URL]' -> FORBIDDEN
5. headline MUST be Chinese <=25 chars
6. data_card.rows only for tickers in headline
7. If story is paper/framework with no ticker -> data_card = null

Return JSON: {{"stories": [{{tag, headline (中文), dek, data_card(or null), body[3], source_url, source_name, timestamp}}]}}
Citation format: [SourceName @ HH:MM MYT] or [Finnhub @ HH:MM MYT] or [yfinance @ HH:MM MYT]
No markdown fences."""  # noqa

    lines = []
    for i, item in enumerate(items[:10]):
        title = item['title'].replace('"',"'").replace("\\","/")
        summary = item.get('summary','N/A')[:200].replace('"',"'")
        lines.append(f"[{i}] Title: {title}\n    Source: {item['source']}\n    Summary: {summary}")
    stext = "\n\n".join(lines)

    ll = []
    for sym, d in sorted(live_data.items()):
        if "_error" in d: ll.append(f"  {sym}: {d.get('_error','ERROR')}")
        elif "_skipped" in d: ll.append(f"  {sym}: NOT FETCHED")
        else: ll.append(f"  {sym}: price={d.get('price','N/A')}, chg={d.get('change_pct','N/A')}, vol={d.get('volume','N/A')}")
    user = f"Date: {ds}\nCategory: {cat}\n<live_data>\n{chr(10).join(ll)}\n</live_data>\n\nDetail these:\n\n{stext}"
    return _llm_call(system, user, DETAIL_MODEL, DETAIL_MAX_INPUT, DETAIL_MAX_OUTPUT)

def _parse_detail_result(raw, items, cat):
    parsed = _json_extract(raw)
    if parsed is None: return _degraded_detail(items, cat, {})
    try: data = json.loads(parsed)
    except: return _degraded_detail(items, cat, {})
    return data.get("stories", []) or _degraded_detail(items, cat, {})

def _degraded_detail(items, cat, _ld):
    tags = {"us_stocks":"📈 个股","my_stocks":"🇲🇾 马股","ai":"🤖 AI","macro":"🌐 宏观"}
    ns = datetime.now(MYT).strftime("%H:%M MYT")
    return [{"tag": tags.get(cat,"📰"), "headline": i["title"][:32],
             "dek":"LLM JSON parse error", "data_card":None,
             "body":[f"From {i['source']}.","Extraction failed.","Source: "+i.get("url","")],
             "source_url":i.get("url",""),"source_name":i.get("source",""),"timestamp":ns,"_degraded":True}
            for i in items[:10]]

def _clean_data_cards(stories: dict) -> dict:
    """Remove data_cards where all values are placeholder/unverified."""
    for cat in stories:
        for s in stories[cat]:
            dc = s.get("data_card")
            if not dc or not isinstance(dc, dict):
                continue
            rows = dc.get("rows", [])
            if not rows:
                s["data_card"] = None; continue
            all_bad = all(
                all(v in ("数据未验证", "N/A", "", None) for k, v in row.items() if k != "ticker")
                for row in rows
            )
            if all_bad:
                s["data_card"] = None
    return stories

def scan_uncited_numbers(stories: dict) -> list:
    warnings = []
    patterns = [r'\$\d+(?:,\d{3})*(?:\.\d{1,2})?', r'(?<![a-zA-Z])\d+(?:\.\d{1,2})%', r'RM\s?\d+(?:,\d{3})*(?:\.\d{1,2})?', r'\d+(?:\.\d{1})?[BMT]\b', r'\d+\.\d{1,2}\s*pt', r'\[.*?URL\]', r'\[source\]', r'\[link\]', r'\[来源\]', r'\[待填\]']
    combined = re.compile('|'.join(patterns))
    for cat, sl in stories.items():
        for s in sl:
            full = ' '.join(s.get('body',[])) + ' ' + json.dumps(s.get('data_card',{}))
            for m in combined.finditer(full):
                if '[' not in full[m.start():m.start()+80]:
                    warnings.append({"category":cat, "headline":s.get('headline','?'), "warning":f"Bad: {m.group()[:40]}"})
    return warnings

# =====================================================================
# Layer 4
# =====================================================================
def layer4_render(stories: dict, date_str: str) -> str:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    tp = CONFIG_DIR / "news-template.html"
    if not tp.exists():
        env = Environment(autoescape=select_autoescape(["html"]))
        template = env.from_string(_inline_fallback_template())
    else:
        env = Environment(loader=FileSystemLoader(str(CONFIG_DIR)), autoescape=select_autoescape(["html"]))
        template = env.get_template("news-template.html")
    now = datetime.now(MYT)
    cat_cfg = [{"key":"us_stocks","icon":"🇺🇸","short":"美股","title":"美股 · US Markets","stories":stories.get("us_stocks",[]),"candidates_count":str(len(stories.get("us_stocks",[])))},
               {"key":"my_stocks","icon":"🇲🇾","short":"马股","title":"马股 · Bursa Malaysia","stories":stories.get("my_stocks",[]),"candidates_count":str(len(stories.get("my_stocks",[])))},
               {"key":"ai","icon":"🤖","short":"AI","title":"AI · 人工智能","stories":stories.get("ai",[]),"candidates_count":str(len(stories.get("ai",[])))},
               {"key":"macro","icon":"🌐","short":"宏观","title":"宏观 · Macro","stories":stories.get("macro",[]),"candidates_count":str(len(stories.get("macro",[])))}]
    available = _scan_daily_dates()
    # v3 template extras
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    wd = ["周一","周二","周三","周四","周五","周六","周日"][dt.weekday()]
    date_short = f"{dt.month}月{dt.day}日 {wd}"
    is_today = (date_str == now.strftime("%Y-%m-%d"))
    ctx = {"date": date_str, "generated_at": now.strftime("%Y-%m-%d %H:%M MYT"),
           "categories": cat_cfg, "total_stories": sum(len(v) for v in stories.values()),
           "total_candidates": sum(len(v) for v in stories.values()),
           "build_hash": hashlib.md5(str(time.time()).encode()).hexdigest()[:4],
           "available_dates": available, "date_short": date_short,
           "max_date": now.strftime("%Y-%m-%d"), "is_today": is_today,
           "weekday": wd, "time": now.strftime("%H:%M"), "user": "Henry"}
    html = template.render(**ctx)
    base = _daily_base(date_str); base.parent.mkdir(parents=True, exist_ok=True)
    open(base.with_suffix(".html"), "w").write(html)
    json.dump(stories, open(base.with_suffix(".json"),"w"), indent=2, ensure_ascii=False, default=str)
    return str(base.with_suffix(".html"))

def _generate_spa():
    """Generate root index.html as a Single-Page App with all dates embedded."""
    all_data = {}
    dates = _scan_daily_dates()
    for d in dates:
        sj = _daily_base(d).with_suffix(".json")
        if sj.exists():
            try:
                all_data[d] = json.load(open(sj))
            except Exception:
                pass
    if not all_data:
        return
    now = datetime.now(MYT)
    today = now.strftime("%Y-%m-%d")
    dates_json = json.dumps(sorted(all_data.keys(), reverse=True))
    cats_json = json.dumps([
        {"key":"us_stocks","icon":"🇺🇸","short":"美股","title":"美股 · US Markets"},
        {"key":"my_stocks","icon":"🇲🇾","short":"马股","title":"马股 · Bursa Malaysia"},
        {"key":"ai","icon":"🤖","short":"AI","title":"AI · 人工智能"},
        {"key":"macro","icon":"🌐","short":"宏观","title":"宏观 · Macro"}
    ], ensure_ascii=False)
    all_json = json.dumps(all_data, ensure_ascii=False, default=str)
    spa_html = _SPA_TEMPLATE.replace("__ALL_DATA__", all_json).replace("__DATES__", dates_json).replace("__CATS__", cats_json).replace("__TODAY__", today)
    out = NEWS_DIR / "index.html"
    open(out, "w").write(spa_html)
    log.info(f"SPA index: {out} ({len(dates)} dates)")

_SPA_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#ffffff">
<title>Hermes Daily</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700;900&family=Noto+Serif+SC:wght@700;900&display=swap" rel="stylesheet">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  :root{--bg:#fff;--ink:#1d1d1f;--ink-soft:#424245;--ink-light:#86868b;--divider:#d2d2d7;--accent-red:#c8102e;--accent-blue:#0066cc;--accent-amber:#d97706;--accent-green:#00855b;--card-bg:#fafafa;--nav-bg:rgba(255,255,255,.85)}
  @media(prefers-color-scheme:dark){:root{--bg:#1a1a1c;--ink:#f5f5f7;--ink-soft:#c7c7cc;--ink-light:#8e8e93;--divider:#38383a;--card-bg:#2c2c2e;--nav-bg:rgba(26,26,28,.85)}}
  html{-webkit-text-size-adjust:100%}
  body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--ink);line-height:1.5;-webkit-font-smoothing:antialiased;overflow-x:hidden}
  .wrap{max-width:720px;margin:0 auto;padding:0 24px}
  .topbar{position:sticky;top:0;z-index:100;background:var(--nav-bg);backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px);border-bottom:1px solid var(--divider)}
  .topbar-inner{max-width:720px;margin:0 auto;padding:11px 24px;display:flex;align-items:center;justify-content:space-between}
  .brand{font-family:'Playfair Display',serif;font-size:20px;font-weight:900;letter-spacing:-.5px}
  .date-picker{display:flex;align-items:center;gap:8px}
  .date-picker button{background:none;border:none;color:var(--ink-light);font-size:20px;cursor:pointer;padding:0 2px;line-height:1}
  .date-picker button:hover{color:var(--accent-blue)}
  .date-picker button:disabled{opacity:.25;cursor:default}
  .date-display{position:relative;font-size:13px;font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums;cursor:pointer;padding:5px 10px;border-radius:8px;background:var(--card-bg);display:flex;align-items:center;gap:6px}
  .date-display:hover{color:var(--accent-blue)}
  .date-display input[type="date"]{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}
  .date-display .cal-icon{font-size:12px}
  .tabs{position:sticky;top:47px;z-index:99;background:var(--nav-bg);backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px);border-bottom:1px solid var(--divider)}
  .tabs-inner{max-width:720px;margin:0 auto;padding:0 12px;display:flex;gap:2px;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none}
  .tabs-inner::-webkit-scrollbar{display:none}
  .tab{flex:1 0 auto;min-width:72px;text-align:center;padding:13px 14px;font-size:14px;font-weight:600;color:var(--ink-light);border-bottom:2.5px solid transparent;cursor:pointer;white-space:nowrap;transition:color .15s,border-color .15s;background:none;font-family:inherit}
  .tab.active{color:var(--ink)}
  .tab[data-cat="us_stocks"].active{border-bottom-color:var(--accent-red)}
  .tab[data-cat="my_stocks"].active{border-bottom-color:var(--accent-amber)}
  .tab[data-cat="ai"].active{border-bottom-color:var(--accent-blue)}
  .tab[data-cat="macro"].active{border-bottom-color:var(--accent-green)}
  .tab .count{display:inline-block;min-width:18px;padding:1px 5px;margin-left:3px;font-size:11px;font-weight:600;border-radius:9px;background:var(--card-bg);color:var(--ink-light)}
  .tab.active .count{background:var(--ink);color:var(--bg)}
  .masthead{padding:28px 0 4px}
  .masthead-title{font-family:'Playfair Display','Noto Serif SC',serif;font-size:44px;font-weight:900;letter-spacing:-1px;line-height:1}
  .masthead-sub{font-size:12px;color:var(--ink-light);margin-top:8px;text-transform:uppercase;letter-spacing:1.2px}
  .panel{display:none}.panel.active{display:block;animation:fade .25s ease}
  @keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
  .panel-head{margin:32px 0 22px;padding-bottom:12px;border-bottom:1px solid var(--divider);display:flex;align-items:baseline;justify-content:space-between}
  .panel-title{font-family:'Playfair Display','Noto Serif SC',serif;font-size:26px;font-weight:700}
  .panel-count{font-size:11px;color:var(--ink-light);text-transform:uppercase;letter-spacing:1.2px}
  .story{margin-bottom:40px;padding-bottom:40px;border-bottom:1px solid var(--divider)}
  .story:last-child{border-bottom:none}
  .story-meta{display:flex;gap:10px;align-items:center;font-size:11px;color:var(--ink-light);text-transform:uppercase;letter-spacing:1.1px;margin-bottom:11px}
  .story-meta .dot{color:var(--divider)}
  .tag-us_stocks{color:var(--accent-red);font-weight:600}
  .tag-my_stocks{color:var(--accent-amber);font-weight:600}
  .tag-ai{color:var(--accent-blue);font-weight:600}
  .tag-macro{color:var(--accent-green);font-weight:600}
  .story-headline{font-family:'Playfair Display','Noto Serif SC',serif;font-size:28px;font-weight:700;line-height:1.2;letter-spacing:-.3px;margin-bottom:10px}
  .story.lead .story-headline{font-size:34px}
  .story-dek{font-size:16px;color:var(--ink-soft);line-height:1.55;margin-bottom:16px}
  .story-hero{width:100%;height:210px;border-radius:8px;margin-bottom:16px;display:flex;align-items:center;justify-content:center;color:var(--ink-light);font-size:11px;letter-spacing:1px;text-transform:uppercase;overflow:hidden;background:linear-gradient(135deg,#f5f5f7,#e8e8ed 50%,#d8d8df)}
  .story-hero img{width:100%;height:100%;object-fit:cover}
  .data-card{background:var(--card-bg);border-left:3px solid var(--accent-red);padding:13px 17px;margin:16px 0;border-radius:0 6px 6px 0}
  .data-card.my_stocks{border-left-color:var(--accent-amber)}.data-card.ai{border-left-color:var(--accent-blue)}.data-card.macro{border-left-color:var(--accent-green)}
  .data-card-label{font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:var(--ink-light);margin-bottom:7px}
  .data-row{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;font-size:14px}
  .data-row .num{font-weight:600;font-variant-numeric:tabular-nums}
  .data-row .up{color:var(--accent-red)}.data-row .down{color:#00a35c}
  .data-citation{font-size:10px;color:var(--ink-light);margin-top:7px;font-style:italic}
  .story-body p{font-size:15px;line-height:1.65;margin-bottom:13px}
  .story-body p:first-of-type::first-letter{font-family:'Playfair Display',serif;font-size:36px;font-weight:900;line-height:1;color:var(--accent-red);padding-right:2px}
  .story-warning{background:#fff3cd;border-left:3px solid #d97706;padding:11px 15px;margin:14px 0;color:#856404;font-size:13px;border-radius:0 4px 4px 0}
  @media(prefers-color-scheme:dark){.story-warning{background:#3a2e10;color:#fde68a}}
  .story-source{margin-top:18px;padding-top:13px;border-top:1px dotted var(--divider);font-size:12px;color:var(--ink-light);display:flex;justify-content:space-between;align-items:center}
  .source-pill{display:inline-flex;align-items:center;padding:4px 12px;background:var(--card-bg);border-radius:12px;font-weight:500;color:var(--ink-soft);text-decoration:none;min-height:30px}
  .empty{padding:60px 20px;text-align:center;color:var(--ink-light);font-size:14px}
  .doc-footer{margin:48px 0 60px;padding-top:28px;border-top:2px solid var(--ink);text-align:center;font-size:11px;color:var(--ink-light);letter-spacing:1.5px;text-transform:uppercase}
  .nav-hint{font-size:11px;color:var(--ink-light);text-align:center;padding:8px 0;display:none}
  .no-data-hint{padding:40px;text-align:center;color:var(--ink-light);font-size:14px;border:1px dashed var(--divider);border-radius:8px;margin:20px 0}
  @media(max-width:640px){
    .wrap{padding:0 18px}.topbar-inner{padding-left:18px;padding-right:18px}
    .brand{font-size:17px}.date-display{font-size:12px}
    .masthead-title{font-size:32px}.tab{font-size:13px;padding:12px 12px;min-width:64px}
    .story-headline{font-size:23px}.story.lead .story-headline{font-size:27px}
    .story-hero{height:170px}
  }
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-inner">
    <span class="brand">Hermes Daily</span>
    <div class="date-picker">
      <button id="prevDay" title="前一天">‹</button>
      <label class="date-display">
        <span class="cal-icon">📅</span>
        <span id="dateText"></span>
        <input type="date" id="datePick" max="__TODAY__">
      </label>
      <button id="nextDay" title="后一天">›</button>
    </div>
  </div>
</div>

<div class="tabs">
  <div class="tabs-inner" id="tabsContainer"></div>
</div>

<div class="wrap">
  <header class="masthead">
    <div class="masthead-title">Hermes Daily</div>
    <div class="masthead-sub" id="mastheadSub"></div>
  </header>
  <div id="panelsContainer"></div>
  <footer class="doc-footer" id="docFooter"></footer>
</div>

<script>
const ALL_DATA = __ALL_DATA__;
const DATES = __DATES__;
const CATS = __CATS__;
const TODAY = "__TODAY__";
const weekdays = ['周日','周一','周二','周三','周四','周五','周六'];

let curDate = DATES[0];

function fmt(d){
  const dt=new Date(d+'T00:00:00');
  return (dt.getMonth()+1)+'月'+dt.getDate()+'日 '+weekdays[dt.getDay()];
}
function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}

// Build tabs
const tabsEl = document.getElementById('tabsContainer');
CATS.forEach(cat => {
  const btn = document.createElement('button');
  btn.className = 'tab'; btn.dataset.cat = cat.key;
  btn.innerHTML = cat.icon + ' ' + cat.short + '<span class="count">0</span>';
  btn.onclick = () => { switchTab(cat.key); window.scrollTo({top:0}); };
  tabsEl.appendChild(btn);
});

// Build panels
const panelsEl = document.getElementById('panelsContainer');
CATS.forEach(cat => {
  const div = document.createElement('div');
  div.className = 'panel'; div.dataset.cat = cat.key;
  div.innerHTML = `<div class="panel-head"><div class="panel-title">${cat.title}</div><div class="panel-count">0 stories</div></div><div class="stories-container"></div>`;
  panelsEl.appendChild(div);
});

function renderStories(catKey, stories){
  const panel = document.querySelector(`.panel[data-cat="${catKey}"]`);
  const container = panel.querySelector('.stories-container');
  panel.querySelector('.panel-count').textContent = stories.length + ' stories';
  if(!stories.length){
    const short = CATS.find(c=>c.key===catKey).short;
    container.innerHTML = `<div class="empty">暂无 ${short} 新闻</div>`;
    return;
  }
  container.innerHTML = stories.map((s,i) => {
    let h = `<article class="story ${i===0?'lead':''}">`;
    h += `<div class="story-meta"><span class="tag-${catKey}">${esc(s.tag)}</span><span class="dot">·</span><span>${esc(s.source_name)}</span></div>`;
    h += `<h2 class="story-headline">${esc(s.headline)}</h2>`;
    h += `<p class="story-dek">${esc(s.dek)}</p>`;
    if(s.hero_image_url) h += `<div class="story-hero"><img src="${esc(s.hero_image_url)}" alt="" loading="lazy"></div>`;
    if(s.data_card){
      h += `<div class="data-card ${catKey}"><div class="data-card-label">${esc(s.data_card.label||'DATA')}</div>`;
      (s.data_card.rows||[]).forEach(r=>{h+=`<div class="data-row"><span>${esc(r.label||r.ticker||'')}</span><span class="num ${r.color||''}">${esc(r.value||String(r.price||''))}</span></div>`;});
      h += `<div class="data-citation">${esc(s.data_card.citation||'')}</div></div>`;
    }
    if(s._warnings&&s._warnings.length) h += `<div class="story-warning">⚠️ ${s._warnings.map(esc).join(' · ')}</div>`;
    h += `<div class="story-body">${(s.body||[]).map(p=>'<p>'+esc(p)+'</p>').join('')}</div>`;
    h += `<div class="story-source"><a href="${esc(s.source_url)}" class="source-pill" target="_blank" rel="noopener">${esc(s.source_name||'')} →</a></div>`;
    h += `</article>`; return h;
  }).join('');
}

function renderDate(date){
  curDate = date;
  const data = ALL_DATA[date];
  document.getElementById('datePick').value = date;
  document.getElementById('dateText').textContent = fmt(date);
  document.getElementById('mastheadSub').textContent = date + ' · For Henry';
  document.getElementById('docFooter').textContent = 'Hermes Daily · ' + date;

  // Nav buttons: use DATES array for prev/next
  const idx = DATES.indexOf(date);
  document.getElementById('prevDay').disabled = (idx >= DATES.length - 1);
  document.getElementById('nextDay').disabled = (idx <= 0);

  if(!data){
    CATS.forEach(cat=>renderStories(cat.key,[]));
    document.querySelector('.stories-container').innerHTML = '<div class="no-data-hint">此日期无数据 · No data for this date</div>';
    return;
  }
  CATS.forEach(cat=>renderStories(cat.key, data[cat.key]||[]));
  document.querySelectorAll('.tab').forEach(t=>{
    const key=t.dataset.cat; t.querySelector('.count').textContent=(data[key]||[]).length;
  });
  const first = CATS.find(c=>(data[c.key]||[]).length>0);
  switchTab(first?first.key:CATS[0].key);
}

function switchTab(key){
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.cat===key));
  document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active',p.dataset.cat===key));
}

// Date navigation via DATES array
document.getElementById('prevDay').onclick = () => {
  const idx = DATES.indexOf(curDate);
  if(idx < DATES.length - 1) renderDate(DATES[idx + 1]);
};
document.getElementById('nextDay').onclick = () => {
  const idx = DATES.indexOf(curDate);
  if(idx > 0) renderDate(DATES[idx - 1]);
};
document.getElementById('datePick').onchange = () => {
  const v = document.getElementById('datePick').value;
  if(ALL_DATA[v]) renderDate(v);
  else {
    // Find nearest available date
    const nearest = DATES.reduce((best,d) => Math.abs(new Date(d)-new Date(v)) < Math.abs(new Date(best)-new Date(v)) ? d : best, DATES[0]);
    renderDate(nearest);
  }
};

renderDate(curDate);
</script>
</body>
</html>'''

# =====================================================================
# Layer 5
# =====================================================================
def layer5_deliver(html_path, date_str, no_telegram=False):
    now = datetime.now(MYT)
    preview = f"📰 Hermes Daily · {date_str} {now.strftime('%H:%M')} MYT\n\n"
    try:
        stories = json.load(open(html_path.replace("index.html","stories.json")))
    except: stories = {}
    for label, key in [("🇺🇸 美股","us_stocks"),("🇲🇾 马股","my_stocks"),("🤖 AI","ai"),("🌐 宏观","macro")]:
        preview += f"{label}\n"
        for s in (stories.get(key,[]) or [])[:3]:
            preview += f"  • {s.get('headline','?')}\n"
        preview += "\n"
    host = _get_tailscale_host()
    url = f"http://{host}:8080/"
    preview += f"完整 -> {url}"
    result = {"preview": preview, "url": url, "status": "dry_run"}
    if no_telegram or "--dry-run" in sys.argv:
        return result
    token, chat_id = _load_telegram_token()
    if not token: return result
    try:
        resp = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat_id, "text": preview, "disable_web_page_preview": True}, timeout=15)
        result["status"] = "delivered" if resp.status_code == 200 else f"e{resp.status_code}"
    except Exception as e:
        log.warning(f"Telegram failed: {e}")
    return result

def weekly_archive():
    from weasyprint import HTML
    today = datetime.now(MYT)
    wk = today.isocalendar()
    pdf_dir = NEWS_DIR / "weekly"; pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / f"{wk[0]}-W{wk[1]:02d}.pdf"
    paths = sorted([_daily_base((today - timedelta(days=i)).strftime("%Y-%m-%d")).with_suffix(".html") for i in range(7) if _daily_base((today - timedelta(days=i)).strftime("%Y-%m-%d")).with_suffix(".html").exists()])
    if not paths: return
    HTML(string="<html><body>"+"".join(f'<div style="page-break-after:always;">{p.read_text()}</div>' for p in paths)+"</body></html>").write_pdf(str(pdf_path))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["daily","weekly_archive"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--skip-live-data", action="store_true")
    parser.add_argument("--date", help="Override date (YYYY-MM-DD)")
    args = parser.parse_args()
    if args.mode == "weekly_archive": weekly_archive(); return
    now = datetime.now(MYT)
    date_str = args.date or now.strftime("%Y-%m-%d")
    log.info(f"Mode: daily ({date_str})")
    t0 = time.time()
    log.info("Layer 1: Collection")
    candidates = layer1_collect(date_str)
    for c in CATEGORIES: log.info(f"  {c}={len(candidates.get(c,[]))}")
    log.info("Layer 2: Rank & Filter (concurrent)")
    ranked = layer2_rank(candidates)
    log.info("Layer 3: Detail Extraction (concurrent)")
    stories = layer3_detail(ranked, skip_live_data=args.skip_live_data)
    stories = _clean_data_cards(stories)
    warnings = scan_uncited_numbers(stories)
    if warnings: log.warning(f"Uncited warnings: {len(warnings)}")
    elapsed = time.time() - t0
    log.info(f"Stats: {_stats['llm_calls']} calls, {_stats['input_tokens']} in + {_stats['output_tokens']} out, ${_stats['cost']:.6f}, {elapsed:.0f}s")
    if args.dry_run:
        print(json.dumps({"date":date_str,"total_stories":sum(len(v)for v in stories.values()),"stats":dict(_stats),"stories":stories,"uncited_warnings":warnings,"time_s":elapsed},indent=2,ensure_ascii=False))
        return
    log.info("Layer 4: Render")
    hp = layer4_render(stories, date_str)
    log.info(f"HTML: {hp}")
    log.info("Layer 5: Delivery")
    r = layer5_deliver(hp, date_str, no_telegram=args.no_telegram)
    log.info(f"Status: {r['status']}")
    # Regenerate SPA index.html (single page with all dates)
    _generate_spa()
    log.info("Done.")

if __name__ == "__main__":
    main()