"""Create tweet drafts from top X trends (news-backed when possible)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import NewsArticle, TweetDraft
from app.services.x_revenue import apply_score_to_draft_fields
from app.services.ai_generator import (
    format_thread_display,
    generate_thread_for_trend_with_news,
    generate_tweet_for_trend_only,
    generate_tweet_for_trend_with_news,
    should_use_thread,
)
from app.services.news_priority import score_article
from app.services.trend_scraper import load_cached_trends


def _find_best_article(db: Session, query: str) -> Optional[NewsArticle]:
    """Pick the best stored article matching the trend keyword."""
    q = (query or "").strip().lstrip("#")
    if not q or len(q) < 2:
        return None

    pattern = f"%{q}%"
    candidates = (
        db.query(NewsArticle)
        .filter(
            or_(
                NewsArticle.title.ilike(pattern),
                NewsArticle.summary.ilike(pattern),
            )
        )
        .order_by(NewsArticle.fetched_at.desc())
        .limit(25)
        .all()
    )
    if not candidates:
        # Try first significant word for multi-word trends
        words = [w for w in q.split() if len(w) >= 4]
        for w in words[:3]:
            p = f"%{w}%"
            candidates = (
                db.query(NewsArticle)
                .filter(
                    or_(
                        NewsArticle.title.ilike(p),
                        NewsArticle.summary.ilike(p),
                    )
                )
                .order_by(NewsArticle.fetched_at.desc())
                .limit(25)
                .all()
            )
            if candidates:
                break

    if not candidates:
        return None

    scored = [(a, score_article(a)) for a in candidates]
    scored.sort(
        key=lambda x: (
            1 if x[1]["is_breaking"] else 0,
            x[1]["priority_score"],
            x[0].fetched_at.timestamp() if x[0].fetched_at else 0,
        ),
        reverse=True,
    )
    return scored[0][0]


def generate_drafts_from_top_trends(
    db: Session,
    top_n: int = 5,
    news_only: bool = False,
) -> Dict[str, Any]:
    """
    For each of the top N cached trends, create a TweetDraft.

    - If matching news exists: AI draft from article + hashtag
    - Else if news_only=False: cautious trend-only draft
    - Else: skip with reason
    """
    top_n = max(1, min(int(top_n or 5), 15))
    cache = load_cached_trends()
    trends = list(cache.get("trends") or [])[:top_n]

    if not trends:
        return {
            "success": False,
            "message": "No trends cached. Click “Refresh from X” first.",
            "created": 0,
            "skipped": 0,
            "drafts": [],
            "results": [],
        }

    results: List[Dict[str, Any]] = []
    drafts_out: List[Dict[str, Any]] = []
    created = 0
    skipped = 0

    for trend in trends:
        name = trend.get("name") or trend.get("query") or ""
        query = trend.get("query") or name
        rank = trend.get("rank")
        article = _find_best_article(db, query)

        try:
            if article:
                priority = score_article(article)
                use_thread = should_use_thread(
                    category=article.category,
                    is_breaking=bool(priority.get("is_breaking")),
                    priority_score=int(priority.get("priority_score") or 0),
                )
                if use_thread:
                    parts = generate_thread_for_trend_with_news(
                        title=article.title,
                        summary=article.summary or "",
                        source=article.source or "",
                        category=article.category or "news",
                        trend_name=name,
                        trend_query=query,
                    )
                    tweet_text = format_thread_display(parts)
                    draft = TweetDraft(
                        article_id=article.id,
                        article_title=article.title,
                        article_url=article.url,
                        tweet_text=tweet_text,
                        is_thread=True,
                        thread_parts=json.dumps(parts, ensure_ascii=False),
                        source=article.source,
                        category=article.category,
                        status="draft",
                        media_path=article.media_path,
                        media_type=article.media_type,
                        attach_media=bool(article.media_path),
                    )
                    mode = "news_thread"
                else:
                    tweet_text = generate_tweet_for_trend_with_news(
                        title=article.title,
                        summary=article.summary or "",
                        source=article.source or "",
                        category=article.category or "news",
                        trend_name=name,
                        trend_query=query,
                    )
                    draft = TweetDraft(
                        article_id=article.id,
                        article_title=article.title,
                        article_url=article.url,
                        tweet_text=tweet_text,
                        is_thread=False,
                        thread_parts=None,
                        source=article.source,
                        category=article.category,
                        status="draft",
                        media_path=article.media_path,
                        media_type=article.media_type,
                        attach_media=bool(article.media_path),
                    )
                    mode = "news"
                article.is_processed = True
            elif news_only:
                skipped += 1
                results.append(
                    {
                        "rank": rank,
                        "trend": name,
                        "query": query,
                        "status": "skipped",
                        "reason": "No matching news (news_only=true)",
                    }
                )
                continue
            else:
                tweet_text = generate_tweet_for_trend_only(name, query)
                draft = TweetDraft(
                    article_id=None,
                    article_title=f"Trending: {name}",
                    article_url=None,
                    tweet_text=tweet_text,
                    source="X Trends",
                    category="trend",
                    status="draft",
                    attach_media=False,
                )
                mode = "trend_only"

            apply_score_to_draft_fields(draft)
            db.add(draft)
            db.flush()
            created += 1
            item = {
                "rank": rank,
                "trend": name,
                "query": query,
                "status": "created",
                "mode": mode,
                "draft_id": draft.id,
                "revenue_score": draft.revenue_score,
                "revenue_grade": draft.revenue_grade,
                "tweet_text": draft.tweet_text,
                "article_id": draft.article_id,
                "article_title": draft.article_title,
            }
            results.append(item)
            drafts_out.append(
                {
                    "id": draft.id,
                    "tweet_text": draft.tweet_text,
                    "article_title": draft.article_title,
                    "status": draft.status,
                    "source": draft.source,
                    "category": draft.category,
                }
            )
        except Exception as e:
            skipped += 1
            results.append(
                {
                    "rank": rank,
                    "trend": name,
                    "query": query,
                    "status": "error",
                    "reason": str(e),
                }
            )
            print(f"[TrendDrafts] Failed for {name}: {e}")

    db.commit()

    news_backed = sum(1 for r in results if r.get("mode") in ("news", "news_thread"))
    trend_only = sum(1 for r in results if r.get("mode") == "trend_only")

    return {
        "success": created > 0,
        "message": (
            f"Created {created} draft(s) from top {len(trends)} trends "
            f"({news_backed} with news, {trend_only} trend-only"
            + (f", {skipped} skipped" if skipped else "")
            + ")."
        ),
        "created": created,
        "skipped": skipped,
        "news_backed": news_backed,
        "trend_only": trend_only,
        "top_n": top_n,
        "drafts": drafts_out,
        "results": results,
    }
