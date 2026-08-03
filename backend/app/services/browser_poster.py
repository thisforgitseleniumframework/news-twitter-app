"""
Semi-automatic X/Twitter posting via browser UI (Playwright).

Opens a real browser, fills the compose box (and optional media), then
leaves the Post click to the user. Reuses a persistent browser profile so
you only log in once.

Use at your own risk — automated browser use may violate X's terms of service.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from app.config import MAX_TWEET_LENGTH
from app.services.media_downloader import absolute_media_path

# Persistent profile so login session survives across posts
PROFILE_DIR = Path(__file__).resolve().parent.parent.parent / ".x_browser_profile"
COMPOSE_URL = "https://x.com/compose/post"

# Keep browser open long enough for the user to review & click Post
BROWSER_IDLE_MS = 30 * 60 * 1000  # 30 minutes

_lock = threading.Lock()
_active = False


def is_browser_session_busy() -> bool:
    return _active


def prepare_tweet_text(tweet_text: str, article_url: Optional[str] = None) -> str:
    full = (tweet_text or "").strip()
    if article_url and article_url not in full:
        candidate = f"{full} {article_url}".strip()
        if len(candidate) <= MAX_TWEET_LENGTH:
            return candidate
    if len(full) > MAX_TWEET_LENGTH:
        return full[: MAX_TWEET_LENGTH - 3] + "..."
    return full


def open_compose_for_review(
    tweet_text: str,
    article_url: Optional[str] = None,
    media_filename: Optional[str] = None,
    attach_media: bool = True,
) -> dict:
    """
    Launch headed Chromium, fill compose UI, attach media if requested.
    Does NOT click Post — user must confirm manually.

    Returns immediately; browser runs in a background thread.
    """
    global _active

    if _active:
        return {
            "success": False,
            "error": (
                "A browser post session is already open. "
                "Finish or close that window, then try again."
            ),
        }

    full_text = prepare_tweet_text(tweet_text, article_url)
    media_path = None
    if attach_media and media_filename:
        media_path = absolute_media_path(media_filename)

    def _run():
        global _active
        _active = True
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

            PROFILE_DIR.mkdir(parents=True, exist_ok=True)

            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    headless=False,
                    viewport={"width": 1100, "height": 800},
                    args=["--disable-blink-features=AutomationControlled"],
                    ignore_default_args=["--enable-automation"],
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(COMPOSE_URL, wait_until="domcontentloaded", timeout=60000)

                # If not logged in, user logs in manually in this window
                try:
                    page.wait_for_selector(
                        'div[role="textbox"][data-testid="tweetTextarea_0"], '
                        'div[role="textbox"][contenteditable="true"]',
                        timeout=120000,
                    )
                except PwTimeout:
                    print(
                        "[BrowserPoster] Compose box not found — "
                        "log in to X in the opened window if needed."
                    )

                # Fill tweet text (X uses contenteditable; typing is more reliable than fill)
                primary = page.locator(
                    'div[role="textbox"][data-testid="tweetTextarea_0"]'
                )
                box = primary if primary.count() > 0 else page.locator(
                    'div[role="textbox"][contenteditable="true"]'
                )
                try:
                    box.first.click(timeout=10000)
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    page.keyboard.type(full_text, delay=12)
                except Exception as e:
                    print(f"[BrowserPoster] Could not fill text: {e}")

                # Attach media via hidden file input
                if media_path:
                    try:
                        file_input = page.locator(
                            'input[data-testid="fileInput"], input[type="file"]'
                        ).first
                        file_input.set_input_files(media_path, timeout=15000)
                        print(f"[BrowserPoster] Attached media: {media_path}")
                        # Wait briefly for preview to appear
                        page.wait_for_timeout(2000)
                    except Exception as e:
                        print(f"[BrowserPoster] Media attach failed: {e}")

                print(
                    "[BrowserPoster] Ready — review the tweet and click Post yourself. "
                    "Close the browser window when done."
                )

                # Stay open until user closes the browser or timeout
                try:
                    page.wait_for_event("close", timeout=BROWSER_IDLE_MS)
                except Exception:
                    pass
                try:
                    context.close()
                except Exception:
                    pass
        except Exception as e:
            print(f"[BrowserPoster] Error: {e}")
        finally:
            _active = False

    # Serialize launches lightly
    if not _lock.acquire(blocking=False):
        return {
            "success": False,
            "error": "Another browser post is starting. Wait a moment and retry.",
        }

    try:
        if _active:
            return {
                "success": False,
                "error": "A browser post session is already open.",
            }
        thread = threading.Thread(target=_run, daemon=True, name="x-browser-poster")
        thread.start()
    finally:
        _lock.release()

    media_note = " with media" if media_path else ""
    return {
        "success": True,
        "mode": "semi_auto",
        "message": (
            f"Browser opened{media_note}. Log in if prompted, review the draft, "
            "then click Post yourself. When finished, use “Mark as posted” in the app."
        ),
        "tweet_text": full_text,
        "media_attached": bool(media_path),
        "media_path": media_path,
        "compose_url": COMPOSE_URL,
    }
