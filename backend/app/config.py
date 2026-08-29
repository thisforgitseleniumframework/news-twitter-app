"""App settings loaded from environment."""
import os
from dotenv import load_dotenv

load_dotenv()

# Single posts (X Premium): concise long-form — 250–500 words.
# ~6 chars/word → 500 words ≈ 3000 chars.
MAX_TWEET_WORDS = int(os.getenv("MAX_TWEET_WORDS", "500"))
MIN_TWEET_WORDS = int(os.getenv("MIN_TWEET_WORDS", "250"))
if MIN_TWEET_WORDS > MAX_TWEET_WORDS:
    MIN_TWEET_WORDS = MAX_TWEET_WORDS

AI_TWEET_TARGET_WORDS = int(os.getenv("AI_TWEET_TARGET_WORDS", "350"))
if AI_TWEET_TARGET_WORDS < MIN_TWEET_WORDS:
    AI_TWEET_TARGET_WORDS = MIN_TWEET_WORDS
if AI_TWEET_TARGET_WORDS > MAX_TWEET_WORDS:
    AI_TWEET_TARGET_WORDS = MAX_TWEET_WORDS

# Character caps derived from word limits (~6 chars/word + headroom)
MAX_TWEET_LENGTH = int(os.getenv("MAX_TWEET_LENGTH", str(MAX_TWEET_WORDS * 7)))
MIN_TWEET_LENGTH = int(os.getenv("MIN_TWEET_LENGTH", str(MIN_TWEET_WORDS * 5)))
AI_TWEET_TARGET_LENGTH = int(
    os.getenv("AI_TWEET_TARGET_LENGTH", str(AI_TWEET_TARGET_WORDS * 6))
)
if AI_TWEET_TARGET_LENGTH > MAX_TWEET_LENGTH:
    AI_TWEET_TARGET_LENGTH = MAX_TWEET_LENGTH

# Related articles for multi-source drafts.
# Default 0 = PRIMARY ARTICLE ONLY (avoids sports mashups until matching is perfect).
# Set RELATED_SOURCES_LIMIT=2 to re-enable careful same-story multi-source.
RELATED_SOURCES_LIMIT = int(os.getenv("RELATED_SOURCES_LIMIT", "0"))
