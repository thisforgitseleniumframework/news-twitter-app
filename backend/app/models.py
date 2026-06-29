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
    category = Column(String(50))  # "india" or "global"
    published_at = Column(String(100))
    fetched_at = Column(DateTime, server_default=func.now())
    is_processed = Column(Boolean, default=False)


class TweetDraft(Base):
    __tablename__ = "tweet_drafts"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, nullable=True)
    article_title = Column(String(500))
    article_url = Column(String(1000))
    tweet_text = Column(String(280))
    source = Column(String(100))
    category = Column(String(50))
    status = Column(String(20), default="draft")  # draft | approved | posted | rejected
    twitter_post_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    posted_at = Column(DateTime, nullable=True)
