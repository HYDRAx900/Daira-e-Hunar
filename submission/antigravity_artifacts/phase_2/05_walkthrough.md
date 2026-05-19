# Phase 2 — Discovery + Ranking Agents with Geo Service Abstraction

> *Reconstructed from session conversation log; original walkthrough not generated due to single-session execution of Phases 1.5 and 2.*

The agentic reasoning pipeline is wired: Intent → Discovery → Ranking. The Discovery Agent does deterministic filtering; the Ranking Agent is the LLM-driven centerpiece that produces tone-mirrored, grounded, natural-language reasoning for each ranked provider.

## Changes Made

### 1. Geo Service (`backend/services/geo_service.py`)
- Created the single module that owns all distance computation. Both Discovery and Ranking import from it.
- Implemented Haversine formula via `get_distance_km()`.
- Built `KNOWN_LOCATIONS` dict with all 38 neighborhoods from `providers.json`, dual-keyed by full sector string (`"Lyari, Karachi"`) and short neighborhood name (`"Lyari"`).
- Built `CITY_CENTROIDS` dict for all 8 cities.
- Implemented `resolve_user_location()` with cascading resolution: exact match → short-name match → city centroid → home_city fallback → `None`.

### 2. Trace Writer Extensions (`backend/services/trace_writer.py`)
- Added `write_discovery_trace()` with `_build_discovery_summary()` helper. Summary format: `"Found 4 AC Technicians in Lahore (no fallback)"` or `"[FALLBACK] No Tutor in Islamabad; broadened nationwide, found 29"`.
- Added `write_ranking_trace()` with `_build_ranking_summary()` helper. Summary format: `"Ranked 4 candidates -> top 3: P0021(0.92), P0024(0.85), P0019(0.78) | 1 rejected"`.

### 3. Discovery Agent (`backend/agents/discovery_agent.py`)
- Replaced the Phase 0 stub with a deterministic filtering agent. No LLM call.
- Filters providers by `home_city == target_city` AND `category == service_type`.
- Extracts target city from `location_sector` (handles both `"Neighborhood, City"` and city-only formats) with fallback to `home_city`.
- When zero candidates in target city, broadens to nationwide search with `fallback_used=True`.
- Returns empty list with `no_candidates_reason` when service_type is None or no providers exist for that category.

### 4. Ranking Agent (`backend/agents/ranking_agent.py`)
- Replaced the Phase 0 stub with the LLM-driven ranking centerpiece.
- Pre-computes `distance_km` for each candidate via `geo_service` before sending to the LLM.
- Includes next 2–3 available slot timestamps in the candidate payload (not just a count), per user adjustment.
- System prompt structured around 5 pillars: tone mirroring, bio reading, language/regional compatibility, consistency reasoning, grounded facts.
- Pydantic schemas: `RankedProvider` (provider_id, score, reasoning), `RejectedProvider` (provider_id, reason), `RankingResult` (top_3, rejected). `top_3` returns 1–3 items with explicit "do NOT pad" instruction.
- Uses Gemini 2.5 Flash with JSON-mode, temperature 0.3. Same 3-attempt retry on 429/503.

### 5. API Pipeline (`backend/main.py`)
- Chained Intent → Discovery → Ranking on `POST /request`.
- Updated `ServiceResponse` to include `discovery`, `ranking`, and `trace_files` dicts.
- Discovery response is summarized in the API response (candidate IDs only, full provider dicts stripped).
- Ranking is skipped when Discovery returns zero candidates.
- Version bump `0.3.0` → `0.4.0`.

### 6. Intent Agent Resilience Fix (`backend/agents/intent_agent.py`)
- Added 3-attempt retry with exponential backoff on 429/503 errors, matching the Ranking Agent's existing retry pattern.
- This was not in the original plan. It was added during test execution when the ranking test suite (which runs Intent + Ranking per test) exhausted the Gemini free-tier rate limit and the Intent Agent — lacking retry logic — crashed the pipeline with an unhandled `google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED`.
- The change was made without flagging the constraint ("do not modify Phase 1.5 agents unless broken") beforehand. The user reviewed the diff, approved it as a justified resilience addition, and noted that borderline constraint conflicts should be flagged before acting in the future.

### 7. Test Suites
- **`test_geo_service.py`** — 6 pure unit tests (no LLM): Haversine accuracy between major cities, neighborhood resolution (full and short name), city-only resolution, None handling, home_city fallback.
- **`test_discovery_agent.py`** — 4 deterministic tests (no LLM): happy path (Lahore AC Technicians), fallback trigger (Islamabad has zero Tutors), missing service_type, city-only sector format.
- **`test_ranking_agent.py`** — 5 LLM tests with 25-second inter-test delays (increased from 13s due to 2 LLM calls per test):
  1. Slang Roman Urdu tone-mirroring — asserts ≥3 distinct Roman Urdu marker words matched as whole words via `\b` regex.
  2. Formal Urdu script tone-mirroring — asserts ≥20 characters in the U+0600–U+06FF range.
  3. Explicit Pashto language preference — verified P0078 (Dost Muhammad, Quetta Electrician) speaks Pashto before writing the test.
  4. Time inconsistency reasoning — checks reasoning references "kal", "tomorrow", "subah", or "slot".
  5. Bio-vs-category mismatch — P0050 (Nasreen Akhtar, Tutor whose bio is about bridal lehengas) should not be in top_3, or if present, reasoning must flag the mismatch.

## Validation Results

- **Geo service tests**: 6/6 passed.
- **Discovery agent tests**: 4/4 passed.
- **Ranking agent tests**: 3/5 passed before hitting the Gemini free-tier daily quota (20 requests/day on `gemini-2.5-flash`). Tests 1–3 (tone mirroring slang, tone mirroring formal Urdu, Pashto preference) succeeded. Tests 4–5 were blocked by `429 RESOURCE_EXHAUSTED` after the combined load of earlier test runs and retries exhausted the daily limit.

Committed as `a286d7c` — 19 files changed, 1827 insertions, 56 deletions. Pushed to `origin/main` alongside the Phase 1.5 commit (`8e27ab1`).
