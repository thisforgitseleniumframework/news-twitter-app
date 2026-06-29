from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models import TweetDraft
from app.services.twitter_poster import post_tweet

router = APIRouter(prefix="/api/tweets", tags=["tweets"])


class TweetUpdate(BaseModel):
    tweet_text: str


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
    return query.order_by(TweetDraft.created_at.desc()).limit(limit).all()


@router.patch("/{draft_id}")
def update_draft(draft_id: int, update: TweetUpdate, db: Session = Depends(get_db)):
    """Edit the text of a tweet draft."""
    draft = db.query(TweetDraft).filter(TweetDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if len(update.tweet_text) > 280:
        raise HTTPException(status_code=400, detail="Tweet exceeds 280 characters")
    draft.tweet_text = update.tweet_text
    db.commit()
    db.refresh(draft)
    return draft


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
def post_to_twitter(draft_id: int, db: Session = Depends(get_db)):
    """Post an approved tweet draft to Twitter/X."""
    draft = db.query(TweetDraft).filter(TweetDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != "approved":
        raise HTTPException(status_code=400, detail="Only approved drafts can be posted")

    result = post_tweet(draft.tweet_text, draft.article_url)

    if result["success"]:
        draft.status = "posted"
        draft.twitter_post_id = result.get("tweet_id")
        draft.posted_at = datetime.now()
        db.commit()

    return result
