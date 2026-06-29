from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import NewsArticle, TweetDraft
from app.services.news_fetcher import fetch_all_news
from app.services.ai_generator import generate_tweet

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/fetch")
def fetch_and_store_news(category: str = "all", db: Session = Depends(get_db)):
    """Fetch latest news from RSS feeds and store new articles in the DB."""
    articles = fetch_all_news(category)
    new_count = 0

    for data in articles:
        existing = db.query(NewsArticle).filter(NewsArticle.url == data["url"]).first()
        if not existing:
            db.add(NewsArticle(**data))
            new_count += 1

    db.commit()
    return {
        "message": f"Fetched {len(articles)} articles, {new_count} new added",
        "total_fetched": len(articles),
        "new_articles": new_count,
    }


@router.get("/")
def get_news(
    category: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Return stored news articles, optionally filtered by category or source."""
    query = db.query(NewsArticle)
    if category:
        query = query.filter(NewsArticle.category == category)
    if source:
        query = query.filter(NewsArticle.source == source)
    return query.order_by(NewsArticle.fetched_at.desc()).limit(limit).all()


@router.post("/{article_id}/generate-tweet")
def generate_tweet_for_article(article_id: int, db: Session = Depends(get_db)):
    """Generate an AI tweet draft for a specific article using Gemini."""
    article = db.query(NewsArticle).filter(NewsArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    tweet_text = generate_tweet(
        title=article.title,
        summary=article.summary or "",
        source=article.source,
        category=article.category,
    )

    draft = TweetDraft(
        article_id=article.id,
        article_title=article.title,
        article_url=article.url,
        tweet_text=tweet_text,
        source=article.source,
        category=article.category,
        status="draft",
    )
    db.add(draft)
    article.is_processed = True
    db.commit()
    db.refresh(draft)
    return draft
