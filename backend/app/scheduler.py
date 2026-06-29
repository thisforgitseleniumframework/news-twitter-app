import os
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.models import NewsArticle
from app.services.news_fetcher import fetch_all_news


def _fetch_and_store():
    """Background job: fetch news from all RSS feeds and save new articles."""
    db = SessionLocal()
    try:
        articles = fetch_all_news("all")
        new_count = 0
        for data in articles:
            exists = db.query(NewsArticle).filter(NewsArticle.url == data["url"]).first()
            if not exists:
                db.add(NewsArticle(**data))
                new_count += 1
        db.commit()
        print(f"[Scheduler] Done — {new_count} new articles added out of {len(articles)} fetched")
    except Exception as e:
        print(f"[Scheduler] Error: {e}")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    interval_hours = int(os.getenv("NEWS_FETCH_INTERVAL_HOURS", "2"))
    scheduler = BackgroundScheduler()
    scheduler.add_job(_fetch_and_store, "interval", hours=interval_hours, id="news_fetch")
    scheduler.start()
    print(f"[Scheduler] Started — news will be fetched every {interval_hours} hour(s)")
    return scheduler
