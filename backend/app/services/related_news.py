"""
Find related news articles that cover the SAME story (not the same category).

Previously, loose keyword hits (world/cup/football) mixed Argentina, Arsenal,
basketball, and unrelated sports into one draft. Matching is now strict.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple

from sqlalchemy.orm import Session

from app.models import NewsArticle

_STOP = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "was", "are", "were", "be", "been", "being",
    "that", "this", "these", "those", "it", "its", "into", "over", "after", "before",
    "about", "than", "then", "has", "have", "had", "will", "would", "could",
    "should", "may", "might", "not", "no", "yes", "new", "says", "said", "report",
    "reports", "latest", "update", "breaking", "live", "video", "how", "why", "what",
    "when", "who", "which", "their", "they", "them", "his", "her", "our", "your",
    # Too generic in sports / news — do NOT use for matching
    "world", "cup", "final", "match", "game", "games", "team", "teams", "player",
    "players", "sport", "sports", "football", "soccer", "cricket", "tennis",
    "basketball", "league", "premier", "transfer", "win", "won", "beat", "vs",
    "against", "first", "second", "third", "year", "years", "today", "night",
    "time", "times", "news", "star", "stars", "coach", "club", "clubs", "goal",
    "goals", "score", "scored", "international", "national", "men", "women",
    "youth", "return", "open", "end", "ends", "made", "make", "come", "came",
    "still", "just", "also", "more", "most", "only", "into", "over", "under",
}


def extract_keywords(text: str, limit: int = 14) -> List[str]:
    words = re.findall(r"[A-Za-z0-9']{3,}", (text or "").lower())
    out: List[str] = []
    seen: Set[str] = set()
    for w in words:
        if w in _STOP or w in seen or w.isdigit():
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= limit:
            break
    return out


def extract_proper_names(text: str) -> Set[str]:
    """Pull multi-word proper names and distinctive single capitals from titles."""
    names: Set[str] = set()
    # Multi-word: Enzo Fernández, Lautaro Martínez, Aston Villa
    for m in re.findall(r"\b([A-Z][a-zà-ü]+(?:\s+[A-Z][a-zà-ü]+)+)\b", text or ""):
        names.add(m.lower())
        # also last token alone if distinctive
        parts = m.split()
        if len(parts[-1]) >= 4:
            names.add(parts[-1].lower())
    # All-caps or known style: FIFA, ICC, FIBA
    for m in re.findall(r"\b([A-Z]{3,})\b", text or ""):
        if m.lower() not in _STOP:
            names.add(m.lower())
    return names


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def _token_set(text: str) -> Set[str]:
    return set(extract_keywords(text, limit=30))


def similarity_score(primary_title: str, primary_body: str, other_title: str, other_body: str) -> float:
    """
    Score how likely two articles are the same story.
    Requires shared distinctive terms / proper names — not just 'football'/'world cup'.
    """
    p_title_kw = set(extract_keywords(primary_title, limit=12))
    o_title_kw = set(extract_keywords(other_title, limit=12))
    p_names = extract_proper_names(primary_title + " " + (primary_body or "")[:200])
    o_names = extract_proper_names(other_title + " " + (other_body or "")[:200])
    p_all = _token_set(f"{primary_title} {primary_body or ''}")
    o_all = _token_set(f"{other_title} {other_body or ''}")

    title_overlap = len(p_title_kw & o_title_kw)
    name_overlap = len(p_names & o_names)
    body_j = _jaccard(p_all, o_all)
    title_j = _jaccard(p_title_kw, o_title_kw)

    score = 0.0
    score += title_overlap * 15
    score += name_overlap * 25
    score += title_j * 40
    score += body_j * 25

    # Require a proper-name overlap when either side has names (blocks "World Cup" mashups)
    if p_names or o_names:
        if name_overlap < 1 and title_overlap < 3:
            return 0.0
    else:
        # No proper names extracted — need strong title keyword overlap
        if title_overlap < 3:
            return 0.0

    if title_overlap == 0 and name_overlap == 0:
        return 0.0

    return score


def find_related_articles(
    db: Session,
    article: NewsArticle,
    limit: int = 4,
) -> List[NewsArticle]:
    """
    Return other articles that cover the SAME story (different sources when possible).
    Strict matching — empty list is better than mixing unrelated sports news.
    """
    if not article or not article.id:
        return []

    primary_title = article.title or ""
    primary_body = article.summary or ""
    keywords = extract_keywords(f"{primary_title} {primary_body}", limit=10)
    if len(keywords) < 2:
        return []

    # Prefer same category, recent only
    q = db.query(NewsArticle).filter(NewsArticle.id != article.id)
    if article.category:
        q = q.filter(NewsArticle.category == article.category)

    candidates = q.order_by(NewsArticle.fetched_at.desc()).limit(250).all()

    # If too few same-category, widen once but still score strictly
    if len(candidates) < 20:
        candidates = (
            db.query(NewsArticle)
            .filter(NewsArticle.id != article.id)
            .order_by(NewsArticle.fetched_at.desc())
            .limit(350)
            .all()
        )

    scored: List[Tuple[float, NewsArticle]] = []
    primary_url = (article.url or "").rstrip("/")

    for other in candidates:
        if other.url and other.url.rstrip("/") == primary_url:
            continue
        s = similarity_score(
            primary_title,
            primary_body,
            other.title or "",
            other.summary or "",
        )
        # High bar: only clear same-story matches
        if s < 50:
            continue
        if other.source and article.source and other.source != article.source:
            s += 5
        scored.append((s, other))

    scored.sort(key=lambda x: x[0], reverse=True)

    picked: List[NewsArticle] = []
    seen_sources: Set[str] = set()
    if article.source:
        seen_sources.add(article.source.lower())

    for s, other in scored:
        src = (other.source or f"id-{other.id}").lower()
        if src in seen_sources and s < 70:
            continue
        picked.append(other)
        seen_sources.add(src)
        if len(picked) >= min(limit, 2):  # max 2 other outlets
            break

    return picked


def sources_briefing(
    primary: NewsArticle,
    related: List[NewsArticle],
) -> List[Dict[str, Any]]:
    """Serialize primary + related for the AI prompt."""
    items = []
    for a in [primary] + list(related or []):
        items.append(
            {
                "source": a.source or "Unknown",
                "title": a.title or "",
                "summary": (a.summary or "")[:800],
                "category": a.category or "",
                "url": a.url or "",
            }
        )
    return items


def format_sources_for_prompt(items: List[Dict[str, Any]]) -> str:
    """
    Format research notes for the model. Labels stress these are INPUT only —
    the model must synthesize, not copy "According to Outlet:" into the tweet.
    """
    blocks = [
        "These are research notes only. Synthesize one post; do not quote each outlet line-by-line."
    ]
    for i, it in enumerate(items, 1):
        blocks.append(
            f"(Research note {i} | outlet={it.get('source') or 'Unknown'})\n"
            f"Headline: {it.get('title') or 'N/A'}\n"
            f"Facts: {it.get('summary') or 'N/A'}"
        )
    return "\n\n".join(blocks)


def filter_related_payload(
    primary_title: str,
    primary_summary: str,
    related_payload: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Second-pass filter for dict payloads before AI/fallback use."""
    kept = []
    for r in related_payload or []:
        s = similarity_score(
            primary_title,
            primary_summary or "",
            r.get("title") or "",
            r.get("summary") or "",
        )
        if s >= 50:
            kept.append(r)
    return kept[:2]
