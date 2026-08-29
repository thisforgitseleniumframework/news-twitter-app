"""X trending topics API (browser-scraped cache)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import NewsArticle
from app.services.trend_drafts import generate_drafts_from_top_trends
from app.services.trend_scraper import (
    is_scrape_running,
    load_cached_trends,
    refresh_trends_async,
    scrape_x_trends,
)

router = APIRouter(prefix="/api/trends", tags=["trends"])


class GenerateTrendDraftsBody(BaseModel):
    top_n: int = Field(5, ge=1, le=15, description="How many top trends to draft")
    news_only: bool = Field(
        False,
        description="If true, skip trends with no matching news article",
    )


@router.get("/")
def get_trends():
    """Return last scraped trends from cache."""
    data = load_cached_trends()
    data["scraping"] = is_scrape_running()
    return data


@router.post("/refresh")
def refresh_trends(
    headed: bool = Query(
        True,
        description="Show browser window (needed for first-time login)",
    ),
    wait: bool = Query(
        False,
        description="If true, block until scrape finishes (can take ~1 min)",
    ),
):
    """
    Scrape trending topics from X Explore using the saved browser profile.

    Default: starts in background and returns immediately.
    Use wait=true for a synchronous result (API client timeout must be high).
    """
    if wait:
        result = scrape_x_trends(headed=headed)
        result["scraping"] = False
        if not result.get("success") and not result.get("trends"):
            raise HTTPException(status_code=502, detail=result.get("error") or "Scrape failed")
        return result

    result = refresh_trends_async(headed=headed)
    result["scraping"] = True
    if not result.get("started") and result.get("error"):
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.get("/match")
def match_news_for_trend(
    query: str = Query(..., min_length=1, description="Trend keyword without #"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Count / list stored news articles matching a trend keyword."""
    q = query.strip().lstrip("#")
    if not q:
        raise HTTPException(status_code=400, detail="query required")

    pattern = f"%{q}%"
    base = db.query(NewsArticle).filter(
        or_(
            NewsArticle.title.ilike(pattern),
            NewsArticle.summary.ilike(pattern),
        )
    )
    total = base.count()
    articles = (
        base.order_by(NewsArticle.fetched_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "query": q,
        "match_count": total,
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "source": a.source,
                "category": a.category,
                "url": a.url,
            }
            for a in articles
        ],
    }


@router.post("/generate-drafts")
def generate_drafts_from_trends(
    body: GenerateTrendDraftsBody | None = None,
    top_n: int = Query(5, ge=1, le=15),
    news_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    """
    Generate tweet drafts for the top N cached X trends.

    Uses matching news when available; otherwise a cautious trend-only draft
    (unless news_only=true).
    """
    n = body.top_n if body else top_n
    only_news = body.news_only if body else news_only
    result = generate_drafts_from_top_trends(db, top_n=n, news_only=only_news)
    if not result.get("success") and result.get("created", 0) == 0:
        # No drafts — still 200 with message if trends empty / all skipped
        if "No trends cached" in (result.get("message") or ""):
            raise HTTPException(status_code=400, detail=result["message"])
    return result
