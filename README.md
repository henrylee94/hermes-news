# Hermes Daily

A minimalist daily news aggregator with a clean, magazine-style reading experience.

## Overview

Hermes Daily collects and renders curated news stories as a dark-themed slideshow, organized by date. Designed for quick morning scanning — key takeaways, metrics, and support/resistance levels at a glance.

### Pages

- **US Stocks** — Market movers, earnings, macro events
- **MY Stocks** — Bursa Malaysia highlights
- **AI & Tech** — AI developments, GitHub trending repos
- **Macro** — Global economic indicators

## Tech Stack

- Static HTML/CSS/JS — no build step
- JSON data files per date
- Dark/light theme via `prefers-color-scheme`

## Structure

```
index.html              — Main slideshow (today's stories)
2026/
  05/
    29.html             — Daily page
    29.json             — Daily story data
  06/ ...
  07/ ...
```

## Local Development

```bash
python3 -m http.server 8080
# Open http://localhost:8080
```

## License

MIT
