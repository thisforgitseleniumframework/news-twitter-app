import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

from app.config import MAX_TWEET_LENGTH, AI_TWEET_TARGET_LENGTH

load_dotenv()


def generate_tweet(title: str, summary: str, source: str, category: str) -> str:
    """Use Gemini to generate an engaging post from a news article (Premium-length OK)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in your .env file")

    target = min(AI_TWEET_TARGET_LENGTH, MAX_TWEET_LENGTH - 50)
    prompt = f"""You are a social media manager writing posts for a news account on X (Twitter).
The account has X Premium, so posts may be longer than 280 characters (up to {MAX_TWEET_LENGTH}).

Write one engaging post based on the article below.

Article Title: {title}
Summary: {summary[:800] if summary else 'N/A'}
News Source: {source}
Region/Category: {category.upper()}

Rules:
- Aim for about {target} characters or less (can be a short thread-style single post, not a novel)
- Hard maximum: {MAX_TWEET_LENGTH} characters
- Prefer a strong hook in the first line; then key facts; end with 2-4 relevant hashtags
- Be factual, engaging, and informative
- Do NOT include a URL (it will be appended automatically when space allows)
- Return ONLY the post text, nothing else — no explanations, no quotes

Post:"""

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                http_options=types.HttpOptions(timeout=15000),  # 15 second timeout
            ),
        )
        tweet = response.text.strip().strip('"').strip("'")

        if len(tweet) > MAX_TWEET_LENGTH:
            tweet = tweet[: MAX_TWEET_LENGTH - 3] + "..."

        return tweet

    except Exception as e:
        print(f"[AIGenerator] Gemini error: {e}")
        # Fallback: build a simple post without AI
        fallback = f"{title}\n\n{summary[:400] if summary else ''}\n\n#{source.replace(' ', '')} #{category}".strip()
        return fallback[:MAX_TWEET_LENGTH]
