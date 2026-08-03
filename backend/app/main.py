import os
import certifi

# Fix Windows SSL certificate verification for all outbound HTTPS requests
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.models import NewsArticle, TweetDraft
from app.routers import news, tweets
from app.scheduler import start_scheduler
from app.services.media_downloader import MEDIA_DIR


def _migrate_schema():
    """Add columns introduced after the initial DB create (SQLite-safe)."""
    insp = inspect(engine)
    migrations = {
        "news_articles": [
            ("media_path", "VARCHAR(500)"),
            ("media_type", "VARCHAR(20)"),
            ("media_source_url", "VARCHAR(1000)"),
        ],
        "tweet_drafts": [
            ("scheduled_at", "DATETIME"),
            ("engagement_count", "INTEGER DEFAULT 0"),
            ("media_path", "VARCHAR(500)"),
            ("media_type", "VARCHAR(20)"),
            ("attach_media", "BOOLEAN DEFAULT 1"),
        ],
    }
    with engine.begin() as conn:
        for table, columns in migrations.items():
            if table not in insp.get_table_names():
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for col_name, col_type in columns:
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))
                    print(f"[DB] Added {table}.{col_name}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables, migrate schema, start scheduler
    Base.metadata.create_all(bind=engine)
    _migrate_schema()
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    scheduler = start_scheduler()
    yield
    # Shutdown: stop the scheduler cleanly
    scheduler.shutdown()


app = FastAPI(
    title="NewsPost API",
    description="Fetch news from global & India sources and generate tweet drafts",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "ws://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve downloaded article media at /media/<filename>
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

app.include_router(news.router)
app.include_router(tweets.router)


@app.get("/")
def root():
    return {"message": "NewsPost API is running", "docs": "/docs"}


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Dashboard statistics: article and tweet counts."""
    return {
        "total_articles": db.query(NewsArticle).count(),
        "draft_tweets": db.query(TweetDraft).filter(TweetDraft.status == "draft").count(),
        "approved_tweets": db.query(TweetDraft).filter(TweetDraft.status == "approved").count(),
        "scheduled_tweets": db.query(TweetDraft).filter(TweetDraft.status == "scheduled").count(),
        "posted_tweets": db.query(TweetDraft).filter(TweetDraft.status == "posted").count(),
        "rejected_tweets": db.query(TweetDraft).filter(TweetDraft.status == "rejected").count(),
    }
