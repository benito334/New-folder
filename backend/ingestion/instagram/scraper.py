"""Scraper module for Instagram videos (moved into backend.ingestion.instagram)."""
from typing import List, Dict
import requests
import time
from pathlib import Path
from loguru import logger
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

import json
from datetime import datetime

from .config import DOWNLOAD_DIR, setup_logging
from .db import contains_source_id, insert_metadata

# Initialise robust logging
setup_logging("scraper")

INSTAGRAM_BASE = "https://www.instagram.com"


def scrape_account(username: str, download: bool = False, max_downloads: int = 1000) -> List[Dict]:
    """Return list of post metadata dicts and optionally download new videos."""
    """Scrape the Instagram feed of a public account for posts."""
    posts: List[Dict] = []
    downloads_done = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
            locale="en-US",
        )
        page = context.new_page()
        target_url = f"{INSTAGRAM_BASE}/{username}/"
        logger.debug("Navigating to {}", target_url)
        try:
            page.goto(target_url, timeout=60000)
            page.wait_for_selector("article", timeout=60000)
            anchors = page.query_selector_all("article a")
            for a in anchors:
                href = a.get_attribute("href")
                if not href:
                    continue
                url = f"{INSTAGRAM_BASE}{href}" if href.startswith("/") else href
                try:
                    parts = [part for part in href.split("/") if part]
                    post_id = parts[-1] if parts[-1] not in ("reel", "p", "tv") else parts[-2]
                except Exception:
                    continue

                media_type = "image"
                video_src = None
                try:
                    post_page = context.new_page()
                    post_page.goto(url, timeout=60000)
                    has_video = post_page.query_selector("video") is not None
                    if has_video:
                        media_type = "video"
                        video_el = post_page.query_selector("video")
                        video_src = video_el.get_attribute("src") if video_el else None
                        if not video_src:
                            meta = post_page.query_selector("meta[property='og:video']")
                            if meta:
                                video_src = meta.get_attribute("content")
                        upload_ts = None
                        ts_meta = post_page.query_selector("meta[property='og:video:upload_date']")
                        if ts_meta:
                            try:
                                upload_ts = int(ts_meta.get_attribute("content"))
                            except (TypeError, ValueError):
                                pass
                    logger.debug("Post {} classified as {}", post_id, media_type)
                    post_page.close()
                except Exception as e:
                    logger.exception("Failed to inspect post {}: {}", url, e)

                date_str = ""
                if media_type == "video" and upload_ts:
                                        date_str = datetime.utcfromtimestamp(upload_ts).strftime("%Y%m%dT%H%M%S")
                post_meta = {
                    "id": post_id,
                    "url": url,
                    "date_posted": date_str,
                    "media_type": media_type,
                }

                # Skip if already in DB
                if contains_source_id(post_id):
                    continue

                if download and media_type == "video" and video_src and downloads_done < max_downloads:
                    try:
                        Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
                        ts_suffix = post_meta["date_posted"] or str(int(time.time()))
                        dest_path = DOWNLOAD_DIR / f"{post_id}_{ts_suffix}.mp4"
                        if not dest_path.exists():
                            logger.debug("Downloading video {}", video_src)
                            r = requests.get(video_src, timeout=120)
                            dest_path.write_bytes(r.content)
                            downloads_done += 1
                            logger.info("Downloaded video to {} ({} / {})", dest_path, downloads_done, max_downloads)

                            # write JSON sidecar
                            meta_path = dest_path.with_suffix(".json")
                            with meta_path.open("w", encoding="utf-8") as fp:
                                json.dump(post_meta, fp, ensure_ascii=False, indent=2)

                            # insert into DB
                            record = {
                                "source_id": post_id,
                                "source_type": "instagram",
                                "original_url": url,
                                "file_path": str(dest_path.relative_to(DOWNLOAD_DIR.parent)),
                                "publish_date": post_meta["date_posted"],
                                "author": username,
                                "length_seconds": None,
                                "language": None,
                                "license": None,
                                "ingest_date": datetime.utcnow().isoformat(timespec="seconds"),
                                "notes": "",
                            }
                            insert_metadata(record)
                        else:
                            logger.debug("Video {} already exists on disk", dest_path)
                    except Exception as e:
                        logger.exception("Failed to download video {}: {}", url, e)

                posts.append(post_meta)
        except PlaywrightTimeoutError:
            logger.error("Timeout while loading Instagram page for {}", username)
        except Exception as e:
            logger.exception("Error scraping Instagram: {}", e)
        finally:
            context.close()
            browser.close()

    logger.info("Scraped {} posts from {} ({} videos downloaded)", len(posts), username, downloads_done)
    return posts
