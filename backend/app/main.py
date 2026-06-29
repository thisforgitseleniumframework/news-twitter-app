from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.models import NewsArticle, TweetDraft
from app.routers import news, tweets
from app.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables and start background scheduler
    Base.metadata.create_all(bind=engine)
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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "posted_tweets": db.query(TweetDraft).filter(TweetDraft.status == "posted").count(),
        "rejected_tweets": db.query(TweetDraft).filter(TweetDraft.status == "rejected").count(),
    }
