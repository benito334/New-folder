"""Scraper module for Instagram videos (moved into backend.ingestion.instagram)."""
from typing import List, Dict, Set
import random
import requests
import time
import json
from pathlib import Path
from loguru import logger
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from datetime import datetime

from .config import (
    DOWNLOAD_DIR,
    setup_logging,
    WAIT_BETWEEN_DOWNLOADS_MIN,
    WAIT_BETWEEN_DOWNLOADS_MAX,
    HEADLESS,
    SCROLL_DELAY_MIN,
    SCROLL_DELAY_MAX,
    CLASSIFY_DELAY_MIN,
    CLASSIFY_DELAY_MAX,
    MAX_CLASSIFICATIONS_PER_SCRAPE,
)
from .db import contains_source_id, insert_metadata

# Initialise robust logging
#setup_logging("scraper")
INSTAGRAM_BASE = "https://www.instagram.com"


def scrape_account(username: str, download: bool = False, max_downloads: int = 1000) -> List[Dict]:
    """Return list of post metadata dicts and optionally download new videos."""
    """Scrape the Instagram feed of a public account for posts."""
    posts: List[Dict] = []
    downloads_done = 0
    with sync_playwright() as p:
        # Headful mode with stealth patches and random viewport for better disguise
        browser = p.chromium.launch(headless=HEADLESS, args=["--start-maximized"])
        # Rotate UA & viewport
        rand_ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100,120)}.0.{random.randint(1000,9999)}.0 Safari/537.36"
        viewport = {"width": random.randint(1200, 1920), "height": random.randint(800, 1080)}
        logger.debug("Using UA={} viewport={}x{}", rand_ua, viewport['width'], viewport['height'])
        context = browser.new_context(user_agent=rand_ua, viewport=viewport)
        page = context.new_page()
        target_url = f"{INSTAGRAM_BASE}/{username}/"
        logger.debug("Navigating to {}", target_url)
        try:
            page.goto(target_url, timeout=60000)
            # simulate human scroll
            page.mouse.wheel(0, random.randint(300, 800))
            await_delay = random.uniform(WAIT_BETWEEN_DOWNLOADS_MIN, WAIT_BETWEEN_DOWNLOADS_MAX)
            logger.debug("Waiting {:.1f} seconds to imitate reading profile", await_delay)
            time.sleep(await_delay)
            page.wait_for_selector("article", timeout=60000)

            processed_post_ids: Set[str] = set()
            classified_count = 0
            unchanged_scrolls = 0
            while True:
                anchors = page.query_selector_all("article a")
                if len(anchors) == len(processed_post_ids):
                    unchanged_scrolls += 1
                else:
                    unchanged_scrolls = 0
                for a in anchors:
                    href = a.get_attribute("href")
                    if not href:
                        continue
                    # Extract unique post ID from href
                    parts = [part for part in href.split("/") if part]
                    try:
                        post_id = parts[-1] if parts[-1] not in ("reel", "p", "tv") else parts[-2]
                    except Exception:
                        continue

                    if post_id in processed_post_ids:
                        continue
                    processed_post_ids.add(post_id)

                    # Skip early if post already in DB
                    if contains_source_id(post_id):
                        logger.debug("Post {} already processed; skipping", post_id)
                        continue

                    url = f"{INSTAGRAM_BASE}{href}" if href.startswith("/") else href
                    media_type = "image"
                    video_src = None
                    upload_ts = None
                    # --- Inspect individual post page ---
                    try:
                        post_page = context.new_page()
                        post_page.goto(url, timeout=60000)
                        # wait a bit for video element or meta tag to load (lazy-loaded reels)
                        try:
                            post_page.wait_for_selector("video, meta[property='og:video']", timeout=5000)
                        except PlaywrightTimeoutError:
                            pass  # element didn't appear in time

                        video_el = post_page.query_selector("video")
                        if video_el is None:
                            meta_tag = post_page.query_selector("meta[property='og:video']")
                            if meta_tag:
                                video_src = meta_tag.get_attribute("content")
                                has_video = True
                            else:
                                has_video = False
                        else:
                            has_video = True
                            video_src = video_el.get_attribute("src")

                        if has_video:
                            media_type = "video"
                            # get upload timestamp if available
                            ts_meta = post_page.query_selector("meta[property='og:video:upload_date']")
                            if ts_meta:
                                try:
                                    upload_ts = int(ts_meta.get_attribute("content"))
                                except (TypeError, ValueError):
                                    pass
                        logger.debug("Post {} classified as {}", post_id, media_type)
                    except Exception as e:
                        logger.exception("Failed to inspect post {}: {}", url, e)
                    finally:
                        try:
                            post_page.close()
                        except Exception:
                            pass

                    time.sleep(random.uniform(CLASSIFY_DELAY_MIN, CLASSIFY_DELAY_MAX))  # imitate human delay for each scrape classification
                    # --- Build metadata and download if needed ---
                    date_str = ""
                    if media_type == "video" and upload_ts:
                        date_str = datetime.utcfromtimestamp(upload_ts).strftime("%Y%m%dT%H%M%S")

                    post_meta: Dict = {
                        "id": post_id,
                        "url": url,
                        "date_posted": date_str,
                        "media_type": media_type,
                    }

                    
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
                                if downloads_done >= max_downloads:
                                    logger.info("Reached download cap {}. Stopping scrape early.", max_downloads)
                                    stop_due_to_download_cap = True
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
                    classified_count += 1
                    if classified_count >= MAX_CLASSIFICATIONS_PER_SCRAPE:
                        logger.info("Reached classification cap {}. Stopping scrape early.", classified_count)
                        break

                dialog = page.query_selector("div[role='dialog'] h2")
                if dialog and "Log in" in dialog.inner_text():
                    logger.info("Login prompt detected; stopping further scrolling.")
                    break

                if stop_due_to_download_cap:
                    break

                if unchanged_scrolls >= 2:
                    logger.debug("No new posts after scrolling; reached end.")
                    break

                page.mouse.wheel(0, viewport["height"])
                if classified_count >= MAX_CLASSIFICATIONS_PER_SCRAPE:
                    break
                time.sleep(random.uniform(SCROLL_DELAY_MIN, SCROLL_DELAY_MAX))

            # end scroll loop
            if stop_due_to_download_cap:
                pass

        except PlaywrightTimeoutError:
            logger.error("Timeout while loading Instagram page for {}", username)
        except Exception as e:
            logger.exception("Error scraping Instagram: {}", e)
        finally:
            context.close()
            browser.close()

    logger.info("Scraped {} posts from {} ({} videos downloaded)", len(posts), username, downloads_done)
    return posts
