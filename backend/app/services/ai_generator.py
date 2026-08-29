import os
import re
from typing import List, Optional

from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - dependency may be absent in local envs
    genai = None
    types = None

from app.config import (
    MAX_TWEET_LENGTH,
    MIN_TWEET_LENGTH,
    MIN_TWEET_WORDS,
    MAX_TWEET_WORDS,
    AI_TWEET_TARGET_LENGTH,
    AI_TWEET_TARGET_WORDS,
)

load_dotenv()

# Soft target per thread tweet (classic scroll-stopping length; Premium allows more)
THREAD_PART_TARGET = min(int(os.getenv("THREAD_PART_TARGET", "320")), MAX_TWEET_LENGTH)
THREAD_MIN_PARTS = 2
THREAD_MAX_PARTS = 3


def _client():
    if genai is None or types is None:
        raise RuntimeError("google-genai is not installed")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in your .env file")
    return genai.Client(api_key=api_key)


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text or ""))


def _trim_to_max_words(text: str, max_words: int = MAX_TWEET_WORDS) -> str:
    """Hard-cap draft length by words (keeps sentence-ish ending when possible)."""
    text = (text or "").strip()
    words = re.findall(r"\S+", text)
    if len(words) <= max_words:
        return text
    clipped = " ".join(words[:max_words]).rstrip()
    # Prefer ending on sentence punctuation if we cut mid-sentence
    if not re.search(r"[.!?…][\"')\]]*$", clipped):
        # try pull back to last sentence end within last 40 tokens
        m = list(re.finditer(r"[.!?…]", clipped))
        if m and m[-1].end() > len(clipped) * 0.6:
            clipped = clipped[: m[-1].end()].strip()
        else:
            clipped = clipped.rstrip(",;:") + "…"
    return clipped


_BANNED_BOILERPLATE = [
    "here's the context readers need",
    "not just a headline",
    "follow developments closely",
    "shapes the wider conversation",
    "stay informed as details emerge",
    "stories defining the news cycle",
    "avoid unverified claims",
    "we’ll keep tracking verified updates",
    "we'll keep tracking verified updates",
    "this story is still developing",
    "lorem ipsum",
    "dummy text",
    "placeholder",
    "as an ai",
    "i cannot",
    "core headline:",
    "reporting drawn from:",
    "key takeaway:",
    "in today's fast-paced",
    "in conclusion",
    "it is important to note",
    "without further ado",
    "according to espn",
    "according to ndtv",
    "according to the hindu",
    "according to al jazeera",
    "according to guardian",
    "according to times of india",
    "according to toi",
    "here's what we know",
    "this is the latest update",
    "in other news",
    "what matters now",
    "the latest development",
    # Master Rulebook §6 — no AI-sounding clichés
    "this is more than just",
    "it's not just about",
    "a testament to",
    "the journey continues",
    "against all odds",
    "little did he know",
    "little did she know",
    "dreams do come true",
    "the entire nation",
    "nobody believed in him",
    "everyone had given up",
]

# Master Rulebook: News-to-Tweet Intelligence Engine (project: MASTER_RULEBOOK.txt)
_HUMAN_VOICE_GUIDE = """
You are a Researcher + Fact-checker + Story analyst + Social-media strategist + X writer.

GOLDEN RULE: Don't write a tweet just because something happened. Find why it matters,
what happened before it, and what people would miss if they only read the headline.
Pipeline: NEWS → CONTEXT → HIDDEN STORY → VERIFIED FACTS → HUMAN INSIGHT → ENGAGING POST

HIDDEN STORY: Never stop at the obvious headline. Prefer angles like comeback, long wait,
setbacks, preparation, surprising statistic, contradiction, or larger context — only if
supported by the research notes. Every post should teach something beyond the headline.

STRUCTURE (when the material supports it):
1) HOOK — strongest insight / surprise / contrast. Do NOT merely restate the headline.
2) CONTEXT — brief before: struggle, wait, prior failure, preparation (only if relevant).
3) PAYOFF — return to the current event; why it matters because of what came before.
4) ENDING — memorable line, observation, contrast, OR a genuine question (only if useful).
   Do NOT auto-append "What do you think?" to every post.

VOICE: Natural, specific, conversational, intelligent, emotionally authentic.
Write like a sharp human storyteller — never a press release or motivational poster.

MULTI-SOURCE: Research notes may include several outlets on the SAME story. Output must be
ONE synthesized voice. NEVER paste "According to ESPN:…", "According to NDTV:…", or
"Reporting drawn from:…". Merge facts; at most one light outlet mention if needed.

FACTS: Only confirmed facts from the notes. No invented quotes, stats, or drama.
Uncertainty → omit or mark as uncertain. Accuracy > virality.

HASHTAGS: 0–3 highly relevant tags only (discovery, not spam).

OPENING: First line under ~20 words. Never start with Breaking:/Just in:/According to.
"""


def _strip_banned_boilerplate(text: str) -> str:
    """Remove template filler and multi-source dump sections."""
    if not text:
        return ""

    # Cut off entire dump footers (anywhere in the post)
    for marker in (
        r"(?is)\n\s*reporting drawn from\s*:.*$",
        r"(?is)\n\s*sources\s*:\s*[A-Za-z].*$",
        r"(?is)\n\s*drawn from\s*:.*$",
    ):
        text = re.sub(marker, "", text)

    lines = []
    for line in text.splitlines():
        low = line.strip().lower()
        if not low:
            lines.append("")
            continue
        if any(b in low for b in _BANNED_BOILERPLATE):
            continue
        # Drop "According to Outlet: ..." mashup lines
        if re.match(r"^according to\s+.+:", low):
            continue
        if "reporting drawn from" in low:
            continue
        if low.startswith("sources:") and ("," in low or "toi" in low or "espn" in low):
            continue
        # Drop pasted "Outlet Name: full blurb" research lines
        if re.match(
            r"^(espn|ndtv|bbc|reuters|guardian|toi|times of india|al jazeera|"
            r"the hindu|sky sports|indian express)[^:]{0,40}:\s+\S+",
            low,
        ):
            continue
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def _is_on_topic_block(block: str, title: str, summary: str) -> bool:
    """Reject padding blocks that look like a different story."""
    from app.services.related_news import similarity_score

    block = (block or "").strip()
    if not block:
        return False
    # Strip leading "Source: " / "According to X:" labels for scoring
    cleaned = re.sub(
        r"^(according to|via|source)\s+[^:]{1,40}:\s*",
        "",
        block,
        flags=re.I,
    ).strip()
    # Use first sentence as pseudo-title
    pseudo_title = cleaned.split(".")[0][:120]
    score = similarity_score(title or "", summary or "", pseudo_title, cleaned)
    # Also allow if block clearly shares 2+ distinctive keywords with primary title
    if score >= 30:
        return True
    from app.services.related_news import extract_keywords

    tkw = set(extract_keywords(title or "", limit=10))
    bkw = set(extract_keywords(cleaned, limit=14))
    return len(tkw & bkw) >= 2


def _expand_with_source_facts(
    text: str,
    title: str = "",
    summary: str = "",
    related_summaries: Optional[List[str]] = None,
) -> str:
    """
    Grow a short draft using ONLY on-topic article facts.
    Never inject off-topic sports dumps or dummy fluff. Cap at MAX_TWEET_WORDS.
    """
    text = _strip_banned_boilerplate((text or "").strip())
    text = _trim_to_max_words(text, MAX_TWEET_WORDS)
    if word_count(text) >= MIN_TWEET_WORDS:
        return text[:MAX_TWEET_LENGTH]

    chunks: List[str] = []
    # Primary summary/title first (always on-topic)
    for block in [summary, title]:
        block = (block or "").strip()
        if not block:
            continue
        sample = block[:80].lower()
        if sample and sample in text.lower():
            continue
        chunks.append(block)

    # Related only if same story
    for block in list(related_summaries or []):
        block = (block or "").strip()
        if not block:
            continue
        if not _is_on_topic_block(block, title, summary):
            continue
        sample = block[:80].lower()
        if sample and sample in text.lower():
            continue
        chunks.append(block)

    for block in chunks:
        if word_count(text) >= MIN_TWEET_WORDS:
            break
        if word_count(text) >= MAX_TWEET_WORDS:
            break
        room = MAX_TWEET_LENGTH - len(text)
        if room <= 40:
            break
        addition = f"\n\n{block}" if text else block
        if len(addition) > room:
            addition = addition[: room - 3].rstrip() + "..."
        text = f"{text}{addition}".strip()
        text = _trim_to_max_words(text, MAX_TWEET_WORDS)

    return text[:MAX_TWEET_LENGTH]


def _pad_to_min_length(
    text: str,
    title: str = "",
    summary: str = "",
    related_summaries: Optional[List[str]] = None,
) -> str:
    """Ensure draft meets min words using real multi-source facts only."""
    return _expand_with_source_facts(
        text,
        title=title,
        summary=summary,
        related_summaries=related_summaries,
    )


def _generate(
    prompt: str,
    fallback: str,
    *,
    enforce_min: bool = True,
    title: str = "",
    summary: str = "",
    related_summaries: Optional[List[str]] = None,
) -> str:
    try:
        client = _client()
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                http_options=types.HttpOptions(timeout=45000),
            ),
        )
        tweet = (response.text or "").strip().strip('"').strip("'")
        tweet = _strip_banned_boilerplate(tweet)
        tweet = _trim_to_max_words(tweet, MAX_TWEET_WORDS)
        if len(tweet) > MAX_TWEET_LENGTH:
            tweet = tweet[: MAX_TWEET_LENGTH - 3] + "..."
        tweet = tweet or _trim_to_max_words(
            _strip_banned_boilerplate(fallback), MAX_TWEET_WORDS
        )[:MAX_TWEET_LENGTH]
        if enforce_min:
            tweet = _pad_to_min_length(
                tweet,
                title=title,
                summary=summary,
                related_summaries=related_summaries,
            )
            # One expansion retry if still under word min
            if word_count(tweet) < MIN_TWEET_WORDS:
                expand_prompt = f"""Rewrite this news post so it feels human and likable on X.
Length: {MIN_TWEET_WORDS}–{MAX_TWEET_WORDS} words (aim ~{AI_TWEET_TARGET_WORDS}).
Use ONLY the facts below. No invented details. No dummy text. No URLs.
Warm, clear, conversational — someone should want to like and reply.
Keep under {MAX_TWEET_LENGTH} characters. Return only the post.

Current draft:
{tweet}

Primary title: {title}
Primary summary: {summary}
Additional source notes:
{(chr(10).join(related_summaries or []) or 'None')}
"""
                try:
                    resp2 = client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=expand_prompt,
                        config=types.GenerateContentConfig(
                            http_options=types.HttpOptions(timeout=45000),
                        ),
                    )
                    expanded = _strip_banned_boilerplate(
                        (resp2.text or "").strip().strip('"').strip("'")
                    )
                    expanded = _trim_to_max_words(expanded, MAX_TWEET_WORDS)
                    if word_count(expanded) >= MIN_TWEET_WORDS or word_count(expanded) > word_count(tweet):
                        tweet = expanded[:MAX_TWEET_LENGTH]
                        tweet = _pad_to_min_length(
                            tweet,
                            title=title,
                            summary=summary,
                            related_summaries=related_summaries,
                        )
                except Exception as e2:
                    print(f"[AIGenerator] Expand retry failed: {e2}")
        tweet = _trim_to_max_words(tweet, MAX_TWEET_WORDS)
        return tweet[:MAX_TWEET_LENGTH]
    except Exception as e:
        print(f"[AIGenerator] Gemini error: {e}")
        fb = _trim_to_max_words(
            _strip_banned_boilerplate(fallback), MAX_TWEET_WORDS
        )[:MAX_TWEET_LENGTH]
        if enforce_min:
            fb = _pad_to_min_length(
                fb,
                title=title,
                summary=summary,
                related_summaries=related_summaries,
            )
        return _trim_to_max_words(fb, MAX_TWEET_WORDS)[:MAX_TWEET_LENGTH]


def _hashtag_token(trend_name: str, trend_query: str) -> str:
    """Build a single hashtag token from a trend label."""
    raw = (trend_name or trend_query or "").strip()
    if raw.startswith("#"):
        return raw.split()[0]
    parts = re.findall(r"[A-Za-z0-9]+", trend_query or raw)
    if not parts:
        return ""
    if len(parts) == 1:
        return f"#{parts[0]}"
    return "#" + "".join(p[:1].upper() + p[1:] for p in parts)


def ensure_hashtag(text: str, trend_name: str, trend_query: str) -> str:
    """Append trend hashtag if missing (case-insensitive)."""
    tag = _hashtag_token(trend_name, trend_query)
    if not tag:
        return text
    if re.search(re.escape(tag), text or "", flags=re.I):
        return text
    candidate = f"{(text or '').rstrip()}\n\n{tag}".strip()
    if len(candidate) <= MAX_TWEET_LENGTH:
        return candidate
    room = MAX_TWEET_LENGTH - len(tag) - 2
    if room < 20:
        return text[:MAX_TWEET_LENGTH]
    return f"{text[:room].rstrip()}\n\n{tag}"


def _trim_to_limit(text: str) -> str:
    if not text:
        return ""
    if len(text) <= MAX_TWEET_LENGTH:
        return text
    return text[: MAX_TWEET_LENGTH - 3] + "..."


def _normalize_tag(value: str) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", value).strip()
    if not cleaned:
        return ""
    if cleaned.lower() in {"the", "and", "for", "with", "from"}:
        return ""
    return cleaned[:25] if cleaned else ""


def _extract_sports_entities(title: str, summary: str) -> List[str]:
    text = f"{title or ''} {summary or ''}".strip()
    if not text:
        return []

    lower = text.lower()
    sport_keywords = [
        "football",
        "soccer",
        "cricket",
        "tennis",
        "basketball",
        "rugby",
        "golfer",
        "player",
        "club",
        "manager",
        "transfer",
        "match",
        "final",
        "league",
        "cup",
        "tournament",
    ]
    player_map = {
        "cristiano ronaldo": "Cristiano Ronaldo",
        "ronaldo": "Cristiano Ronaldo",
        "messi": "Messi",
        "lionel messi": "Lionel Messi",
        "virat kohli": "Virat Kohli",
        "rohit sharma": "Rohit Sharma",
        "neymar": "Neymar",
        "mbappe": "Mbappe",
        "kylian mbappe": "Kylian Mbappe",
        "haaland": "Erling Haaland",
        "mohamed salah": "Mohamed Salah",
        "kevin de bruyne": "Kevin De Bruyne",
        "djokovic": "Novak Djokovic",
        "novak djokovic": "Novak Djokovic",
        "lebron james": "LeBron James",
        "lebron": "LeBron James",
        "james": "LeBron James",
    }
    club_map = {
        "al-nassr": "Al-Nassr",
        "al nassr": "Al-Nassr",
        "manchester united": "Manchester United",
        "barcelona": "Barcelona",
        "real madrid": "Real Madrid",
        "paris saint germain": "Paris Saint-Germain",
        "psg": "Paris Saint-Germain",
        "bayern munich": "Bayern Munich",
        "bayern": "Bayern Munich",
        "inter miami": "Inter Miami",
        "al hilal": "Al-Hilal",
        "al ahli": "Al-Ahli",
    }
    country_map = {
        "portuguese": "Portugal",
        "portugal": "Portugal",
        "argentine": "Argentina",
        "argentina": "Argentina",
        "england": "England",
        "india": "India",
        "brazil": "Brazil",
        "spain": "Spain",
        "france": "France",
        "germany": "Germany",
    }

    if not any(keyword in lower for keyword in sport_keywords) and not any(keyword in lower for keyword in player_map):
        return []

    entities = []
    for keyword, entity in player_map.items():
        if keyword in lower:
            entities.append(entity)

    if "lebron james" in lower:
        entities.append("LeBron James")
    if "novak djokovic" in lower:
        entities.append("Novak Djokovic")
    for keyword, entity in club_map.items():
        if keyword in lower:
            entities.append(entity)
    for keyword, entity in country_map.items():
        if keyword in lower:
            entities.append(entity)

    unique = []
    for entity in entities:
        entity = entity.strip()
        if entity and entity not in unique:
            unique.append(entity)
    return unique[:4]


def build_hashtags(title: str, summary: str, source: str, category: str) -> List[str]:
    """Create smarter hashtags — topic first, source last (and only if useful)."""
    category_key = (category or "news").lower()
    hashtags: List[str] = []
    blob = f"{title or ''} {summary or ''}".lower()

    # Topic tags from content
    if "cricket" in blob or "icc" in blob:
        hashtags.append("#Cricket")
    if "icc" in blob or "anti-corruption" in blob or "anti corruption" in blob:
        hashtags.append("#ICC")
    if "ban" in blob and ("corrupt" in blob or "icc" in blob):
        hashtags.append("#AntiCorruption")

    if category_key == "sports" or category_key.startswith("sports_"):
        entities = _extract_sports_entities(title, summary)
        for entity in entities:
            normalized = _normalize_tag(entity)
            if normalized and normalized.lower() not in {"the", "and"}:
                hashtag = f"#{normalized}"
                if hashtag not in hashtags:
                    hashtags.append(hashtag)
        # Pull proper-ish names from title (2+ capitalized words)
        for m in re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", title or ""):
            normalized = _normalize_tag(m)
            if normalized and len(normalized) > 4:
                tag = f"#{normalized}"
                if tag not in hashtags:
                    hashtags.append(tag)
        if not any(h.lower() == "#sports" for h in hashtags) and len(hashtags) < 2:
            hashtags.append("#Sports")
    else:
        for word in re.findall(r"[A-Za-z0-9]{4,}", title or "")[:4]:
            normalized = _normalize_tag(word)
            if normalized and normalized.lower() not in {"this", "that", "with", "from", "have"}:
                tag = f"#{normalized}"
                if tag not in hashtags:
                    hashtags.append(tag)
        if category_key and category_key not in {"news", "global", "india"}:
            hashtags.append(f"#{category_key.title()}")

    # Source last, only if we still have room and it isn't the only tag
    source_tag = _normalize_tag(source or "")
    if source_tag and len(hashtags) < 3:
        hashtags.append(f"#{source_tag}")

    # Dedupe case-insensitively
    out: List[str] = []
    seen = set()
    for h in hashtags:
        key = h.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
        if len(out) >= 4:
            break
    return out


def _build_fallback_variants(
    title: str,
    summary: str,
    source: str,
    category: str,
    trend_name: Optional[str] = None,
    trend_query: Optional[str] = None,
    related_sources: Optional[List[dict]] = None,
) -> List[str]:
    """Human-sounding drafts for ONE story only — never mash unrelated sports."""
    from app.services.related_news import filter_related_payload

    base_title = (title or "").strip()
    base_summary = (summary or "").strip()
    related_sources = filter_related_payload(
        base_title, base_summary, related_sources or []
    )
    hashtag_suffix = " ".join(build_hashtags(title, summary, source, category))
    tag = _hashtag_token(trend_name, trend_query)
    outlet = source or "reports"

    extras: List[str] = []
    for r in related_sources:
        bit = (r.get("summary") or "").strip()
        if bit and bit.lower() not in (base_summary or "").lower():
            # Weave fact only — no "According to Outlet:" labels
            extras.append(bit)

    main = base_summary if base_summary else base_title
    extra_block = "\n\n".join(extras[:2])

    v1 = (
        f"{base_title}\n\n"
        f"{main}\n\n"
        f"{(extra_block + chr(10) + chr(10)) if extra_block else ''}"
        f"This is the kind of story that can change the conversation fast. "
        f"What part of it matters most to you right now?\n\n"
        f"(via {outlet}"
        f"{' + others covering the same story' if related_sources else ''})\n\n"
        f"{hashtag_suffix}"
    ).strip()

    v2 = (
        f"{base_title}\n\n"
        f"Here's the part people are likely to miss: {main}\n\n"
        f"{(extra_block + chr(10) + chr(10)) if extra_block else ''}"
        f"The stakes feel bigger than the headline, and that's why this one is getting attention. "
        f"How are you reading it?\n\n"
        f"{hashtag_suffix}"
    ).strip()

    v3 = (
        f"{main}\n\n"
        f"That headline is only part of the story. The real question is what happens next.\n\n"
        f"{(extra_block + chr(10) + chr(10)) if extra_block else ''}"
        f"If you were watching this unfold, what would you flag first?\n\n"
        f"{hashtag_suffix}"
    ).strip()

    variants = [v1, v2, v3]
    if tag:
        variants = [ensure_hashtag(v, trend_name or tag, trend_query or tag) for v in variants]
    # Only on-topic text for length padding — never raw "ESPN: basketball…" dumps
    related_summ = [r.get("summary") or "" for r in related_sources if r.get("summary")]
    return [
        _trim_to_limit(
            _pad_to_min_length(
                _strip_banned_boilerplate(v),
                title=base_title,
                summary=base_summary,
                related_summaries=related_summ,
            )
        )
        for v in variants
    ]


def _inject_hashtags(text: str, title: str, summary: str, source: str, category: str) -> str:
    """Append a compact hashtag block when the draft is missing one."""
    if not text:
        return text
    hashtags = build_hashtags(title, summary, source, category)
    if not hashtags:
        return text
    if any(tag in text for tag in hashtags):
        return text
    candidate = f"{text.rstrip()}\n\n{' '.join(hashtags)}".strip()
    return candidate[:MAX_TWEET_LENGTH]


def _rewrite_if_generic(text: str, fallback: str, title: str, summary: str) -> str:
    """Prefer the fallback when the draft is too generic or bland."""
    if not text:
        return fallback or ""
    lower = (text or "").lower()
    generic_patterns = [
        "here's what we know",
        "this is the latest update",
        "the latest development",
        "what matters now",
        "in other news",
    ]
    if any(pattern in lower for pattern in generic_patterns):
        return fallback or text
    if "?" not in text and len(text.split()) < 55:
        return fallback or text
    if text.startswith((title or "").strip()) and len(text.split()) < 70:
        return fallback or text
    return text


def _build_engagement_variants(
    title: str,
    summary: str,
    source: str,
    category: str,
    related_sources: Optional[List[dict]] = None,
) -> List[str]:
    """Compose several distinct fallback drafts and return the strongest one."""
    base_title = (title or "").strip() or "A major story is developing"
    base_summary = (summary or "").strip()
    if base_summary:
        if len(base_summary) > 240:
            base_summary = base_summary[:237].rstrip() + "..."
    else:
        base_summary = "The latest updates are still unfolding, and the stakes are becoming clearer by the hour."

    if category and category.lower().startswith("sports"):
        cta = "What do you think matters most here — the result, the reaction, or what happens next?"
        tone = "This is the kind of update that can change the entire conversation around a game or a rivalry."
    else:
        cta = "What do you think matters most here — the impact, the reaction, or what happens next?"
        tone = "This is the sort of update that can change the tone of the whole conversation."

    hashtags = " ".join(build_hashtags(title, summary, source, category))
    variants = [
        (
            f"{base_title}\n\n"
            f"{base_summary}\n\n"
            f"{tone} {cta}\n\n"
            f"{hashtags}"
        ).strip(),
        (
            f"{base_title}\n\n"
            f"Here's the part people are likely to miss: {base_summary}\n\n"
            f"The stakes feel bigger than the headline, and that's why this one is getting attention. "
            f"How are you reading it?\n\n"
            f"{hashtags}"
        ).strip(),
        (
            f"{base_summary}\n\n"
            f"That headline is only part of the story. The real question is what happens next.\n\n"
            f"If you were watching this unfold, what would you flag first?\n\n"
            f"{hashtags}"
        ).strip(),
    ]

    scored = []
    for variant in variants:
        cleaned = _trim_to_limit(_pad_to_min_length(
            _strip_banned_boilerplate(variant),
            title=title,
            summary=summary,
            related_summaries=[r.get("summary") or "" for r in (related_sources or []) if r.get("summary")],
        ))
        scored.append((score_tweet_variant(cleaned), cleaned))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [text for _, text in scored]


def score_tweet_variant(text: str) -> int:
    """Reward posts built for X revenue-share: replies, dwell, original voice."""
    value = 0
    text = text or ""
    lower = text.lower()
    try:
        from app.services.x_revenue import score_content_for_x_revenue
        value += int((score_content_for_x_revenue(text).get("score") or 0) * 0.55)
    except Exception:
        pass
    n = len(text)
    words = word_count(text)

    if n <= MAX_TWEET_LENGTH:
        value += 8
    if MIN_TWEET_WORDS <= words <= MAX_TWEET_WORDS:
        value += 30
    elif words < MIN_TWEET_WORDS:
        value -= 25
        value -= max(0, (MIN_TWEET_WORDS - words) // 10)
    elif words > MAX_TWEET_WORDS:
        value -= 20
        value -= max(0, (words - MAX_TWEET_WORDS) // 10)

    # Human / engagement signals
    if text.count("\n") >= 2:
        value += 6
    if "?" in text:
        value += 10
    if re.search(r"\b(you|your|we|we're|let's|honestly|look|here's what|how are you|what do you think)\b", lower):
        value += 14
    if re.search(r"\b(worth|stands out|talking about|curious|think|feel|matters most|bigger than the headline)\b", lower):
        value += 10
    if re.search(r"\b(it's|don't|won't|can't|here's|that's|what's)\b", lower):
        value += 6  # natural contractions
    # Hidden-story / contrast signals (Master Rulebook)
    if re.search(r"\b(before|after|wait|waiting|return|comeback|years?|months?|first|record|never|almost)\b", lower):
        value += 8
    if re.search(r"\b(this is the sort|here's the part|real question|conversation fast|stokes|change the tone)\b", lower):
        value += 8
    # Prefer 0–3 hashtags
    hash_count = lower.count("#")
    if 0 <= hash_count <= 3:
        value += 6
    elif hash_count > 5:
        value -= 10
    if re.search(r"\b\d+\b", text):
        value += 8

    # Empty auto-question penalty
    if re.search(r"what do you think\?\s*$", lower) and "why" not in lower[:80]:
        value -= 6

    acc = lower.count("according to")
    if acc == 0:
        value += 4
    elif acc >= 2:
        value -= 20

    if "sources:" in lower or "reporting drawn" in lower or "core headline:" in lower:
        value -= 15

    if re.search(r"\b(rt if|retweet if|like if|follow me|link in bio|tag a friend)\b", lower):
        value -= 40

    for phrase in _BANNED_BOILERPLATE:
        if phrase in lower:
            value -= 50
    if n > MAX_TWEET_LENGTH:
        value -= 20
    if words < 100:
        value -= 20
    return value


def generate_tweet_variants(
    title: str,
    summary: str,
    source: str,
    category: str,
    fallback_only: bool = False,
    trend_name: Optional[str] = None,
    trend_query: Optional[str] = None,
    related_sources: Optional[List[dict]] = None,
) -> List[str]:
    """
    Create engaging long-form posts by consolidating sources in a human voice.
    Target: MIN_TWEET_WORDS–MAX_TWEET_WORDS, likable, no dummy text.
    """
    # Drop off-topic "related" items (prevents sports mashups)
    from app.services.related_news import filter_related_payload

    related_sources = filter_related_payload(
        title, summary or "", related_sources or []
    )
    related_summaries = [
        f"{r.get('source')}: {r.get('title')} — {r.get('summary')}"
        for r in related_sources
        if r.get("title") or r.get("summary")
    ]
    all_summaries = [summary or ""] + [
        (r.get("summary") or "") for r in related_sources
    ]
    combined_summary = "\n".join(s for s in all_summaries if s).strip() or summary

    fallback_variants = _build_fallback_variants(
        title=title,
        summary=combined_summary or summary,
        source=source,
        category=category,
        trend_name=trend_name,
        trend_query=trend_query,
        related_sources=related_sources,
    )
    if fallback_only:
        return fallback_variants

    if related_sources:
        from app.services.related_news import format_sources_for_prompt

        sources_block = format_sources_for_prompt(
            [
                {
                    "source": source,
                    "title": title,
                    "summary": summary or "",
                }
            ]
            + related_sources
        )
    else:
        sources_block = (
            f"[Source 1: {source or 'Unknown'}]\n"
            f"Title: {title}\n"
            f"Summary: {summary[:1200] if summary else 'N/A'}"
        )

    word_rules = (
        f"LENGTH: between {MIN_TWEET_WORDS} and {MAX_TWEET_WORDS} words "
        f"(aim ~{AI_TWEET_TARGET_WORDS}). Hard cap {MAX_TWEET_LENGTH} characters. "
        "Use only the length the story needs — no filler padding."
    )
    ban_rules = (
        "NEVER invent facts/quotes. NEVER use dummy text. "
        "NEVER use clichés: 'This is more than just…', 'testament to…', 'against all odds…', "
        "'dreams do come true…', 'the journey continues…', 'little did they know…'. "
        "NEVER spam: 'Here's the context readers need', 'in conclusion', stacked 'According to…'."
    )
    same_story_rules = (
        "CRITICAL — SAME STORY ONLY: Research notes are for ONE event "
        f"(primary title: {title}). "
        "If a block is a different match, transfer, sport, country, or event, IGNORE it. "
        "Do NOT mash unrelated sports into one post."
    )
    synthesize_rules = (
        "CRITICAL — SYNTHESIZE: Read ON-TOPIC notes, find the HIDDEN STORY (what the headline misses), "
        "then write ONE fresh post: Hook → Context → Payoff → Ending. "
        "Forbidden: 'According to [Outlet]:', 'Reporting drawn from:', outlet-by-outlet paste. "
        "0–3 hashtags. No URLs. Return ONLY the finished post."
    )
    goal_rules = (
        "GOAL: readers finish the post, want to share/reply, and learn something beyond the headline. "
        "Ask a question only if it adds value — never auto-add 'What do you think?'."
    )

    # Option 1 — Best storytelling angle (Master Rulebook §15)
    prompt = f"""Act as the News-to-Tweet Intelligence Engine.

{_HUMAN_VOICE_GUIDE}
{word_rules}
{ban_rules}
{same_story_rules}
{synthesize_rules}
{goal_rules}

ANGLE: Best Storytelling — strongest overall version (hook + hidden context + payoff).
Primary story ONLY: {title}
Category: {(category or 'news').upper()}

=== RESEARCH NOTES (input only — do not paste into the tweet) ===
{sources_block}
=== END ===

Write the Best Tweet now:"""

    # Option 2 — Emotional / human angle
    prompt_alt = f"""Act as the News-to-Tweet Intelligence Engine.

{_HUMAN_VOICE_GUIDE}
{word_rules}
{ban_rules}
{same_story_rules}
{synthesize_rules}

ANGLE: Emotional/Human — journey, stakes, or human connection (only if facts support emotion).
Do not manufacture drama. Ignore off-topic research notes.
Primary story ONLY: {title}
Category: {(category or 'news').upper()}

=== RESEARCH NOTES (do not paste) ===
{sources_block}
=== END ===

Write the Alternative Angle tweet now:"""

    fb = fallback_variants[0] if fallback_variants else (title or "")
    generated = _generate(
        prompt,
        fb,
        enforce_min=True,
        title=title,
        summary=combined_summary or summary or "",
        related_summaries=related_summaries,
    )
    generated = _strip_banned_boilerplate(generated)
    variants = [_trim_to_limit(generated)]

    gen2 = _generate(
        prompt_alt,
        fallback_variants[1] if len(fallback_variants) > 1 else fb,
        enforce_min=True,
        title=title,
        summary=combined_summary or summary or "",
        related_summaries=related_summaries,
    )
    gen2 = _strip_banned_boilerplate(gen2)
    if gen2 and gen2 not in variants:
        variants.append(_trim_to_limit(gen2))

    if fallback_variants:
        variants.append(fallback_variants[0])

    unique_variants: List[str] = []
    for variant in variants:
        if variant and variant not in unique_variants:
            unique_variants.append(variant)
    return unique_variants[:3]


def _looks_like_outlet_dump(text: str) -> bool:
    """Detect the broken multi-outlet paste format."""
    if not text:
        return False
    low = text.lower()
    if low.count("according to ") >= 2:
        return True
    if "reporting drawn from:" in low:
        return True
    if len(re.findall(r"(?m)^according to\s+.+:", text, flags=re.I)) >= 2:
        return True
    # Many distinct "Outlet: blurb" style lines
    if len(re.findall(r"(?m)^[A-Z][\w\s/()]{2,30}:\s+\S+", text)) >= 3:
        return True
    return False


def _sanitize_to_single_story(text: str, title: str, summary: str) -> str:
    """Keep only paragraphs that belong to the primary story."""
    text = _strip_banned_boilerplate(text or "")
    if not text:
        return ""
    paras = re.split(r"\n\s*\n", text)
    kept: List[str] = []
    for i, p in enumerate(paras):
        p = p.strip()
        if not p:
            continue
        if re.match(r"^according to\s+.+:", p, flags=re.I):
            continue
        if p.lower().startswith("reporting drawn from:"):
            continue
        # Always keep opening hook/title-ish first short para
        if i == 0 or word_count(p) < 12:
            kept.append(p)
            continue
        if _is_on_topic_block(p, title, summary):
            kept.append(p)
        # else drop off-topic paragraph
    cleaned = "\n\n".join(kept).strip()
    return _trim_to_max_words(cleaned, MAX_TWEET_WORDS)[:MAX_TWEET_LENGTH]


def generate_engagement_tweet(
    title: str,
    summary: str,
    source: str,
    category: str,
    related_sources: Optional[List[dict]] = None,
    fallback_only: bool = False,
) -> str:
    """
    Create a single-post draft using the Master Rulebook engine.
    Prefer generate_rulebook_packet() when you need Hidden Story / alternatives.
    """
    if fallback_only:
        variants = _build_engagement_variants(
            title=title or "",
            summary=summary or "",
            source=source or "",
            category=category or "news",
            related_sources=related_sources or [],
        )
        return variants[0] if variants else (title or "")

    from app.services.rulebook_engine import generate_rulebook_packet

    packet = generate_rulebook_packet(
        title=title or "",
        summary=summary or "",
        source=source or "",
        category=category or "news",
        related_sources=related_sources,
    )
    return (packet.get("best_tweet") or "").strip()


def generate_tweet(
    title: str,
    summary: str,
    source: str,
    category: str,
    related_sources: Optional[List[dict]] = None,
) -> str:
    """
    Generate one human long-form post about a single story via Master Rulebook.
    """
    return generate_engagement_tweet(
        title=title,
        summary=summary,
        source=source,
        category=category,
        related_sources=related_sources,
        fallback_only=False,
    )


def generate_tweet_for_trend_with_news(
    title: str,
    summary: str,
    source: str,
    category: str,
    trend_name: str,
    trend_query: str,
    related_sources: Optional[List[dict]] = None,
) -> str:
    """News-backed draft that must include the trending topic/hashtag."""
    variants = generate_tweet_variants(
        title=title,
        summary=summary,
        source=source,
        category=category,
        trend_name=trend_name,
        trend_query=trend_query,
        related_sources=related_sources,
    )
    text = max(variants, key=score_tweet_variant) if variants else ""
    return ensure_hashtag(text, trend_name, trend_query)


def generate_tweet_for_trend_only(trend_name: str, trend_query: str) -> str:
    """
    Trend-only draft when no matching news is found.
    Must not invent news facts — only engage with the trend as a topic.
    """
    tag = _hashtag_token(trend_name, trend_query)
    prompt = f"""You write warm, engaging X posts for a news account.
A topic is trending, but you have NO verified article yet — be honest about that.

{_HUMAN_VOICE_GUIDE}

Trending topic: {trend_name}
Keyword: {trend_query}
Required hashtag: {tag or '#' + trend_query}

Write ONE post ({MIN_TWEET_WORDS}–{MAX_TWEET_WORDS} words if you can stay factual; shorter is OK if you lack facts):
- Sound human and curious, not preachy
- Note it's trending / sparking conversation
- Invite people to share what THEY know (with sources)
- Do NOT invent news, stats, or event details
- Include the required hashtag
- Return ONLY the post text

Post:"""
    fallback = (
        f"This one's lighting up the timeline: {trend_name}\n\n"
        f"We're not going to fake a full story without solid reporting — "
        f"but clearly people care. What are you seeing on this, and which sources "
        f"do you trust right now?\n\n"
        f"{tag}"
    )
    text = _generate(
        prompt,
        fallback,
        enforce_min=True,
        title=trend_name or "",
        summary="",
    )
    return ensure_hashtag(text, trend_name, trend_query)


# ---------------------------------------------------------------------------
# Thread generation (hook → fact → why it matters)
# ---------------------------------------------------------------------------


def should_use_thread(
    category: Optional[str] = None,
    is_breaking: bool = False,
    priority_score: int = 0,
) -> bool:
    """
    Optional auto-thread heuristic (only used when format=auto).
    Default generation uses format=single so threads are never forced.
    """
    if is_breaking or priority_score >= 40:
        return True
    cat = (category or "").lower()
    if cat == "sports" or cat.startswith("sports_"):
        return True
    if priority_score >= 25:
        return True
    return False


def format_thread_display(parts: List[str]) -> str:
    """Join thread parts into numbered display text stored in tweet_text."""
    cleaned = [p.strip() for p in (parts or []) if (p or "").strip()]
    if not cleaned:
        return ""
    return "\n\n".join(f"{i}/ {part}" for i, part in enumerate(cleaned, 1))


def _trim_thread_part(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if len(text) <= MAX_TWEET_LENGTH:
        return text
    return text[: MAX_TWEET_LENGTH - 3] + "..."


def _strip_part_number(text: str) -> str:
    """Remove leading '1/' or '1.' numbering if the model included it."""
    return re.sub(r"^\s*\d+\s*[\/\.\)\:\-–—]\s*", "", (text or "").strip()).strip()


def parse_thread_response(raw: str) -> List[str]:
    """Parse numbered thread text from the model into individual parts."""
    if not (raw or "").strip():
        return []

    text = raw.strip().strip('"').strip("'")
    # Split on lines that start a new tweet number: 1/  2.  3)
    chunks = re.split(r"(?m)(?=^\s*\d+\s*[\/\.\)\:\-–—]\s*)", text)
    parts: List[str] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        body = _strip_part_number(chunk)
        if body:
            parts.append(_trim_thread_part(body))

    if len(parts) >= THREAD_MIN_PARTS:
        return parts[:THREAD_MAX_PARTS]

    # Fallback: blank-line separated blocks
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) >= THREAD_MIN_PARTS:
        return [_trim_thread_part(_strip_part_number(b)) for b in blocks[:THREAD_MAX_PARTS]]

    return []


def _build_fallback_thread(
    title: str,
    summary: str,
    source: str,
    category: str,
    trend_name: Optional[str] = None,
    trend_query: Optional[str] = None,
) -> List[str]:
    base_title = (title or "").strip() or "Big story developing"
    summary_snippet = (summary or "").strip()
    if len(summary_snippet) > 260:
        summary_snippet = summary_snippet[:257].rstrip() + "..."
    if not summary_snippet:
        summary_snippet = f"Key details are emerging from {source or 'reports'}."

    hashtags = " ".join(build_hashtags(title, summary, source, category))
    tag = _hashtag_token(trend_name, trend_query)

    part1 = f"{base_title}\n\nWhy this matters now."
    part2 = summary_snippet
    part3 = f"Here’s what to watch next. What do you think?\n\n{hashtags}".strip()

    parts = [_trim_thread_part(p) for p in (part1, part2, part3)]
    if tag:
        parts[-1] = ensure_hashtag(parts[-1], trend_name or tag, trend_query or tag)
    return parts


def generate_thread(
    title: str,
    summary: str,
    source: str,
    category: str,
    fallback_only: bool = False,
    trend_name: Optional[str] = None,
    trend_query: Optional[str] = None,
) -> List[str]:
    """
    Create a 2–3 tweet thread:
      1) Hook / why it matters now
      2) Key fact
      3) Why it matters / what to watch (+ CTA)
    Uses one AI call when available; falls back to local templates.
    """
    fallback = _build_fallback_thread(
        title=title,
        summary=summary,
        source=source,
        category=category,
        trend_name=trend_name,
        trend_query=trend_query,
    )
    if fallback_only:
        return fallback

    target = min(THREAD_PART_TARGET, MAX_TWEET_LENGTH - 20)
    hashtag_hint = " ".join(build_hashtags(title, summary, source, category)[:3])
    trend_line = ""
    if trend_name or trend_query:
        tag = _hashtag_token(trend_name or "", trend_query or "")
        trend_line = f"\nTrending topic to include (esp. in tweet 3): {trend_name or trend_query} {tag}"

    prompt = f"""You are a social media manager writing a short news THREAD for X (Twitter).

Write exactly 3 tweets as a thread about this article.
Structure:
1/ Strong hook — stakes and why it matters NOW (optional short question)
2/ Key fact — the actual news, concrete and factual
3/ Why it matters / what to watch next — end with a light CTA or question; include 2-3 hashtags

Article Title: {title}
Summary: {summary[:900] if summary else 'N/A'}
News Source: {source}
Category: {(category or 'news').upper()}
Suggested hashtags: {hashtag_hint or 'none'}{trend_line}

Rules:
- Factual, concise, no URLs
- Each tweet about {target} characters max (shorter is fine)
- No clickbait or invented stats
- Number each line exactly like: 1/ text
- Return ONLY the 3 numbered tweets, nothing else

Thread:"""

    # Thread parts stay short; do not enforce single-post min length on each part
    raw = _generate(
        prompt,
        format_thread_display(fallback),
        enforce_min=False,
    )
    parts = parse_thread_response(raw)

    if len(parts) < THREAD_MIN_PARTS:
        return fallback

    # Ensure hashtags on the last part when missing
    if hashtag_hint and "#" not in parts[-1]:
        candidate = f"{parts[-1].rstrip()}\n\n{hashtag_hint}".strip()
        if len(candidate) <= MAX_TWEET_LENGTH:
            parts[-1] = candidate

    if trend_name or trend_query:
        parts[-1] = ensure_hashtag(parts[-1], trend_name or "", trend_query or "")

    return [_trim_thread_part(p) for p in parts[:THREAD_MAX_PARTS] if p]


def generate_thread_for_trend_with_news(
    title: str,
    summary: str,
    source: str,
    category: str,
    trend_name: str,
    trend_query: str,
) -> List[str]:
    """News-backed thread that includes the trending hashtag on the last tweet."""
    parts = generate_thread(
        title=title,
        summary=summary,
        source=source,
        category=category,
        trend_name=trend_name,
        trend_query=trend_query,
    )
    if parts:
        parts[-1] = ensure_hashtag(parts[-1], trend_name, trend_query)
    return parts
