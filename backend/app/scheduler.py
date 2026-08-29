import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models import TweetDraft
from app.services.news_fetcher import fetch_all_news
from app.services.news_store import store_new_articles
from app.services.twitter_poster import post_tweet, post_thread
import json


def _fetch_and_store():
    """Background job: fetch news from all RSS feeds, save articles + media."""
    db = SessionLocal()
    try:
        articles = fetch_all_news("all")
        new_count, media_count = store_new_articles(db, articles)
        print(
            f"[Scheduler] Done — {new_count} new articles, "
            f"{media_count} media saved (of {len(articles)} fetched)"
        )
    except Exception as e:
        print(f"[Scheduler] Error: {e}")
    finally:
        db.close()


def _api_keys_configured() -> bool:
    required = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET",
        "TWITTER_BEARER_TOKEN",
    ]
    return all(os.getenv(k) and not str(os.getenv(k)).startswith("your_") for k in required)


def _post_scheduled_tweets():
    """
    Background job: post (or open browser for) scheduled tweets that are due.

    - If X API keys are configured → post via API
    - Else → open browser compose (same semi-auto flow as the UI)
    - Avoid re-firing the same draft every minute via twitter_post_id markers
    """
    db = SessionLocal()
    try:
        now = datetime.now()
        due = (
            db.query(TweetDraft)
            .filter(
                TweetDraft.status == "scheduled",
                TweetDraft.scheduled_at != None,  # noqa: E711
                TweetDraft.scheduled_at <= now,
            )
            .all()
        )

        for draft in due:
            # Already handed off to browser once — wait for user "Mark as posted"
            marker = (draft.twitter_post_id or "").strip()
            if marker.startswith("browser-due") or marker.startswith("awaiting"):
                print(
                    f"[Scheduler] Draft {draft.id} already opened in browser "
                    f"({marker}); waiting for Mark as posted"
                )
                continue

            use_media = bool(draft.attach_media and draft.media_path)
            posted = False

            thread_parts = []
            raw_parts = getattr(draft, "thread_parts", None)
            if raw_parts and getattr(draft, "is_thread", False):
                try:
                    parsed = json.loads(raw_parts) if isinstance(raw_parts, str) else raw_parts
                    if isinstance(parsed, list):
                        thread_parts = [str(p).strip() for p in parsed if str(p or "").strip()]
                except Exception:
                    thread_parts = []
            is_thread = len(thread_parts) >= 2

            if _api_keys_configured():
                if is_thread:
                    result = post_thread(
                        thread_parts,
                        article_url=draft.article_url,
                        media_path=draft.media_path if use_media else None,
                        media_type=draft.media_type if use_media else None,
                        attach_media=use_media,
                    )
                else:
                    result = post_tweet(
                        draft.tweet_text,
                        draft.article_url,
                        media_path=draft.media_path if use_media else None,
                        media_type=draft.media_type if use_media else None,
                        attach_media=use_media,
                    )
                if result.get("success"):
                    draft.status = "posted"
                    draft.twitter_post_id = result.get("tweet_id")
                    draft.posted_at = now
                    posted = True
                    print(
                        f"[Scheduler] Posted scheduled tweet {draft.id} via API "
                        f"(media={result.get('media_attached')}"
                        f"{', thread=' + str(result.get('thread_count')) if is_thread else ''})"
                    )
                else:
                    print(
                        f"[Scheduler] API post failed for {draft.id}: "
                        f"{result.get('error')} — trying browser"
                    )

            if not posted:
                # Semi-auto browser path (no paid API)
                try:
                    from app.services.browser_poster import (
                        is_browser_session_busy,
                        open_compose_for_review,
                    )

                    if is_browser_session_busy():
                        print(
                            f"[Scheduler] Browser busy; will retry draft {draft.id} later"
                        )
                        continue

                    compose_text = thread_parts[0] if is_thread else draft.tweet_text
                    browser = open_compose_for_review(
                        compose_text,
                        article_url=draft.article_url,
                        media_filename=draft.media_path if use_media else None,
                        attach_media=use_media,
                    )
                    if browser.get("success"):
                        draft.twitter_post_id = f"browser-due-{draft.id}"
                        # Stay "scheduled" until user confirms post in the UI
                        print(
                            f"[Scheduler] Opened browser for scheduled draft {draft.id}. "
                            "Click Post on X, then Mark as posted in the app."
                        )
                    else:
                        print(
                            f"[Scheduler] Browser open failed for {draft.id}: "
                            f"{browser.get('error')}"
                        )
                except Exception as e:
                    print(f"[Scheduler] Browser fallback error for {draft.id}: {e}")

        db.commit()
    except Exception as e:
        print(f"[Scheduler] Error posting scheduled tweets: {e}")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    interval_hours = int(os.getenv("NEWS_FETCH_INTERVAL_HOURS", "2"))
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _fetch_and_store, "interval", hours=interval_hours, id="news_fetch"
    )
    scheduler.add_job(
        _post_scheduled_tweets, "interval", minutes=1, id="scheduled_posts"
    )
    scheduler.start()
    print(f"[Scheduler] Started — news will be fetched every {interval_hours} hour(s)")
    print("[Scheduler] Scheduled posts checked every minute (API or browser)")
    return scheduler
