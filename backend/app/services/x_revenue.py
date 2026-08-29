"""
X Creator Revenue Sharing — content quality layer.

Program eligibility (account-level, not automated here) typically includes:
  - Active X Premium / Premium+
  - Enough organic impressions in a rolling window (X has changed thresholds over time)
  - Enough verified followers
  - Payout setup in an eligible country + compliance with X Rules

What this module optimizes for (content-level signals that help earnings):
  Revenue share is heavily driven by verified-user engagement around your posts
  (especially conversation / replies where ads can appear). So we score drafts for:

  1. Conversation bait that invites real replies (not empty "thoughts?" spam)
  2. Original framing (not pure headline copy-paste / link dumps)
  3. Scroll-stopping hook in the first line
  4. Substance / dwell potential (Premium-length posts when appropriate)
  5. Media-ready structure and light hashtag use
  6. Low risk of spam / engagement-bait / policy flags

This does NOT guarantee payouts. It ranks drafts by how well they match
engagement patterns that tend to perform under X's ad-share model.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence

# Soft copy patterns that look like engagement farming / low-quality bait
_BAIT_PATTERNS = (
    r"\blink in bio\b",
    r"\bretweet if\b",
    r"\brt if\b",
    r"\blike if\b",
    r"\bfollow me\b",
    r"\bfollow for more\b",
    r"\bdm me\b",
    r"\bcomment\s+[\"'].+[\"']\s+if\b",
    r"\btag someone\b",
    r"\btag a friend\b",
    r"\bdouble tap\b",
    r"\bshare this\b",
    r"\bgiveaway\b",
    r"\bfree money\b",
    r"\bmake \$?\d+k\b",
    r"\bguaranteed\b",
)

_GENERIC_OPENERS = (
    "breaking:",
    "just in:",
    "in other news",
    "according to reports",
    "sources say",
    "it has been reported",
    "here's what you need to know",
    "let that sink in",
    "this is huge",
    "wow.",
    "unbelievable.",
)

_CONVERSATION_CUES = (
    r"\?",  # any question
    r"\bwhy\b",
    r"\bhow\b",
    r"\bwhat do you\b",
    r"\bwould you\b",
    r"\bdo you think\b",
    r"\bunpopular opinion\b",
    r"\bhot take\b",
    r"\bagree or disagree\b",
    r"\bcurious\b",
    r"\bhonestly\b",
    r"\bchange my mind\b",
)

_SUBSTANCE_MARKERS = (
    r"\bbecause\b",
    r"\bhowever\b",
    r"\bbut\b",
    r"\bmeanwhile\b",
    r"\bwhich means\b",
    r"\bin other words\b",
    r"\bthe catch\b",
    r"\bthe problem\b",
    r"\bthe upside\b",
    r"\bfor context\b",
    r"\bcompared to\b",
    r"\b\d{1,3}(?:,\d{3})+\b",  # large numbers
    r"\b\d+%\b",
    r"\b\$\d+",
    r"\b\d{4}\b",  # years
)

# Account checklist shown in the UI (not scored from draft text)
ACCOUNT_ELIGIBILITY_CHECKLIST = [
    {
        "id": "premium",
        "label": "X Premium or Premium+ active",
        "why": "Required to join Creator Revenue Sharing.",
    },
    {
        "id": "impressions",
        "label": "Hit X’s organic impressions threshold (rolling window)",
        "why": "X changes the number; check Creator Studio → Monetization.",
    },
    {
        "id": "verified_followers",
        "label": "Enough verified followers",
        "why": "Payouts weight engagement from Premium / verified users.",
    },
    {
        "id": "payouts",
        "label": "Payout method + eligible country set up",
        "why": "Without Stripe/payout setup, earnings cannot be withdrawn.",
    },
    {
        "id": "rules",
        "label": "No spam, manipulation, or policy strikes",
        "why": "Engagement farming and inauthentic activity can void share.",
    },
]


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text or ""))


def _first_line(text: str) -> str:
    if not text:
        return ""
    line = re.split(r"[\n\r]+", text.strip(), maxsplit=1)[0]
    return line.strip()


def _hashtag_count(text: str) -> int:
    return len(re.findall(r"(?<!\w)#\w+", text or ""))


def _url_count(text: str) -> int:
    return len(re.findall(r"https?://\S+", text or "", flags=re.I))


def score_content_for_x_revenue(
    text: str,
    *,
    is_thread: bool = False,
    thread_parts: Optional[Sequence[str]] = None,
    has_media: bool = False,
    category: str = "",
) -> Dict[str, Any]:
    """
    Return a 0–100 revenue-fit score plus checklist tips.

    Higher = more likely to spark verified conversation / dwell / shares
    under X's ad revenue-share dynamics (replies matter a lot).
    """
    parts: List[str] = []
    if is_thread and thread_parts:
        parts = [str(p).strip() for p in thread_parts if str(p or "").strip()]
    body = "\n\n".join(parts) if parts else (text or "").strip()
    if not body:
        return {
            "score": 0,
            "grade": "F",
            "label": "empty",
            "breakdown": {},
            "tips": ["Draft is empty — generate or write content first."],
            "checks": {},
            "program_notes": ACCOUNT_ELIGIBILITY_CHECKLIST,
        }

    lower = body.lower()
    words = _word_count(body)
    first = _first_line(body)
    first_words = _word_count(first)
    tips: List[str] = []
    checks: Dict[str, bool] = {}
    breakdown: Dict[str, int] = {}

    # --- 1. Hook (0–18) ---
    hook = 0
    if first_words >= 4:
        hook += 6
    if first_words <= 22 and first_words >= 5:
        hook += 4  # punchy opener
    elif first_words > 40:
        tips.append("Shorten the first line — front-load the surprise in ≤20 words.")
    if first and first[0].isupper() and not first.lower().startswith(_GENERIC_OPENERS):
        hook += 4
    if any(first.lower().startswith(g) for g in _GENERIC_OPENERS):
        hook = max(0, hook - 6)
        tips.append("Avoid generic openers (Breaking:/Just in:). Lead with the twist.")
    if re.search(r"[!?]", first):
        hook += 2
    # Digits / proper names in opener = concrete
    if re.search(r"\d", first):
        hook += 2
    hook = min(18, hook)
    breakdown["hook"] = hook
    checks["strong_hook"] = hook >= 12

    # --- 2. Conversation / replies (0–22) — critical for ad-share ---
    convo = 0
    cue_hits = sum(1 for p in _CONVERSATION_CUES if re.search(p, lower))
    if "?" in body:
        convo += 10
        checks["has_question"] = True
    else:
        checks["has_question"] = False
        tips.append(
            "Add one real question that invites a reply (X pays more when verified users talk under your post)."
        )
    if cue_hits >= 2:
        convo += 6
    elif cue_hits == 1:
        convo += 3
    # Thread final tweet as CTA
    if parts and len(parts) >= 2 and ("?" in parts[-1] or re.search(r"\byou\b", parts[-1], re.I)):
        convo += 4
        checks["thread_cta"] = True
    else:
        checks["thread_cta"] = bool(parts)
    # Penalize empty bait questions only
    if re.search(r"^(thoughts|agree)\??$", body.strip().lower()):
        convo = max(0, convo - 10)
        tips.append("Replace empty 'thoughts?' with a specific stake or tradeoff.")
    convo = min(22, convo)
    breakdown["conversation"] = convo

    # --- 3. Original substance / dwell (0–22) ---
    substance = 0
    if words >= 40:
        substance += 6
    if words >= 90:
        substance += 6
    if words >= 160:
        substance += 4  # Premium long-form dwell
    if words < 25 and not parts:
        tips.append("Too thin — add context, stakes, or a non-obvious angle (dwell time helps).")
    marker_hits = sum(1 for p in _SUBSTANCE_MARKERS if re.search(p, lower))
    substance += min(6, marker_hits * 2)
    if parts:
        # Multi-part threads earn when each beat adds info
        avg_w = words / max(1, len(parts))
        if 25 <= avg_w <= 80:
            substance += 4
        checks["thread_structure"] = len(parts) >= 3
        if len(parts) < 3:
            tips.append("Threads perform best at 3–6 beats: hook → facts → stakes → question.")
    else:
        checks["thread_structure"] = False
    # Pure link dump
    if _url_count(body) and words < 30:
        substance = max(0, substance - 10)
        tips.append("Don't post link-only. Summarize the insight; put the link later or in reply.")
    substance = min(22, substance)
    breakdown["substance"] = substance
    checks["enough_substance"] = substance >= 12

    # --- 4. Originality vs headline paste (0–12) ---
    originality = 8
    # Heavy quotes / "according to"
    if lower.count('"') >= 4 or lower.count("according to") >= 2:
        originality -= 4
        tips.append("Retell in your voice — heavy quoting reads as a wire rewrite, not creator content.")
    if re.search(r"^\W*https?://", body.strip(), re.I):
        originality = 0
        tips.append("Never lead with a bare URL.")
    breakdown["originality"] = max(0, originality)
    checks["original_voice"] = originality >= 6

    # --- 5. Media & packaging (0–12) ---
    pack = 0
    if has_media:
        pack += 8
        checks["has_media"] = True
    else:
        checks["has_media"] = False
        tips.append("Attach an image/video when possible — media posts get more expansion & replies.")
    tags = _hashtag_count(body)
    if 1 <= tags <= 3:
        pack += 3
    elif tags > 5:
        pack -= 4
        tips.append("Use at most 1–3 hashtags; hashtag stuffing looks spammy to the algorithm.")
    if tags == 0 and category:
        pack += 1  # ok without tags
    pack = min(12, max(0, pack))
    breakdown["packaging"] = pack

    # --- 6. Policy / spam risk (0–14, start full and subtract) ---
    safety = 14
    bait_hits = sum(1 for p in _BAIT_PATTERNS if re.search(p, lower))
    if bait_hits:
        safety -= min(12, bait_hits * 5)
        tips.append("Remove engagement-farming phrases (RT if / follow me / giveaway). They risk deboost + payout issues.")
    if body.count("#") > 8:
        safety -= 4
    if re.search(r"(.)\1{4,}", body):
        safety -= 3
    if words > 0 and len(set(lower.split())) / max(1, len(lower.split())) < 0.45 and words > 40:
        safety -= 3
        tips.append("Reduce repetition — duplicate-looking content underperforms and can look automated.")
    safety = max(0, safety)
    breakdown["policy_safety"] = safety
    checks["low_spam_risk"] = safety >= 10

    # --- 7. Length fit for Premium (0–10) ---
    length_pts = 0
    if parts:
        # threads: each part ideally under classic-friendly length but OK longer on Premium
        overs = sum(1 for p in parts if len(p) > 1100)
        if overs:
            length_pts = 4
            tips.append("Some thread parts are very long — split so each post is scannable.")
        else:
            length_pts = 8 if 3 <= len(parts) <= 8 else 6
    else:
        n = len(body)
        if 120 <= n <= 900:
            length_pts = 8
        elif 900 < n <= 2500:
            length_pts = 10  # Premium long-form
        elif 60 <= n < 120:
            length_pts = 5
        else:
            length_pts = 2
            if n < 60:
                tips.append("Post is very short — expand with stakes or a sharp take for Premium audiences.")
    breakdown["length_fit"] = length_pts

    raw = (
        hook
        + convo
        + substance
        + breakdown["originality"]
        + pack
        + safety
        + length_pts
    )
    # max theoretical ~18+22+22+12+12+14+10 = 110 → normalize to 100
    score = int(round(min(100, (raw / 110.0) * 100)))

    if score >= 85:
        grade, label = "A", "strong revenue fit"
    elif score >= 70:
        grade, label = "B", "good — small tweaks"
    elif score >= 55:
        grade, label = "C", "average — needs reply bait + substance"
    elif score >= 40:
        grade, label = "D", "weak for monetization"
    else:
        grade, label = "F", "rewrite before posting"

    # Keep top actionable tips
    uniq_tips: List[str] = []
    for t in tips:
        if t not in uniq_tips:
            uniq_tips.append(t)
    if score >= 85 and not uniq_tips:
        uniq_tips.append("Looks solid — post when your audience is active; reply to early comments fast.")

    return {
        "score": score,
        "grade": grade,
        "label": label,
        "breakdown": breakdown,
        "tips": uniq_tips[:6],
        "checks": checks,
        "program_notes": ACCOUNT_ELIGIBILITY_CHECKLIST,
    }


def apply_score_to_draft_fields(draft: Any) -> Dict[str, Any]:
    """Score draft text and write revenue_score / revenue_grade / revenue_tips on the ORM row."""
    parts_raw = getattr(draft, "thread_parts", None)
    parts: Optional[List[str]] = None
    if isinstance(parts_raw, list):
        parts = [str(p) for p in parts_raw if p]
    elif isinstance(parts_raw, str) and parts_raw.strip():
        try:
            parsed = json.loads(parts_raw)
            if isinstance(parsed, list):
                parts = [str(p) for p in parsed if p]
        except Exception:
            parts = None

    is_thread = bool(getattr(draft, "is_thread", False)) and bool(parts) and len(parts) >= 2
    text = getattr(draft, "tweet_text", None) or ""
    if is_thread and parts:
        text = "\n\n".join(parts)

    has_media = bool(getattr(draft, "media_path", None)) and (
        getattr(draft, "attach_media", True) is not False
    )
    result = score_content_for_x_revenue(
        text,
        is_thread=is_thread,
        thread_parts=parts,
        has_media=has_media,
        category=getattr(draft, "category", None) or "",
    )
    draft.revenue_score = int(result["score"])
    draft.revenue_grade = str(result["grade"])
    draft.revenue_tips = json.dumps(result, ensure_ascii=False)
    return {
        "revenue_score": draft.revenue_score,
        "revenue_grade": draft.revenue_grade,
        "revenue_tips": draft.revenue_tips,
        "revenue": result,
    }


def parse_revenue_tips(raw: Any) -> Optional[Dict[str, Any]]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except Exception:
            return None
    return None


def enrich_draft_dict(d: dict, draft: Any) -> dict:
    """Attach revenue fields onto a serialized draft dict."""
    tips = parse_revenue_tips(getattr(draft, "revenue_tips", None))
    score = getattr(draft, "revenue_score", None)
    grade = getattr(draft, "revenue_grade", None)
    if tips is None and (d.get("tweet_text") or d.get("thread_parts")):
        tips = score_content_for_x_revenue(
            d.get("tweet_text") or "",
            is_thread=bool(d.get("is_thread")),
            thread_parts=d.get("thread_parts"),
            has_media=bool(d.get("media_path") and d.get("attach_media", True)),
            category=d.get("category") or "",
        )
        score = tips.get("score")
        grade = tips.get("grade")
    d["revenue_score"] = score
    d["revenue_grade"] = grade
    d["revenue"] = tips
    return d
