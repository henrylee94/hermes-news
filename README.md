# Hermes Daily News

A daily news aggregator that pulls from 20+ RSS sources, uses LLM to extract key insights, and renders a clean dark-themed slideshow.

[![Deployed on Vercel](https://img.shields.io/badge/Deployed_on-Vercel-black?style=flat&logo=vercel)](https://portfolio-website-three-henna-93.vercel.app)

## What It Does

1. **Collect** — Fetches articles from RSS feeds (WSJ, MarketWatch, BBC, FT, TechCrunch, Arxiv, etc.)
2. **Rank & Detail** — LLM extracts key takeaways, metrics, support/resistance levels
3. **Render** — Generates static HTML pages + JSON data per day
4. **Deliver** — Pushes to Telegram, optional PDF weekly archive

4 categories: 🇺🇸 US Stocks · 🇲🇾 MY Stocks · 🤖 AI · 🌐 Macro

## Quick Start

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY=sk-...
python pipeline/news_pipeline.py daily
```

Output: `2026/MM/DD.html` + `DD.json` + root `index.html` (SPA)

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `LLM_API_KEY` | (required) | API key for LLM calls (fallback: `OPENROUTER_API_KEY`, then `~/.hermes/.env`) |
| `LLM_API_BASE` | `https://openrouter.ai/api/v1` | OpenAI-compatible API endpoint |
| `LLM_MODEL` | `deepseek/deepseek-v4-flash` | Model name for story extraction |
| `HERMES_WORKSPACE` | `~/geewoni-workspace` | Workspace root |
| `NEWS_OUTPUT_DIR` | `{workspace}/vault/News` | Where daily files are written |
| `NEWS_CONFIG_DIR` | `{workspace}/vault/Config` | Where sources.md and templates live |

## Project Structure

```
├── pipeline/
│   ├── news_pipeline.py    — Main 5-layer pipeline (965 lines)
│   ├── run.py              — Simple wrapper
│   └── (local dev copy)
├── config/
│   └── sources.md          — RSS source definitions (20+ feeds)
├── templates/
│   └── news-template.html  — Jinja2 HTML template
├── 2026/                   — Daily output (year/month/day)
│   ├── 05/
│   ├── 06/
│   └── 07/
├── index.html              — SPA with all dates embedded
├── requirements.txt
└── README.md
```

## Data Sources

- **US Stocks**: WSJ Markets, MarketWatch, Google News
- **MY Stocks**: FMT Business, EdgeProp, Bursa Malaysia
- **AI**: HuggingFace Papers, Simon Willison, Arxiv ML, TechCrunch, The Verge, MIT Tech Review
- **Macro**: BBC World, FT World, WSJ World, CNBC Politics

Source definitions: `config/sources.md`

## Local Development

```bash
python -m http.server 8080
# Open http://localhost:8080
```

## License

MIT
