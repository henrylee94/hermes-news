#!/usr/bin/env python3
"""
Hermes News — HTML Renderer
Takes stories.json + template → daily HTML page + updates SPA index.
No LLM calls.
"""
import json, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

MYT = timezone(timedelta(hours=8), "MYT")

BASE_DIR = Path(os.environ.get("HERMES_WORKSPACE", os.path.expanduser("~/geewoni-workspace")))
VAULT_DIR = BASE_DIR / "vault"
CONFIG_DIR = Path(os.environ.get("NEWS_CONFIG_DIR", VAULT_DIR / "Config"))
NEWS_DIR = Path(os.environ.get("NEWS_OUTPUT_DIR", VAULT_DIR / "News"))

def daily_base(date_str):
    """NEWS_DIR/YYYY/MM/DD base path."""
    from datetime import datetime as dt
    d = dt.strptime(date_str, "%Y-%m-%d")
    return NEWS_DIR / d.strftime("%Y") / d.strftime("%m") / d.strftime("%d")

def scan_dates():
    """Scan year/month dirs, return sorted YYYY-MM-DD strings."""
    dates = []
    for year_dir in sorted(NEWS_DIR.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue
            for f in month_dir.glob("*.json"):
                dd = f.stem
                try:
                    ds = f"{year_dir.name}-{month_dir.name}-{dd.zfill(2)}"
                    datetime.strptime(ds, "%Y-%m-%d")
                    dates.append(ds)
                except ValueError:
                    pass
    return sorted(dates, reverse=True)

def render_daily(stories, date_str):
    """Render daily page from stories dict."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    # Try repo-local template first, then config dir
    repo_templates = Path(__file__).resolve().parent.parent / "templates"
    tp_candidates = [repo_templates / "news-template.html", CONFIG_DIR / "news-template.html"]

    env = Environment(autoescape=select_autoescape(["html"]))
    template = None
    for tp in tp_candidates:
        if tp.exists():
            env = Environment(loader=FileSystemLoader(str(tp.parent)), autoescape=select_autoescape(["html"]))
            template = env.get_template(tp.name)
            break
    if template is None:
        print("ERROR: No template found", file=sys.stderr)
        return None

    now = datetime.now(MYT)
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    wd = ["周一","周二","周三","周四","周五","周六","周日"][dt.weekday()]
    date_short = f"{dt.month}月{dt.day}日 {wd}"
    available = scan_dates()
    is_today = (date_str == now.strftime("%Y-%m-%d"))

    cat_cfg = [
        {"key":"us_stocks","icon":"🇺🇸","short":"美股","title":"美股 · US Markets",
         "stories": stories.get("us_stocks",[]),"candidates_count": str(len(stories.get("us_stocks",[])))},
        {"key":"my_stocks","icon":"🇲🇾","short":"马股","title":"马股 · Bursa Malaysia",
         "stories": stories.get("my_stocks",[]),"candidates_count": str(len(stories.get("my_stocks",[])))},
        {"key":"ai","icon":"🤖","short":"AI","title":"AI · 人工智能",
         "stories": stories.get("ai",[]),"candidates_count": str(len(stories.get("ai",[])))},
        {"key":"macro","icon":"🌐","short":"宏观","title":"宏观 · Macro",
         "stories": stories.get("macro",[]),"candidates_count": str(len(stories.get("macro",[])))},
    ]
    import hashlib, time
    ctx = {
        "date": date_str,
        "generated_at": now.strftime("%Y-%m-%d %H:%M MYT"),
        "categories": cat_cfg,
        "total_stories": sum(len(v) for v in stories.values()),
        "total_candidates": sum(len(v) for v in stories.values()),
        "build_hash": hashlib.md5(str(time.time()).encode()).hexdigest()[:4],
        "available_dates": available,
        "date_short": date_short,
        "max_date": now.strftime("%Y-%m-%d"),
        "is_today": is_today,
        "weekday": wd,
        "time": now.strftime("%H:%M"),
        "user": "Henry"
    }
    html = template.render(**ctx)
    base = daily_base(date_str)
    base.parent.mkdir(parents=True, exist_ok=True)
    open(base.with_suffix(".html"), "w").write(html)
    return str(base.with_suffix(".html"))

def render_spa():
    """Regenerate root index.html from all daily JSONs."""
    all_data = {}
    dates = scan_dates()
    for d in dates:
        sj = daily_base(d).with_suffix(".json")
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

    # Read SPA template (embedded in original pipeline or a separate file)
    spa_template = _get_spa_template()
    spa_html = (spa_template
        .replace("__ALL_DATA__", all_json)
        .replace("__DATES__", dates_json)
        .replace("__CATS__", cats_json)
        .replace("__TODAY__", today))
    out = NEWS_DIR / "index.html"
    open(out, "w").write(spa_html)
    print(f"SPA: {out} ({len(dates)} dates)", file=sys.stderr)

def _get_spa_template():
    """Read SPA template from pipeline module or inline fallback."""
    tpl_path = Path(__file__).resolve().parent.parent / "templates" / "spa-template.html"
    if tpl_path.exists():
        return tpl_path.read_text()
    # Inline fallback (minimal)
    return open(Path(__file__).resolve().parent / "news_pipeline.py").read().split("_SPA_TEMPLATE = r'''")[1].split("'''")[0]

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Render stories.json → HTML")
    p.add_argument("--stories", required=True, help="Path to stories.json")
    p.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    p.add_argument("--spa", action="store_true", help="Also regenerate SPA index.html")
    args = p.parse_args()

    stories = json.load(open(args.stories))
    html_path = render_daily(stories, args.date)
    print(f"Daily: {html_path}", file=sys.stderr)
    if args.spa:
        render_spa()
