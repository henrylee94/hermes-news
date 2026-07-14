---
name: hermes-news
description: Hermes Daily news aggregator project guide — content structure, daily workflow.
---

# Hermes Daily — SKILL.md

## What Is This

A minimalist daily news aggregator. Dark-themed slideshow format, organized by date. Designed for quick morning scanning.

## Quick Start

```bash
python3 -m http.server 8080
# Open http://localhost:8080
```

## Architecture

```
index.html                    Main app shell + date navigation
YYYY-MM-DD/
├── index.html                Daily page (rendered)
└── stories.json              Raw story data
portfolio/                    (removed — see henrylee94/portfolio-website)
```

## Content Structure

Each day's `stories.json`:

```json
{
  "categories": [
    {
      "key": "us_stocks",
      "label": "US Stocks",
      "stories": [
        {
          "title": "NVDA earnings beat",
          "takeaway": "Revenue +12% QoQ...",
          "metric": { "label": "Revenue", "value": "$44.1B" },
          "support": 180.50,
          "resistance": 205.00
        }
      ]
    }
  ]
}
```

## Pages

| Key | Topic |
|-----|-------|
| us_stocks | US market movers, earnings |
| my_stocks | Bursa Malaysia highlights |
| ai_tech | AI developments, GitHub trending |
| macro | Global economic indicators |

## Adding a New Day

1. Create `YYYY-MM-DD/` directory
2. Add `stories.json` with categories and stories
3. Add `index.html` (copy from previous day, update data path)
4. The date picker in `index.html` auto-discovers directories

## Theme

- Supports `prefers-color-scheme: dark/light`
- CSS variables for all colors
- Font: Inter + Playfair Display + Noto Serif SC

## Content Rules

- Every story needs: title, takeaway, at least one metric
- Support/resistance levels for stock stories
- Keep takeaways under 2 sentences
- No external images — text and data only

## Automation

A daily cron job can generate `stories.json` from news APIs.
Source data can come from any structured format.

## Do NOT

- Add large media files (images, videos)
- Hardcode colors outside CSS variables
- Break the date navigation logic
- Commit generated daily pages if using automation (add to .gitignore)
