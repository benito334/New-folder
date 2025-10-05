"""SQLite helper for media metadata storage."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Any, Iterable

from loguru import logger

from .config import DB_FILE

# Schema based on planning.md
_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS media_metadata (
    source_id TEXT PRIMARY KEY,
    source_type TEXT,
    original_url TEXT,
    file_path TEXT,
    publish_date DATETIME,
    author TEXT,
    length_seconds INTEGER,
    language TEXT,
    license TEXT,
    ingest_date DATETIME,
    notes TEXT
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(_CREATE_SQL)
    return conn


def contains_source_id(source_id: str) -> bool:
    """Return True if source_id exists; on database error log and return False."""
    try:
        conn = get_conn()
        cur = conn.execute(
            "SELECT 1 FROM media_metadata WHERE source_id=?",
            (source_id,),
        )
        exists = cur.fetchone() is not None
    except sqlite3.DatabaseError as e:
        logger.error("Database error while checking source_id %s: %s; treating as absent", source_id, e)
        exists = False
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return exists


def insert_metadata(meta: Dict[str, Any]):
    keys = ",".join(meta.keys())
    placeholders = ",".join(["?"] * len(meta))
    values: Iterable[Any] = meta.values()
    conn = get_conn()
    try:
        conn.execute(f"INSERT OR IGNORE INTO media_metadata ({keys}) VALUES ({placeholders})", tuple(values))
        conn.commit()
    except Exception as e:
        logger.error("Failed to insert metadata: {}", e)
    finally:
        conn.close()
