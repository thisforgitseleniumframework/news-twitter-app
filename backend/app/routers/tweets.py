from fastapi import APIRouter, Body, Depends, HTTPException, WebSocket
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import Integer, case, func

from app.database import get_db
from app.models import TweetDraft, NewsArticle
from app.config import MAX_TWEET_LENGTH
from app.services.twitter_poster import post_tweet
from app.services.media_downloader import media_public_url
from app.services.browser_poster import open_compose_for_review, is_browser_session_busy

router = APIRouter(prefix="/api/tweets", tags=["tweets"])


class TweetUpdate(BaseModel):
    tweet_text: Optional[str] = None
    attach_media: Optional[bool] = None


class ScheduleTweet(BaseModel):
    scheduled_at: datetime  # ISO format: "2024-01-20T15:30:00"


class BatchAction(BaseModel):
    ids: List[int]
    action: str  # 'approve', 'reject', 'delete'


class PostOptions(BaseModel):
    attach_media: Optional[bool] = None  # override draft.attach_media for this post


def _serialize_draft(draft: TweetDraft) -> dict:
    return {
        "id": draft.id,
        "article_id": draft.article_id,
        "article_title": draft.article_title,
        "article_url": draft.article_url,
        "tweet_text": draft.tweet_text,
        "source": draft.source,
        "category": draft.category,
        "status": draft.status,
        "twitter_post_id": draft.twitter_post_id,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
        "posted_at": draft.posted_at.isoformat() if draft.posted_at else None,
        "scheduled_at": draft.scheduled_at.isoformat() if draft.scheduled_at else None,
        "engagement_count": draft.engagement_count or 0,
        "media_path": draft.media_path,
        "media_type": draft.media_type,
        "attach_media": bool(draft.attach_media) if draft.attach_media is not None else True,
        "media_url": media_public_url(draft.media_path),
    }


@router.get("/")
def get_drafts(
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Return tweet drafts, optionally filtered by status."""
    query = db.query(TweetDraft)
    if status:
        query = query.filter(TweetDraft.status == status)
    drafts = query.order_by(TweetDraft.created_at.desc()).limit(limit).all()
    return [_serialize_draft(d) for d in drafts]


@router.patch("/{draft_id}")
def update_draft(draft_id: int, update: TweetUpdate, db: Session = Depends(get_db)):
    """Edit draft text and/or whether media should be attached when posting."""
    draft = db.query(TweetDraft).filter(TweetDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if update.tweet_text is not None:
        if len(update.tweet_text) > MAX_TWEET_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Tweet exceeds {MAX_TWEET_LENGTH} characters (X Premium limit)",
            )
        draft.tweet_text = update.tweet_text
    if update.attach_media is not None:
        if update.attach_media and not draft.media_path:
            raise HTTPException(status_code=400, detail="No media available for this draft")
        draft.attach_media = update.attach_media
    db.commit()
    db.refresh(draft)
    return _serialize_draft(draft)


@router.post("/{draft_id}/approve")
def approve_draft(draft_id: int, db: Session = Depends(get_db)):
    """Mark a tweet draft as approved."""
    draft = db.query(TweetDraft).filter(TweetDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.status = "approved"
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{draft_id}/reject")
def reject_draft(draft_id: int, db: Session = Depends(get_db)):
    """Mark a tweet draft as rejected."""
    draft = db.query(TweetDraft).filter(TweetDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.status = "rejected"
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{draft_id}/post")
def post_to_twitter(
    draft_id: int,
    options: Optional[PostOptions] = Body(default=None),
    db: Session = Depends(get_db),
):
    """Post an approved tweet draft to Twitter/X via official API (optionally with media)."""
    draft = db.query(TweetDraft).filter(TweetDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != "approved":
        raise HTTPException(status_code=400, detail="Only approved drafts can be posted")

    # Prefer explicit body override, else draft preference
    use_media = draft.attach_media
    if options is not None and options.attach_media is not None:
        use_media = options.attach_media
        draft.attach_media = options.attach_media

    result = post_tweet(
        draft.tweet_text,
        draft.article_url,
        media_path=draft.media_path if use_media else None,
        media_type=draft.media_type if use_media else None,
        attach_media=bool(use_media),
    )

    if result["success"]:
        draft.status = "posted"
        draft.twitter_post_id = result.get("tweet_id")
        draft.posted_at = datetime.now()
        db.commit()

    return result


@router.post("/{draft_id}/post-browser")
def post_via_browser(
    draft_id: int,
    options: Optional[PostOptions] = Body(default=None),
    db: Session = Depends(get_db),
):
    """
    Semi-auto post: open X in a real browser, fill text + media, user clicks Post.

    Does not mark the draft as posted. Call /mark-posted after you publish.
    Works for draft or approved tweets (no paid API required).
    """
    draft = db.query(TweetDraft).filter(TweetDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status not in ("draft", "approved"):
        raise HTTPException(
            status_code=400,
            detail="Only draft or approved tweets can be opened in the browser",
        )
    if is_browser_session_busy():
        raise HTTPException(
            status_code=409,
            detail="A browser post session is already open. Close it first.",
        )

    use_media = bool(draft.attach_media)
    if options is not None and options.attach_media is not None:
        use_media = options.attach_media
        draft.attach_media = options.attach_media
        db.commit()

    result = open_compose_for_review(
        tweet_text=draft.tweet_text,
        article_url=draft.article_url,
        media_filename=draft.media_path if use_media else None,
        attach_media=use_media,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Browser post failed"))
    return result


@router.post("/{draft_id}/mark-posted")
def mark_as_posted(draft_id: int, db: Session = Depends(get_db)):
    """Mark a draft as posted after you published it manually in the browser."""
    draft = db.query(TweetDraft).filter(TweetDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status == "posted":
        return _serialize_draft(draft)
    if draft.status not in ("draft", "approved", "scheduled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot mark status '{draft.status}' as posted",
        )
    draft.status = "posted"
    draft.posted_at = datetime.now()
    if not draft.twitter_post_id:
        draft.twitter_post_id = "browser-manual"
    db.commit()
    db.refresh(draft)
    return _serialize_draft(draft)


@router.post("/batch/action")
def batch_action(action: BatchAction, db: Session = Depends(get_db)):
    """Perform batch actions on multiple tweet drafts."""
    if not action.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    
    drafts = db.query(TweetDraft).filter(TweetDraft.id.in_(action.ids)).all()
    
    if action.action == "approve":
        for draft in drafts:
            draft.status = "approved"
    elif action.action == "reject":
        for draft in drafts:
            draft.status = "rejected"
    elif action.action == "delete":
        for draft in drafts:
            db.delete(draft)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    db.commit()
    return {
        "success": True,
        "action": action.action,
        "count": len(drafts),
        "message": f"{action.action.capitalize()} completed for {len(drafts)} tweets"
    }


@router.post("/{draft_id}/schedule")
def schedule_tweet(draft_id: int, schedule: ScheduleTweet, db: Session = Depends(get_db)):
    """Schedule a tweet to be posted at a specific time."""
    draft = db.query(TweetDraft).filter(TweetDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status not in ["draft", "approved"]:
        raise HTTPException(status_code=400, detail="Only draft or approved tweets can be scheduled")
    if schedule.scheduled_at <= datetime.now():
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future")
    
    draft.status = "scheduled"
    draft.scheduled_at = schedule.scheduled_at
    db.commit()
    db.refresh(draft)
    return {
        "success": True,
        "message": f"Tweet scheduled for {schedule.scheduled_at.isoformat()}",
        "draft": draft
    }


@router.get("/analytics/overview")
def get_analytics_overview(db: Session = Depends(get_db)):
    """Get analytics overview: success rate, source performance, etc."""
    posted = db.query(TweetDraft).filter(TweetDraft.status == "posted").count()
    rejected = db.query(TweetDraft).filter(TweetDraft.status == "rejected").count()
    total_final = posted + rejected
    
    success_rate = (posted / total_final * 100) if total_final > 0 else 0
    
    # Best performing sources
    source_performance = db.query(
        TweetDraft.source,
        func.count(TweetDraft.id).label("count"),
        func.sum(case((TweetDraft.status == "posted", 1), else_=0).cast(Integer)).label("posted_count")
    ).group_by(TweetDraft.source).all()
    
    sources = []
    for source, count, posted_count in source_performance:
        if source:
            sources.append({
                "source": source,
                "total": count,
                "posted": posted_count or 0,
                "success_rate": (posted_count or 0) / count * 100 if count > 0 else 0
            })
    
    return {
        "success_rate": round(success_rate, 2),
        "total_posted": posted,
        "total_rejected": rejected,
        "top_sources": sorted(sources, key=lambda x: x["success_rate"], reverse=True)[:5]
    }


@router.get("/analytics/peak-times")
def get_peak_posting_times(db: Session = Depends(get_db)):
    """Analyze peak posting times from historically posted tweets."""
    posted_tweets = db.query(TweetDraft).filter(
        TweetDraft.status == "posted",
        TweetDraft.posted_at != None
    ).all()
    
    if not posted_tweets:
        return {"message": "No posted tweets yet", "peak_hours": []}
    
    hour_counts = {}
    for tweet in posted_tweets:
        hour = tweet.posted_at.hour
        hour_counts[hour] = hour_counts.get(hour, 0) + 1
    
    peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "peak_hours": [{"hour": f"{h:02d}:00", "count": count} for h, count in peak_hours],
        "recommendation": f"Best time to post: {peak_hours[0][0]:02d}:00 - {peak_hours[0][0]+1:02d}:00" if peak_hours else "Insufficient data"
    }


@router.get("/analytics/category-stats")
def get_category_stats(db: Session = Depends(get_db)):
    """Get performance stats by category (general + sports)."""
    from app.services.news_fetcher import CATEGORY_META

    categories = list(CATEGORY_META.keys())
    # Also include any orphan categories present in DB
    db_cats = [r[0] for r in db.query(TweetDraft.category).distinct().all() if r[0]]
    for c in db_cats:
        if c not in categories:
            categories.append(c)

    stats = {}
    for cat in categories:
        total = db.query(TweetDraft).filter(TweetDraft.category == cat).count()
        posted = db.query(TweetDraft).filter(
            TweetDraft.category == cat,
            TweetDraft.status == "posted"
        ).count()
        if total == 0 and cat not in ("india", "global"):
            # Skip empty sports cats to keep analytics compact
            continue
        stats[cat] = {
            "total": total,
            "posted": posted,
            "success_rate": (posted / total * 100) if total > 0 else 0,
            "label": CATEGORY_META.get(cat, {}).get("label", cat),
        }
    
    return stats


# WebSocket manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@router.websocket("/ws/stats")
async def websocket_stats(websocket: WebSocket, db: Session = Depends(get_db)):
    """WebSocket endpoint for real-time stats updates."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                # Send current stats
                from app.models import NewsArticle
                stats = {
                    "total_articles": db.query(NewsArticle).count(),
                    "draft_tweets": db.query(TweetDraft).filter(TweetDraft.status == "draft").count(),
                    "approved_tweets": db.query(TweetDraft).filter(TweetDraft.status == "approved").count(),
                    "scheduled_tweets": db.query(TweetDraft).filter(TweetDraft.status == "scheduled").count(),
                    "posted_tweets": db.query(TweetDraft).filter(TweetDraft.status == "posted").count(),
                    "rejected_tweets": db.query(TweetDraft).filter(TweetDraft.status == "rejected").count(),
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_json(stats)
    except:
        manager.disconnect(websocket)
