import os
from pathlib import Path
from typing import Optional
import tweepy
from dotenv import load_dotenv

from app.config import MAX_TWEET_LENGTH
from app.services.media_downloader import absolute_media_path

load_dotenv()


def _oauth1_user():
    """Shared OAuth 1.0a credentials for v1.1 media upload + v2 client."""
    required = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET",
    ]
    if not all(os.getenv(k) for k in required):
        return None
    return {
        "consumer_key": os.getenv("TWITTER_API_KEY"),
        "consumer_secret": os.getenv("TWITTER_API_SECRET"),
        "access_token": os.getenv("TWITTER_ACCESS_TOKEN"),
        "access_token_secret": os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
    }


def _get_client() -> Optional[tweepy.Client]:
    """Initialize Twitter/X API v2 client."""
    creds = _oauth1_user()
    bearer = os.getenv("TWITTER_BEARER_TOKEN")
    if not creds or not bearer:
        return None

    return tweepy.Client(
        bearer_token=bearer,
        consumer_key=creds["consumer_key"],
        consumer_secret=creds["consumer_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
    )


def _get_api_v1() -> Optional[tweepy.API]:
    """API v1.1 client (required for media upload)."""
    creds = _oauth1_user()
    if not creds:
        return None
    auth = tweepy.OAuth1UserHandler(
        creds["consumer_key"],
        creds["consumer_secret"],
        creds["access_token"],
        creds["access_token_secret"],
    )
    return tweepy.API(auth)


def _upload_media(filename: str, media_type: Optional[str] = None) -> Optional[int]:
    """
    Upload a local media file and return media_id, or None on failure.
    Images: simple upload. Videos: chunked upload.
    """
    path = absolute_media_path(filename)
    if not path:
        print(f"[Twitter] Media file missing: {filename}")
        return None

    api = _get_api_v1()
    if api is None:
        print("[Twitter] Cannot upload media — API keys missing")
        return None

    try:
        is_video = (media_type == "video") or Path(path).suffix.lower() in {
            ".mp4", ".mov", ".m4v", ".webm"
        }
        if is_video:
            media = api.media_upload(
                filename=path,
                media_category="tweet_video",
                chunked=True,
            )
        else:
            media = api.media_upload(filename=path)
        return media.media_id
    except Exception as e:
        print(f"[Twitter] Media upload failed: {e}")
        return None


def post_tweet(
    tweet_text: str,
    article_url: Optional[str] = None,
    media_path: Optional[str] = None,
    media_type: Optional[str] = None,
    attach_media: bool = True,
) -> dict:
    """Post a tweet to Twitter/X, optionally with attached image/video."""
    client = _get_client()

    if client is None:
        return {
            "success": False,
            "error": "Twitter API keys not configured. Add them to your .env file.",
        }

    try:
        full_text = tweet_text
        if article_url and len(full_text) + len(article_url) + 1 <= MAX_TWEET_LENGTH:
            full_text = f"{tweet_text} {article_url}"
        if len(full_text) > MAX_TWEET_LENGTH:
            full_text = full_text[: MAX_TWEET_LENGTH - 3] + "..."

        media_ids = None
        media_attached = False
        if attach_media and media_path:
            media_id = _upload_media(media_path, media_type)
            if media_id is not None:
                media_ids = [media_id]
                media_attached = True

        kwargs = {"text": full_text}
        if media_ids:
            kwargs["media_ids"] = media_ids

        response = client.create_tweet(**kwargs)
        tweet_id = response.data["id"]
        return {
            "success": True,
            "tweet_id": str(tweet_id),
            "tweet_url": f"https://x.com/i/web/status/{tweet_id}",
            "tweet_text": full_text,
            "media_attached": media_attached,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
