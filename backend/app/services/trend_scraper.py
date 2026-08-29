"""
Fetch trending topics from X (Twitter) via browser UI automation (Playwright).

Uses the same persistent profile as browser posting so you only log in once.
Scrapes Explore / Trending pages — not the official API.

Personal / experimental use only. Automated scraping may violate X's terms.
"""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.x_browser_common import profile_dir, release, try_acquire

CACHE_PATH = Path(__file__).resolve().parent.parent.parent / ".trends_cache.json"
TRENDING_URLS = (
    "https://x.com/explore/tabs/trending",
    "https://x.com/explore",
    "https://x.com/i/trends",
)

# Max trends to keep
MAX_TRENDS = 25

_cache_lock = threading.Lock()
_scrape_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_query(name: str) -> str:
    """Strip # and noise for news keyword search."""
    text = (name or "").strip()
    text = text.lstrip("#")
    # Drop trailing volume-like fragments sometimes stuck on labels
    text = re.sub(r"\s+\d+(\.\d+)?[KkMm]?\s*(posts?|tweets?)?\s*$", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_plausible_trend(name: str) -> bool:
    if not name or len(name) < 2:
        return False
    lower = name.lower()
    # Skip chrome / nav noise
    blocked = (
        "what's happening",
        "whats happening",
        "show more",
        "trending",
        "for you",
        "news",
        "sports",
        "entertainment",
        "sign in",
        "log in",
        "follow",
        "promoted",
        "ads",
    )
    if lower in blocked:
        return False
    if lower.startswith("trending in"):
        return False
    # Too long = likely a sentence not a trend
    if len(name) > 80:
        return False
    return True


def load_cached_trends() -> Dict[str, Any]:
    with _cache_lock:
        if not CACHE_PATH.exists():
            return {
                "fetched_at": None,
                "source": None,
                "trends": [],
                "error": None,
                "message": "No trends cached yet. Click Refresh to scrape X Explore.",
            }
        try:
            data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("bad cache shape")
            data.setdefault("trends", [])
            return data
        except Exception as e:
            return {
                "fetched_at": None,
                "source": None,
                "trends": [],
                "error": f"Cache read failed: {e}",
                "message": "Trends cache unreadable. Refresh to scrape again.",
            }


def _save_cache(data: Dict[str, Any]) -> None:
    with _cache_lock:
        CACHE_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _extract_from_page(page) -> List[str]:
    """Collect candidate trend labels from the open page."""
    names: List[str] = []

    # Primary: X trend rows
    selectors = [
        '[data-testid="trend"]',
        'div[data-testid="trend"]',
        'a[href*="/search?q="]',
        'a[href*="/hashtag/"]',
    ]

    for sel in selectors:
        try:
            loc = page.locator(sel)
            count = min(loc.count(), 40)
            for i in range(count):
                try:
                    el = loc.nth(i)
                    text = (el.inner_text(timeout=1500) or "").strip()
                    if not text:
                        continue
                    # Trend cards often have multi-line: category / name / posts
                    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                    # Prefer a middle line that looks like the topic
                    candidate = None
                    for ln in lines:
                        if re.search(r"trending|posts?$|tweets?$|\d+[KkMm]\s*posts", ln, re.I):
                            continue
                        if re.match(r"^\d+$", ln):
                            continue
                        candidate = ln
                        break
                    if not candidate and lines:
                        candidate = max(lines, key=len)
                    if candidate:
                        names.append(candidate)
                except Exception:
                    continue
        except Exception:
            continue

    # Hashtags visible on page
    try:
        body = page.inner_text("body", timeout=5000) or ""
        for m in re.findall(r"#[A-Za-z0-9_]{2,50}", body):
            names.append(m)
    except Exception:
        pass

    return names


def _dedupe_trends(raw_names: List[str]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for name in raw_names:
        name = re.sub(r"\s+", " ", (name or "").strip())
        if not _is_plausible_trend(name):
            continue
        query = _normalize_query(name)
        if not query or len(query) < 2:
            continue
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "name": name if name.startswith("#") or " " in name else name,
                "query": query,
                "rank": len(out) + 1,
            }
        )
        if len(out) >= MAX_TRENDS:
            break
    return out


def scrape_x_trends(headed: bool = True, timeout_ms: int = 90000) -> Dict[str, Any]:
    """
    Open X Explore in Chromium (shared profile), scrape trends, update cache.

    headed=True shows the browser so you can log in if needed.
    """
    if not _scrape_lock.acquire(blocking=False):
        return {
            "success": False,
            "error": "A trends scrape is already running.",
            **load_cached_trends(),
        }

    err = try_acquire("trend scrape")
    if err:
        _scrape_lock.release()
        return {"success": False, "error": err, **load_cached_trends()}

    result: Dict[str, Any] = {
        "success": False,
        "fetched_at": _now_iso(),
        "source": "x_explore",
        "trends": [],
        "error": None,
        "message": "",
    }

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

        raw_names: List[str] = []
        used_url = TRENDING_URLS[0]

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir()),
                headless=not headed,
                viewport={"width": 1200, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"],
            )
            page = context.pages[0] if context.pages else context.new_page()

            for url in TRENDING_URLS:
                used_url = url
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    # Allow client-side trend lists to render
                    page.wait_for_timeout(4000)
                    # If login wall, give user time when headed
                    loginish = page.locator(
                        'input[name="text"], input[autocomplete="username"], '
                        'a[href="/login"], [data-testid="loginButton"]'
                    )
                    if headed and loginish.count() > 0:
                        print(
                            "[Trends] Login may be required — "
                            "sign in to X in the browser window."
                        )
                        page.wait_for_timeout(45000)

                    # Wait for any trend-like content
                    try:
                        page.wait_for_selector(
                            '[data-testid="trend"], a[href*="/search?q="], '
                            'a[href*="/hashtag/"]',
                            timeout=20000,
                        )
                    except PwTimeout:
                        print(f"[Trends] No trend selectors yet on {url}")

                    # Scroll a bit to load more
                    page.mouse.wheel(0, 1200)
                    page.wait_for_timeout(1500)

                    found = _extract_from_page(page)
                    raw_names.extend(found)
                    if len(_dedupe_trends(raw_names)) >= 8:
                        break
                except Exception as e:
                    print(f"[Trends] Failed on {url}: {e}")
                    continue

            try:
                context.close()
            except Exception:
                pass

        trends = _dedupe_trends(raw_names)
        result["trends"] = trends
        result["source"] = used_url
        result["fetched_at"] = _now_iso()

        if trends:
            result["success"] = True
            result["message"] = (
                f"Scraped {len(trends)} trends from X. "
                "Click a trend to filter news."
            )
            result["error"] = None
        else:
            result["success"] = False
            result["error"] = (
                "No trends found. Log in to X in the browser profile "
                "(use Open browser post once if needed), then refresh trends again."
            )
            result["message"] = result["error"]

        _save_cache(
            {
                "fetched_at": result["fetched_at"],
                "source": result["source"],
                "trends": trends,
                "error": result.get("error"),
                "message": result.get("message"),
            }
        )
        return result

    except Exception as e:
        result["error"] = str(e)
        result["message"] = f"Trend scrape failed: {e}"
        print(f"[Trends] Error: {e}")
        # Keep previous cache if scrape fails
        cached = load_cached_trends()
        if cached.get("trends"):
            result["trends"] = cached["trends"]
            result["fetched_at"] = cached.get("fetched_at")
        return result
    finally:
        release()
        _scrape_lock.release()


def refresh_trends_async(headed: bool = True) -> Dict[str, Any]:
    """
    Start scrape in a background thread; return immediately.
    Poll GET /api/trends for results.
    """
    from app.services.x_browser_common import busy_reason, is_browser_busy

    if is_scrape_running():
        return {
            "success": False,
            "started": False,
            "error": "A trends scrape is already running.",
            **load_cached_trends(),
        }

    if is_browser_busy():
        return {
            "success": False,
            "started": False,
            "error": f"Browser busy: {busy_reason()}",
            **load_cached_trends(),
        }

    def _run():
        scrape_x_trends(headed=headed)

    t = threading.Thread(target=_run, daemon=True, name="x-trend-scrape")
    t.start()
    return {
        "success": True,
        "started": True,
        "message": (
            "Scraping X trends in the browser. "
            "Log in if prompted. Results appear shortly — the list will refresh."
        ),
        **load_cached_trends(),
    }


def is_scrape_running() -> bool:
    return _scrape_lock.locked()
