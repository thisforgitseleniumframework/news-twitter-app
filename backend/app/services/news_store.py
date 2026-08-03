"""Shared helpers for storing fetched news + downloading media."""
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models import NewsArticle
from app.services.media_downloader import attach_media_to_article


def store_new_articles(db: Session, articles: List[Dict]) -> Tuple[int, int]:
    """
    Insert new articles and download media for each new one.

    Returns (new_article_count, media_saved_count).
    """
    new_count = 0
    media_count = 0

    for data in articles:
        # media_source_url is not a DB-ready field until download succeeds
        media_source_url = data.pop("media_source_url", None)

        existing = db.query(NewsArticle).filter(NewsArticle.url == data["url"]).first()
        if existing:
            # Optionally backfill media for existing articles that lack it
            if not existing.media_path and (media_source_url or existing.media_source_url):
                if attach_media_to_article(existing, media_source_url or existing.media_source_url):
                    media_count += 1
            continue

        article = NewsArticle(**data)
        db.add(article)
        db.flush()  # assign id for media filename prefix
        new_count += 1

        if media_source_url and attach_media_to_article(article, media_source_url):
            media_count += 1

    db.commit()
    return new_count, media_count
