import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


def generate_tweet(title: str, summary: str, source: str, category: str) -> str:
    """Use Gemini to generate an engaging tweet from a news article."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in your .env file")

    prompt = f"""You are a social media manager writing tweets for a news account.
Write a single engaging tweet based on the article below.

Article Title: {title}
Summary: {summary[:300] if summary else 'N/A'}
News Source: {source}
Region: {category.upper()}

Rules:
- Maximum 240 characters (space is reserved for the article URL)
- Add 2-3 relevant hashtags at the end
- Be factual, engaging, and informative
- Do NOT include a URL (it will be appended automatically)
- Return ONLY the tweet text, nothing else — no explanations, no quotes

Tweet:"""

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

        if len(tweet) > 240:
            tweet = tweet[:237] + "..."

        return tweet

    except Exception as e:
        print(f"[AIGenerator] Gemini error: {e}")
        fallback = f"{title[:200]} #{source.replace(' ', '')} #{category}"
        return fallback[:280]
