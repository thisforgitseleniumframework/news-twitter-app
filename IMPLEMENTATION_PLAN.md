# Twitter Content Generation Implementation Plan

## Goal
Create a reliable, token-efficient content generation pipeline for this project so it can produce highly engaging tweets and threads without depending heavily on repeated AI calls.

## Core Principles
- Prefer local fallback generation when AI services are unavailable or rate-limited.
- Use a small number of AI calls per article rather than generating repeatedly.
- Keep prompts concise and deterministic.
- Cache or reuse high-quality drafts when possible.
- Make the system robust for a free-tier API plan.

## Phase 1 — Low-cost draft generation
### Implement
- Add a reusable draft-generation function that returns:
  - one short post
  - one hook-based variant
  - one conversation-style variant
- Keep the default path local-first if AI is unavailable.
- Limit prompt length and avoid unnecessary repetition.

### Files
- [backend/app/services/ai_generator.py](backend/app/services/ai_generator.py)

### Outcome
Each article can generate a strong draft with minimal API usage.

## Phase 2 — Token-safe fallback strategy
### Implement
- Add a fallback template system that generates good posts without calling the AI API.
- Use a compact prompt structure and avoid long context windows.
- Only call the AI API when a draft is needed for a high-priority article.

### Files
- [backend/app/services/ai_generator.py](backend/app/services/ai_generator.py)
- [backend/app/config.py](backend/app/config.py)

### Outcome
The app can continue functioning even when API quotas are exhausted.

## Phase 3 — Thread support
### Implement
- Add a function that creates a short thread for major news stories.
- Default to 2–3 tweets instead of a long single post.
- Use a compact structure:
  1. Hook tweet
  2. Key fact tweet
  3. Why it matters tweet

### Files
- [backend/app/services/ai_generator.py](backend/app/services/ai_generator.py)

### Outcome
Posts feel more engaging and more native to X/Twitter.

## Phase 4 — Engagement-aware selection
### Implement
- Score each draft using heuristics such as:
  - strong opening line
  - clear takeaway
  - question or CTA
  - readable length
- Choose the best draft automatically.

### Files
- [backend/app/services/ai_generator.py](backend/app/services/ai_generator.py)

### Outcome
The app picks the most engaging version without extra API calls.

## Phase 5 — Optional future enhancements
### Add later if needed
- Topic-based tone selection
- Brand voice presets
- Performance learning from past posts
- Media-aware caption generation
- Scheduling-based content pacing

## Implementation Notes
- Keep all generation logic in one service file for maintainability.
- Prefer deterministic templates over verbose AI prompts.
- Add tests for fallback generation and scoring.
- Avoid generating multiple AI drafts for every article unless the article is high priority.

## Suggested working rule
For each article:
- use a local fallback draft immediately
- call AI only if the article is considered high priority or if the fallback is too generic
- reuse the best draft for later posting
