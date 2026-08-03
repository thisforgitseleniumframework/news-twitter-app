"""App settings loaded from environment."""
import os
from dotenv import load_dotenv

load_dotenv()

# X Premium long posts support up to 25,000 characters.
# Free accounts are limited to 280 — override via MAX_TWEET_LENGTH if needed.
MAX_TWEET_LENGTH = int(os.getenv("MAX_TWEET_LENGTH", "25000"))

# Soft target for AI drafts (leave room for hashtags / URL; not a hard product limit)
AI_TWEET_TARGET_LENGTH = int(os.getenv("AI_TWEET_TARGET_LENGTH", "800"))
