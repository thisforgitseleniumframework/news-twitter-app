"""
News-to-Tweet Intelligence Engine — driven by MASTER_RULEBOOK.txt.

Pipeline:
  NEWS → research notes → Hidden Story → Verified Context
       → Best Tweet (+ Alternative) → Hashtags → Sources
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import (
    AI_TWEET_TARGET_WORDS,
    MAX_TWEET_LENGTH,
    MAX_TWEET_WORDS,
    MIN_TWEET_WORDS,
    RELATED_SOURCES_LIMIT,
)

# Project root: backend/app/services → ../../..
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_RULEBOOK_CANDIDATES = [
    _PROJECT_ROOT / "MASTER_RULEBOOK.txt",
    Path(__file__).resolve().parents[2] / "MASTER_RULEBOOK.txt",
    Path.cwd() / "MASTER_RULEBOOK.txt",
    Path.cwd().parent / "MASTER_RULEBOOK.txt",
]

_rulebook_cache: Optional[str] = None


def load_master_rulebook() -> str:
    """Load the Master Rulebook text from disk (cached)."""
    global _rulebook_cache
    if _rulebook_cache is not None:
        return _rulebook_cache

    for path in _RULEBOOK_CANDIDATES:
        try:
            if path.is_file():
                _rulebook_cache = path.read_text(encoding="utf-8", errors="replace").strip()
                if _rulebook_cache:
                    print(f"[Rulebook] Loaded {path} ({len(_rulebook_cache)} chars)")
                    return _rulebook_cache
        except Exception as e:
            print(f"[Rulebook] Failed to read {path}: {e}")

    # Minimal embedded fallback if file missing
    _rulebook_cache = (
        "Master Rulebook (embedded fallback): Discover the hidden story behind the headline. "
        "Research context, verify facts, write Hook→Context→Payoff→Ending. "
        "Human tone, no AI clichés, 0–3 hashtags, synthesize sources never dump outlets. "
        "Accuracy over virality."
    )
    print("[Rulebook] Using embedded fallback (MASTER_RULEBOOK.txt not found)")
    return _rulebook_cache


def _extract_json_object(raw: str) -> Dict[str, Any]:
    """Parse a JSON object from model output (tolerates markdown fences)."""
    text = (raw or "").strip()
    if not text:
        return {}
    # Strip ```json ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S | re.I)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _fallback_packet(
    title: str,
    summary: str,
    source: str,
    category: str,
) -> Dict[str, Any]:
    """Local packet when Gemini is unavailable — still follows structure."""
    from app.services.ai_generator import (
        _pad_to_min_length,
        build_hashtags,
        generate_engagement_tweet,
        word_count,
    )

    best = generate_engagement_tweet(
        title=title,
        summary=summary,
        source=source,
        category=category,
        related_sources=[],
        fallback_only=True,
    )
    best = _pad_to_min_length(
        best, title=title, summary=summary, related_summaries=None
    )
    # Different local angle for alternative when we only have RSS fields
    alt_hook = (
        f"What if the headline understated the story?\n\n{title}\n\n"
        f"{(summary or '').strip()}\n\n"
        f"The feed only gives the outline — the meaningful angle is what changed, "
        f"who it affects, and what readers would miss if they stopped at the title."
    )
    alt = _pad_to_min_length(
        alt_hook, title=title, summary=summary, related_summaries=None
    )
    tags = build_hashtags(title, summary, source, category)[:3]
    if tags and "#" not in best:
        room = MAX_TWEET_LENGTH - len(best) - 2
        tag_line = " ".join(tags)
        if len(tag_line) <= room:
            best = f"{best.rstrip()}\n\n{tag_line}".strip()
    return {
        "hidden_story": (
            f"Beyond the headline “{title}”: focus on what changed, who is involved, "
            f"and why this moment matters more than a one-line summary suggests."
        ),
        "verified_context": [
            f"Headline/event: {title}",
            f"Reported summary: {(summary or 'Not provided in feed.')[:500]}",
            f"Primary outlet in feed: {source or 'Unknown'}",
            "Note: Gemini unavailable — context limited to RSS fields; treat as provisional.",
        ],
        "uncertain": [
            "Broader background (career history, prior setbacks, exact timeline) not verified from feed alone."
        ],
        "best_tweet": best[:MAX_TWEET_LENGTH],
        "alternative_tweet": alt[:MAX_TWEET_LENGTH],
        "hashtags": tags,
        "sources": [source] if source else [],
        "word_count": word_count(best),
        "rulebook": True,
        "mode": "fallback_local",
    }


def generate_rulebook_packet(
    title: str,
    summary: str,
    source: str,
    category: str,
    related_sources: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    """
    Full Master Rulebook pipeline (§17 output shape).

    Returns dict with:
      hidden_story, verified_context, uncertain,
      best_tweet, alternative_tweet, hashtags, sources, word_count
    """
    from app.services.ai_generator import (
        _generate,
        _looks_like_outlet_dump,
        _pad_to_min_length,
        _sanitize_to_single_story,
        _strip_banned_boilerplate,
        _trim_to_max_words,
        build_hashtags,
        word_count,
    )
    from app.services.related_news import filter_related_payload, format_sources_for_prompt

    title = (title or "").strip()
    summary = (summary or "").strip()
    source = (source or "").strip()
    category = (category or "news").strip()

    if RELATED_SOURCES_LIMIT <= 0:
        related_sources = []
    else:
        related_sources = filter_related_payload(
            title, summary, related_sources or []
        )[:RELATED_SOURCES_LIMIT]

    rulebook = load_master_rulebook()

    if related_sources:
        sources_block = format_sources_for_prompt(
            [
                {
                    "source": source or "Unknown",
                    "title": title,
                    "summary": summary,
                }
            ]
            + related_sources
        )
    else:
        sources_block = (
            f"(Research note 1 | outlet={source or 'Unknown'})\n"
            f"Headline: {title}\n"
            f"Facts: {summary or 'N/A'}"
        )

    source_names = [source] if source else []
    for r in related_sources:
        s = (r.get("source") or "").strip()
        if s and s not in source_names:
            source_names.append(s)

    prompt = f"""You are the News-to-Tweet Intelligence Engine.

Follow this Master Rulebook EXACTLY (it is your constitution for this task):

======= MASTER RULEBOOK START =======
{rulebook}
======= MASTER RULEBOOK END =======

ADDITIONAL HARD CONSTRAINTS FOR THIS APP:
- Write about ONE story only (primary headline below). Ignore off-topic research notes.
- best_tweet and alternative_tweet length: {MIN_TWEET_WORDS}–{MAX_TWEET_WORDS} words (aim ~{AI_TWEET_TARGET_WORDS}).
- Hard character cap per tweet: {MAX_TWEET_LENGTH}.
- NEVER paste outlet dumps ("According to ESPN:", "Reporting drawn from:").
- NEVER invent facts. Mark uncertainty in the uncertain array.
- hashtags: 0–3 only.
- alternative_tweet must be a DIFFERENT angle (emotional/human OR analytical), not a paraphrase.
- Return ONLY valid JSON (no markdown fences) with exactly these keys:
{{
  "hidden_story": "string — what people miss if they only read the headline",
  "verified_context": ["fact1", "fact2", "..."],
  "uncertain": ["claim that is not fully verified", "..."],
  "best_tweet": "full post text ready to publish",
  "alternative_tweet": "different-angle full post text",
  "hashtags": ["#Tag1", "#Tag2"]
}}

PRIMARY HEADLINE: {title}
CATEGORY: {category.upper()}
PRIMARY OUTLET: {source or "Unknown"}

=== RESEARCH NOTES (input only — do not paste into tweets) ===
{sources_block}
=== END RESEARCH NOTES ===

Produce the JSON packet now:"""

    fallback_packet = _fallback_packet(title, summary, source, category)

    # Empty string fallback: if Gemini fails, _generate returns "" and we use local packet.
    # Do NOT pass the JSON packet as fallback — _generate would mangle it and we'd
    # mislabel local output as gemini_rulebook.
    try:
        raw = _generate(
            prompt,
            "",
            enforce_min=False,
            title=title,
            summary=summary,
        )
    except Exception as e:
        print(f"[Rulebook] Generation failed: {e}")
        return fallback_packet

    data = _extract_json_object(raw)
    if not data or not (data.get("best_tweet") or "").strip():
        # Try to treat raw as tweet if JSON failed but we got prose
        if raw and not raw.strip().startswith("{") and word_count(raw) >= 40:
            data = {
                "hidden_story": fallback_packet["hidden_story"],
                "verified_context": fallback_packet["verified_context"],
                "uncertain": fallback_packet["uncertain"],
                "best_tweet": raw.strip(),
                "alternative_tweet": raw.strip(),
                "hashtags": fallback_packet["hashtags"],
            }
            mode = "raw_tweet_fallback"
        else:
            print("[Rulebook] Empty/invalid Gemini JSON — using local fallback packet")
            return fallback_packet
    else:
        mode = "gemini_rulebook"

    best = str(data.get("best_tweet") or "").strip()
    alt = str(data.get("alternative_tweet") or "").strip() or best

    best = _strip_banned_boilerplate(best)
    best = _sanitize_to_single_story(best, title, summary)
    best = _trim_to_max_words(best, MAX_TWEET_WORDS)[:MAX_TWEET_LENGTH]
    best = _pad_to_min_length(best, title=title, summary=summary, related_summaries=None)
    best = _trim_to_max_words(best, MAX_TWEET_WORDS)[:MAX_TWEET_LENGTH]

    alt = _strip_banned_boilerplate(alt)
    alt = _sanitize_to_single_story(alt, title, summary)
    alt = _trim_to_max_words(alt, MAX_TWEET_WORDS)[:MAX_TWEET_LENGTH]
    alt = _pad_to_min_length(alt, title=title, summary=summary, related_summaries=None)
    alt = _trim_to_max_words(alt, MAX_TWEET_WORDS)[:MAX_TWEET_LENGTH]

    if _looks_like_outlet_dump(best) or word_count(best) < 40:
        print("[Rulebook] best_tweet looked like dump/empty — using local fallback tweet")
        return fallback_packet

    # Detect Gemini echoing the local template (API key invalid / refused)
    fb_hidden = str(fallback_packet.get("hidden_story") or "")
    hidden = str(data.get("hidden_story") or "").strip()
    if hidden and fb_hidden and hidden.strip() == fb_hidden.strip() and mode == "gemini_rulebook":
        print("[Rulebook] Response matched local template — treating as fallback_local")
        return fallback_packet
    if not hidden:
        hidden = fb_hidden

    tags = data.get("hashtags") or []
    if not isinstance(tags, list):
        tags = []
    tags = [str(t).strip() for t in tags if str(t).strip()][:3]
    if not tags:
        tags = build_hashtags(title, summary, source, category)[:3]

    # Ensure hashtags appear in tweet if model forgot them
    if tags and "#" not in best:
        room = MAX_TWEET_LENGTH - len(best) - 2
        tag_line = " ".join(tags)
        if len(tag_line) <= room:
            best = f"{best.rstrip()}\n\n{tag_line}".strip()

    verified = data.get("verified_context") or []
    if not isinstance(verified, list):
        verified = [str(verified)]
    verified = [str(v).strip() for v in verified if str(v).strip()]

    uncertain = data.get("uncertain") or []
    if not isinstance(uncertain, list):
        uncertain = [str(uncertain)] if uncertain else []
    uncertain = [str(v).strip() for v in uncertain if str(v).strip()]

    return {
        "hidden_story": hidden,
        "verified_context": verified or fallback_packet["verified_context"],
        "uncertain": uncertain,
        "best_tweet": best,
        "alternative_tweet": alt,
        "hashtags": tags,
        "sources": source_names,
        "word_count": word_count(best),
        "rulebook": True,
        "mode": mode,
    }
