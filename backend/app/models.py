from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    url = Column(String(1000), unique=True, index=True)
    source = Column(String(100))
    # india | global | sports_local | sports_international |
    # sports_laliga | sports_epl | sports_tennis | sports_cricket
    category = Column(String(50))
    published_at = Column(String(100))
    fetched_at = Column(DateTime, server_default=func.now())
    is_processed = Column(Boolean, default=False)
    # Media saved under backend/media/ when news is fetched
    media_path = Column(String(500), nullable=True)  # filename in media folder
    media_type = Column(String(20), nullable=True)  # "image" | "video"
    media_source_url = Column(String(1000), nullable=True)  # original remote URL


class TweetDraft(Base):
    __tablename__ = "tweet_drafts"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, nullable=True)
    article_title = Column(String(500))
    article_url = Column(String(1000))
    tweet_text = Column(Text)  # Premium long posts up to MAX_TWEET_LENGTH
    source = Column(String(100))
    category = Column(String(50))
    status = Column(String(20), default="draft")  # draft | approved | posted | rejected | scheduled
    twitter_post_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    posted_at = Column(DateTime, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)  # For scheduling posts
    engagement_count = Column(Integer, default=0)  # Track engagement metrics
    # Copied from article at generate-time; user can toggle attach when posting
    media_path = Column(String(500), nullable=True)
    media_type = Column(String(20), nullable=True)  # "image" | "video"
    attach_media = Column(Boolean, default=True)
