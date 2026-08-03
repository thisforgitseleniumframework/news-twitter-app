"""
Score articles so breaking / high-urgency stories can be sorted first.

Signals used:
  - Explicit breaking language in title/summary
  - How fresh the item is (fetched_at / published_at)
  - Source trust weight (wire services slightly preferred)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Optional

# Phrase/keyword boosts (checked case-insensitively on title + summary)
BREAKING_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\bbreaking\b", re.I), 45, "breaking"),
    (re.compile(r"\bjust\s+in\b", re.I), 40, "just_in"),
    (re.compile(r"\balert\b", re.I), 35, "alert"),
    (re.compile(r"\burgent\b", re.I), 30, "urgent"),
    (re.compile(r"\bdeveloping\b", re.I), 28, "developing"),
    (re.compile(r"\blive\s*[:\-–]|live\s+updates?\b", re.I), 25, "live"),
    (re.compile(r"\bexclusive\b", re.I), 18, "exclusive"),
    (re.compile(r"\bflash\b", re.I), 22, "flash"),
    (re.compile(r"\bemergency\b", re.I), 30, "emergency"),
    (re.compile(r"\bexplosion\b|\bearthquake\b|\bterror\b|\battack\b", re.I), 20, "crisis"),
    (re.compile(r"\bcollapse\b|\bcrash\b|\bshot\b|\bkilled\b", re.I), 12, "incident"),
]

# Mild preference for major outlets (not a hard filter)
SOURCE_WEIGHTS: dict[str, int] = {
    "Reuters": 12,
    "BBC World": 10,
    "Al Jazeera": 8,
    "Guardian World": 8,
    "The Hindu": 7,
    "NDTV": 7,
    "Times of India": 6,
    "India Today": 6,
    "Economic Times": 5,
}

# Minimum score to show a BREAKING badge
BREAKING_BADGE_THRESHOLD = 40


def _parse_published(published_at: Optional[str]) -> Optional[datetime]:
    if not published_at:
        return None
    try:
        dt = parsedate_to_datetime(published_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    # ISO-ish fallback
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _recency_boost(article: Any, now: datetime) -> int:
    """0–35 points based on how new the story is."""
    fetched = getattr(article, "fetched_at", None)
    published = _parse_published(getattr(article, "published_at", None))

    ref = published or fetched
    if ref is None:
        return 0

    if ref.tzinfo is None:
        # Compare naive as local/UTC-agnostic
        age = now.replace(tzinfo=None) - ref.replace(tzinfo=None)
    else:
        age = now - ref.astimezone(timezone.utc)

    hours = max(age.total_seconds() / 3600.0, 0.0)

    if hours <= 1:
        return 35
    if hours <= 3:
        return 28
    if hours <= 6:
        return 20
    if hours <= 12:
        return 12
    if hours <= 24:
        return 6
    if hours <= 48:
        return 2
    return 0


def score_article(article: Any, now: Optional[datetime] = None) -> dict:
    """
    Return priority metadata for an article.

    {
      priority_score: int,
      is_breaking: bool,
      priority_reasons: list[str],
    }
    """
    now = now or datetime.now(timezone.utc)
    title = getattr(article, "title", "") or ""
    summary = getattr(article, "summary", "") or ""
    text = f"{title}\n{summary}"
    source = getattr(article, "source", "") or ""

    score = 0
    reasons: list[str] = []

    for pattern, pts, label in BREAKING_PATTERNS:
        if pattern.search(text):
            score += pts
            reasons.append(label)

    recency = _recency_boost(article, now)
    if recency:
        score += recency
        if recency >= 28:
            reasons.append("very_fresh")
        elif recency >= 12:
            reasons.append("fresh")

    src_pts = SOURCE_WEIGHTS.get(source, 0)
    if src_pts:
        score += src_pts

    # Slight bump for unprocessed so they stay actionable
    if not getattr(article, "is_processed", False):
        score += 5

    is_breaking = score >= BREAKING_BADGE_THRESHOLD and any(
        r in reasons
        for r in (
            "breaking",
            "just_in",
            "alert",
            "urgent",
            "developing",
            "live",
            "flash",
            "emergency",
            "crisis",
            "very_fresh",
        )
    )
    # Also badge pure keyword hits even if recency is lower
    keyword_hit = any(
        r in reasons
        for r in (
            "breaking",
            "just_in",
            "alert",
            "urgent",
            "developing",
            "flash",
            "emergency",
        )
    )
    if keyword_hit:
        is_breaking = True

    return {
        "priority_score": int(score),
        "is_breaking": bool(is_breaking),
        "priority_reasons": reasons,
    }
