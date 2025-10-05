# Instagram Ingestion Service

This module continuously monitors a public Instagram account, classifies posts, and downloads new videos to local storage while recording metadata in SQLite.

---
## Features
- Headless (or headful) scraping powered by **Playwright**
- Randomised user–agent, viewport, scroll & classification delays to mimic human behaviour
- Continuous monitoring loop with configurable scrape interval
- Download cap per cycle + classification cap to avoid excessive traffic
- Skips posts already present in local SQLite DB (`media_metadata`)
- Robust against corrupt DB rows – logs and continues
- Structured logs (`monitor.log`, `scraper.log`) with rotation

---
## Directory Layout
```
backend/
└─ ingestion/
   └─ instagram/
      ├── config.py      # all env-driven settings
      ├── db.py          # SQLite helpers
      ├── scraper.py     # Playwright logic
      ├── monitor.py     # continuous loop wrapper
      ├── Dockerfile     # base image (root of repo)
      ├── docker-compose.yml (root)
      └── README.md      # <-- you are here
```
- Downloads: `data/downloads/instagram/`
- SQLite DB: `data/db/media_metadata.db`
- Logs: `data/monitor.log`, `data/scraper.log` (scraper log optional)

---
## Quick Start (Docker)
```bash
# build container
docker compose build

# start continuous monitor in background
docker compose up -d

# watch logs
docker compose logs -f instagram_scraper  # full logs
```
The Docker image is based on `mcr.microsoft.com/playwright/python` which already bundles Chromium & drivers.

---
## Environment Variables (.env)
| Variable | Default | Purpose |
|----------|---------|---------|
| `TARGET_ACCOUNT` | *(required)* | Instagram username to scrape |
| `MAX_DOWNLOADS` | `10` | Max videos to download per cycle |
| `MAX_CLASSIFICATIONS_PER_SCRAPE` | `1000` | Safety cap on post inspections |
| `SCRAPE_INTERVAL` | `300` | Seconds between monitor cycles |
| `WAIT_BETWEEN_DOWNLOADS_MIN/MAX` | `5` / `10` | Random pause before first scroll |
| `SCROLL_DELAY_MIN/MAX` | `1` / `2` | Random sleep after each scroll |
| `CLASSIFY_DELAY_MIN/MAX` | `0` / `0` | Delay after each post inspected |
| `DOWNLOAD_DIR` | `data/downloads` | Base folder for saved files |
| `HEADLESS` | `true` | Set `false` to see the browser | 
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose output |

Create a `.env` in project root or export vars prior to running Docker.

---
## Local Development
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# one-off scrape (no loop)
python -m backend.ingestion.instagram.scraper <username>

# continuous
python -m backend.ingestion.instagram.monitor
```
Install Playwright browsers once:
```bash
playwright install chromium
```

---
## Database Schema (`media_metadata`)
| column | type | description |
|--------|------|-------------|
| `source_id` | TEXT PK | Instagram post id |
| `source_type` | TEXT | `instagram` |
| `original_url` | TEXT | full reel URL |
| `file_path` | TEXT | relative path of downloaded `.mp4` |
| `publish_date` | DATETIME | UTC `YYYYMMDDTHHMMSS` if available |
| `author` | TEXT | account name |
| `length_seconds` | INTEGER | *future* |
| `language` | TEXT | *future* |
| `license` | TEXT | *future* |
| `ingest_date` | DATETIME | ISO timestamp when stored |
| `notes` | TEXT | free form |

---
## Common Operations
### List DB rows
```bash
sqlite3 data/db/media_metadata.db "SELECT source_id, ingest_date FROM media_metadata ORDER BY ingest_date DESC LIMIT 20;"
```
### Clear downloads & DB (danger!)
```bash
rm -rf data/downloads/instagram/*
sqlite3 data/db/media_metadata.db "DELETE FROM media_metadata;"
```
### Disable individual logs
Comment out `setup_logging("scraper")` in `scraper.py` to merge all logs into the monitor sink.

---
## Troubleshooting
- **Miss-classified image**: reels may lazy-load video tag. We now wait up to 5 s and fallback to `og:video` meta.
- **Hang after few skips**: corrupt DB rows – handled; ensure `db.py` patch deployed.
- **Playwright timeout**: Instagram rate-limiting; increase `SCRAPE_INTERVAL` or use fresh IP.

---
© 2025 Ingestion Team
