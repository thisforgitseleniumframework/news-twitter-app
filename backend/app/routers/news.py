from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import NewsArticle, TweetDraft
from app.services.news_fetcher import fetch_all_news, list_categories, SPORTS_CATEGORY_IDS
from app.services.news_store import store_new_articles
from app.services.ai_generator import generate_tweet
from app.services.media_downloader import media_public_url
from app.services.news_priority import score_article

router = APIRouter(prefix="/api/news", tags=["news"])


def _serialize_article(article: NewsArticle, priority: Optional[dict] = None) -> dict:
    """Include a public media URL and optional priority fields for the frontend."""
    priority = priority or score_article(article)
    return {
        "id": article.id,
        "title": article.title,
        "summary": article.summary,
        "url": article.url,
        "source": article.source,
        "category": article.category,
        "published_at": article.published_at,
        "fetched_at": article.fetched_at.isoformat() if article.fetched_at else None,
        "is_processed": article.is_processed,
        "media_path": article.media_path,
        "media_type": article.media_type,
        "media_source_url": article.media_source_url,
        "media_url": media_public_url(article.media_path),
        "priority_score": priority["priority_score"],
        "is_breaking": priority["is_breaking"],
        "priority_reasons": priority["priority_reasons"],
    }


@router.get("/fetch")
def fetch_and_store_news(category: str = "all", db: Session = Depends(get_db)):
    """Fetch latest news from RSS feeds, store new articles, and download media."""
    articles = fetch_all_news(category)
    new_count, media_count = store_new_articles(db, articles)
    return {
        "message": (
            f"Fetched {len(articles)} articles, {new_count} new added, "
            f"{media_count} media file(s) saved"
        ),
        "total_fetched": len(articles),
        "new_articles": new_count,
        "media_saved": media_count,
    }


@router.get("/")
def get_news(
    category: Optional[str] = None,
    source: Optional[str] = None,
    keyword: Optional[str] = None,
    days: Optional[int] = None,
    processed: Optional[bool] = None,
    sort: str = Query(
        "priority",
        description="priority (breaking first) | recent | breaking (only high-priority)",
    ),
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Return stored news articles with filtering and priority sorting.
    
    Query Parameters:
    - category: 'india' or 'global'
    - source: Filter by news source
    - keyword: Search in title or summary
    - days: Articles from last N days
    - processed: Filter by processing status
    - sort: priority | recent | breaking
    - limit, offset: Pagination
    """
    query = db.query(NewsArticle)
    
    if category:
        if category == "sports":
            query = query.filter(NewsArticle.category.in_(SPORTS_CATEGORY_IDS))
        elif category == "general":
            query = query.filter(NewsArticle.category.in_(["india", "global"]))
        else:
            query = query.filter(NewsArticle.category == category)
    if source:
        query = query.filter(NewsArticle.source == source)
    if keyword:
        query = query.filter(
            (NewsArticle.title.ilike(f"%{keyword}%")) |
            (NewsArticle.summary.ilike(f"%{keyword}%"))
        )
    if days is not None:
        cutoff_date = datetime.now() - timedelta(days=days)
        query = query.filter(NewsArticle.fetched_at >= cutoff_date)
    if processed is not None:
        query = query.filter(NewsArticle.is_processed == processed)
    
    # Fetch a wider window when scoring, then sort/slice in Python
    # (priority depends on title text, not a DB column)
    fetch_cap = min(max(limit + offset, limit) * 3, 500) if sort in ("priority", "breaking") else limit + offset
    if sort == "recent":
        total = query.count()
        articles = (
            query.order_by(NewsArticle.fetched_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "count": len(articles),
            "sort": sort,
            "articles": [_serialize_article(a) for a in articles],
        }

    candidates = query.order_by(NewsArticle.fetched_at.desc()).limit(fetch_cap).all()
    scored = [(a, score_article(a)) for a in candidates]

    if sort == "breaking":
        scored = [(a, p) for a, p in scored if p["is_breaking"]]
        scored.sort(key=lambda x: (x[1]["priority_score"], x[0].fetched_at or datetime.min), reverse=True)
    else:
        # priority (default): breaking first, then score, then recency
        scored.sort(
            key=lambda x: (
                1 if x[1]["is_breaking"] else 0,
                x[1]["priority_score"],
                x[0].fetched_at or datetime.min,
            ),
            reverse=True,
        )

    total = len(scored)
    page = scored[offset : offset + limit]
    return {
        "total": total,
        "count": len(page),
        "sort": sort,
        "articles": [_serialize_article(a, p) for a, p in page],
    }


@router.get("/sources")
def get_available_sources(db: Session = Depends(get_db)):
    """Get list of all available news sources."""
    sources = db.query(NewsArticle.source).distinct().all()
    return {"sources": [s[0] for s in sources if s[0]]}


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """List configured categories (general + sports) with article counts."""
    catalog = list_categories()
    counts = {
        row[0]: row[1]
        for row in db.query(NewsArticle.category, func.count(NewsArticle.id))
        .group_by(NewsArticle.category)
        .all()
    }
    for item in catalog:
        item["article_count"] = counts.get(item["id"], 0)
    sports_total = sum(counts.get(c, 0) for c in SPORTS_CATEGORY_IDS)
    return {
        "categories": catalog,
        "sports_total": sports_total,
        "sports_ids": SPORTS_CATEGORY_IDS,
    }


@router.post("/{article_id}/generate-tweet")
def generate_tweet_for_article(article_id: int, db: Session = Depends(get_db)):
    """
    Generate an AI tweet draft for a specific article using Gemini.

    The same article can be used any number of times — each click creates a
    new draft. is_processed is set True as a soft “used before” flag only.
    """
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
        media_path=article.media_path,
        media_type=article.media_type,
        attach_media=bool(article.media_path),
    )
    db.add(draft)
    article.is_processed = True  # soft flag only — does not block re-use
    db.commit()
    db.refresh(draft)
    return draft
