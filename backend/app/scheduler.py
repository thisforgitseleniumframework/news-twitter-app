import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.models import TweetDraft
from app.services.news_fetcher import fetch_all_news
from app.services.news_store import store_new_articles
from app.services.twitter_poster import post_tweet


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


def _post_scheduled_tweets():
    """Background job: check for and post scheduled tweets (with media if enabled)."""
    db = SessionLocal()
    try:
        now = datetime.now()
        scheduled_tweets = db.query(TweetDraft).filter(
            TweetDraft.status == "scheduled",
            TweetDraft.scheduled_at <= now
        ).all()
        
        for draft in scheduled_tweets:
            use_media = bool(draft.attach_media and draft.media_path)
            result = post_tweet(
                draft.tweet_text,
                draft.article_url,
                media_path=draft.media_path if use_media else None,
                media_type=draft.media_type if use_media else None,
                attach_media=use_media,
            )
            if result["success"]:
                draft.status = "posted"
                draft.twitter_post_id = result.get("tweet_id")
                draft.posted_at = now
                print(f"[Scheduler] Posted scheduled tweet {draft.id} (media={result.get('media_attached')})")
            else:
                print(f"[Scheduler] Failed to post scheduled tweet {draft.id}: {result.get('error')}")
        
        db.commit()
    except Exception as e:
        print(f"[Scheduler] Error posting scheduled tweets: {e}")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    interval_hours = int(os.getenv("NEWS_FETCH_INTERVAL_HOURS", "2"))
    scheduler = BackgroundScheduler()
    scheduler.add_job(_fetch_and_store, "interval", hours=interval_hours, id="news_fetch")
    scheduler.add_job(_post_scheduled_tweets, "interval", minutes=1, id="scheduled_posts")  # Check every minute
    scheduler.start()
    print(f"[Scheduler] Started — news will be fetched every {interval_hours} hour(s)")
    print(f"[Scheduler] Scheduled posts will be checked every minute")
    return scheduler
