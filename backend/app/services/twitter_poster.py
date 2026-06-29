import os
from typing import Optional
import tweepy
from dotenv import load_dotenv

load_dotenv()


def _get_client() -> Optional[tweepy.Client]:
    """Initialize Twitter/X API v2 client."""
    required = [
        "TWITTER_BEARER_TOKEN",
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET",
    ]
    if not all(os.getenv(k) for k in required):
        return None

    return tweepy.Client(
        bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
        consumer_key=os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
    )


def post_tweet(tweet_text: str, article_url: Optional[str] = None) -> dict:
    """Post a tweet to Twitter/X. Returns success status and tweet ID."""
    client = _get_client()

    if client is None:
        return {
            "success": False,
            "error": "Twitter API keys not configured. Add them to your .env file.",
        }

    try:
        full_text = tweet_text
        if article_url and len(full_text) + len(article_url) + 1 <= 280:
            full_text = f"{tweet_text} {article_url}"

        response = client.create_tweet(text=full_text)
        tweet_id = response.data["id"]
        return {
            "success": True,
            "tweet_id": str(tweet_id),
            "tweet_url": f"https://x.com/i/web/status/{tweet_id}",
            "tweet_text": full_text,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
