"""Monitor an Instagram account and download new video posts continuously.
Moved to backend.ingestion.instagram.monitor.
"""
import json
import time
from pathlib import Path
from typing import Set

from dotenv import load_dotenv
from loguru import logger

from .scraper import scrape_account
from .config import (
    TARGET_ACCOUNT,
    MAX_DOWNLOADS_PER_SCRAPE,
    SCRAPE_INTERVAL,
    DATA_DIR,
    setup_logging,
)

load_dotenv()

SEEN_FILE = DATA_DIR / "downloaded.json"

setup_logging("monitor")


def load_seen() -> Set[str]:
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text()))
        except Exception:
            logger.warning("Failed to read seen file; starting fresh.")
    return set()


def save_seen(ids: Set[str]):
    try:
        SEEN_FILE.write_text(json.dumps(sorted(ids)))
    except Exception as e:
        logger.error("Could not save seen IDs: {}", e)


def main():
    if not TARGET_ACCOUNT:
        raise SystemExit("TARGET_ACCOUNT environment variable not set in .env")

    logger.info("Monitoring Instagram account @{}", TARGET_ACCOUNT)
    seen = load_seen()
    logger.info("Loaded {} previously downloaded posts", len(seen))

    while True:
        start = time.time()
        posts = scrape_account(
            TARGET_ACCOUNT,
            download=True,
            max_downloads=MAX_DOWNLOADS_PER_SCRAPE,
        )
        new_ids = {p["id"] for p in posts if p["media_type"] == "video"}
        unseen = new_ids - seen
        if unseen:
            seen.update(unseen)
            save_seen(seen)
            logger.info("{} new videos downloaded this cycle", len(unseen))
        else:
            logger.info("No new videos this cycle")

        elapsed = time.time() - start
        sleep_for = max(SCRAPE_INTERVAL - elapsed, 1)
        logger.debug("Sleeping {} seconds before next cycle", sleep_for)
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
