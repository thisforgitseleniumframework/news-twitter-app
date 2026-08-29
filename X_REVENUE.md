# X Creator Revenue Sharing — how this app helps

NewsPost is tuned so drafts are more likely to earn **under X’s Creator Revenue Sharing** model: ads shown around conversation (especially replies), with heavier weight on **verified / Premium** engagement.

This is **not** a guarantee of payouts. X’s program rules and thresholds change; always confirm in **Creator Studio → Monetization**.

---

## 1. Account eligibility (you must do this on X)

Typical requirements (verify live on X Help / Creator Studio):

| Requirement | Why it matters |
|-------------|----------------|
| **X Premium or Premium+** | Needed to join revenue sharing |
| **Organic impressions threshold** (rolling window) | X has changed this number over time |
| **Verified / Premium followers** | Payouts weight engagement from verified users |
| **Payout setup + eligible country** | Without payouts configured, you can’t withdraw |
| **No policy / spam strikes** | Manipulation and engagement-farming can void share |

In the app: open **Analytics** → **X Creator Revenue** panel (loads `GET /api/tweets/revenue-guide`).

---

## 2. What the app optimizes in *content*

X tends to reward posts that:

1. **Start conversations** — real questions / stakes (replies matter a lot for ad inventory)
2. **Hold attention** — substance, context, numbers (dwell)
3. **Sound original** — not wire copy or link dumps
4. **Use media** when available
5. **Avoid spam signals** — “RT if”, “follow me”, hashtag walls, empty “Thoughts?”

### Automatic scoring (0–100)

Every draft gets:

- `revenue_score` (0–100)
- `revenue_grade` (A–F)
- Tips + breakdown (hook, conversation, substance, originality, packaging, policy safety, length)

Shown on each **TweetCard** as **X Revenue fit** (expand for tips).

Scorer lives in `backend/app/services/x_revenue.py`.

### Generation prompts

`ai_generator.py` voice guide pushes:

- Punchy first line (no “Breaking:”)
- Specific reply-driving question
- 1–3 hashtags
- No engagement-farm phrases
- Factual rewrite from sources

Variant ranking blends the revenue score so the “best” draft is more monetization-aware.

---

## 3. How to use it day-to-day

1. Fetch news → **Generate tweet** (single or thread).
2. Check **X Revenue fit** on the card. Aim for **B or A** before posting.
3. Edit if tips say so → **Save** (score recalculates on update).
4. Prefer **image/video** attach when the article has media.
5. Post when your audience is active; **reply early** to comments (boosts conversation).
6. Avoid farming: no giveaways-as-bait, no “RT if you agree” spam.

### APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/tweets/revenue-guide` | Account checklist + content rules |
| POST | `/api/tweets/score-revenue` | Score arbitrary text `{ "text": "..." }` |
| — | Draft list/detail | Includes `revenue_score`, `revenue_grade`, `revenue` |

---

## 4. Honest limits

- **Does not** join the program for you or track real X payouts.
- **Does not** know live impression/follower thresholds (those are on X).
- High score ≠ viral; niche + timing + consistency still matter.
- Policy violations or inauthentic engagement can erase earnings regardless of score.

---

## 5. Files involved

- `backend/app/services/x_revenue.py` — scorer
- `backend/app/services/ai_generator.py` — prompts + variant ranking
- `backend/app/models.py` — `revenue_*` columns
- `backend/app/routers/tweets.py` / `news.py` / `trend_drafts.py` — wire-up
- `frontend/app/components/TweetCard.tsx` — badge + tips
- `frontend/app/components/AnalyticsDashboard.tsx` — eligibility guide
