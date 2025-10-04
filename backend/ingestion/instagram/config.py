"""Project configuration loaded from environment variables (.env).
Located inside backend.ingestion.instagram package.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Load variables from .env if present (one directory above project root)
load_dotenv()

# project root: three levels up from this file (instagram -> ingestion -> backend -> ROOT)
BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "db"
DB_DIR.mkdir(exist_ok=True)
DB_FILE = DB_DIR / "media_metadata.db"

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", DATA_DIR / "downloads")) / "instagram"

DATA_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Monitoring settings
TARGET_ACCOUNT = os.getenv("TARGET_ACCOUNT", "")
MAX_DOWNLOADS_PER_SCRAPE = int(os.getenv("MAX_DOWNLOADS", "10"))
WAIT_BETWEEN_DOWNLOADS_MIN = int(os.getenv("WAIT_BETWEEN_DOWNLOADS_MIN", "5"))
WAIT_BETWEEN_DOWNLOADS_MAX = int(os.getenv("WAIT_BETWEEN_DOWNLOADS_MAX", "10"))
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "300"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# Headless browser flag (1=true, 0=false)
HEADLESS = os.getenv("HEADLESS", "true").strip().lower() == "true"


def setup_logging(module_name: str = "app") -> None:
    """Configure loguru sinks for console & rotating files."""
    logger.remove()
    logger.add(sys.stdout, level=LOG_LEVEL, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    log_file = DATA_DIR / f"{module_name}.log"
    logger.add(log_file, rotation="5 MB", retention=5, level=LOG_LEVEL, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
