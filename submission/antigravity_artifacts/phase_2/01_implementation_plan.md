# Phase 2: Discovery + Ranking Agents with Geo Service Abstraction

Build the agentic reasoning pipeline: Intent → Discovery → Ranking. The Discovery Agent is deterministic filtering; the Ranking Agent is the LLM-driven centerpiece that produces tone-mirrored, bio-aware, culturally-sensitive natural-language reasoning for each ranked provider.

---

## Proposed Changes

### Component 1: Geo Service (`backend/services/geo_service.py`)

#### [NEW] [geo_service.py](file:///d:/Infromal%20Economy/backend/services/geo_service.py)

The **single module** that owns all distance computation. Both Discovery and Ranking import from it. Designed so Google Maps Distance Matrix can swap in later behind the same interface.

**Functions:**

```python
def get_distance_km(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
    """Haversine formula. Returns distance in km."""

def resolve_user_location(location_sector: str | None, home_city: str | None) -> tuple[float, float] | None:
    """Best-effort location resolution: neighborhood lookup → city centroid → None."""
```

**Data structures:**

- `KNOWN_LOCATIONS: dict[str, tuple[float, float]]` — All 38 neighborhoods from `providers.json`, using the base coordinates from `generate_providers.py`. Keyed by both full sector string (`"Lyari, Karachi"`) AND short neighborhood name (`"Lyari"`) for flexible matching.
- `CITY_CENTROIDS: dict[str, tuple[float, float]]` — Centroids for all 8 cities (Islamabad, Rawalpindi, Lahore, Faisalabad, Karachi, Quetta, Peshawar, Gilgit).

**`resolve_user_location` logic:**
1. If `location_sector` is not None:
   - Try exact match in `KNOWN_LOCATIONS` (e.g. `"Lyari, Karachi"`)
   - Try short-name match (e.g. `"Lyari"`)
   - Try `CITY_CENTROIDS` (handles city-only sectors like `"Lahore"`)
2. If `location_sector` is None but `home_city` is provided:
   - Fall back to `CITY_CENTROIDS[home_city]`
3. Return `None` if nothing resolves.

---

### Component 2: Discovery Agent (`backend/agents/discovery_agent.py`)

#### [MODIFY] [discovery_agent.py](file:///d:/Infromal%20Economy/backend/agents/discovery_agent.py)

Replace the Phase 0 stub with a deterministic filtering agent. **No LLM call.**

**Input:** A parsed `IntentResult` dict (from Intent Agent).

**Filtering logic:**
1. Load `mock_data/providers.json`.
2. Determine `target_city`: extract from `location_sector` (if "Neighborhood, City" format → take city part) OR from `home_city` field. If the sector is a city name itself (e.g. `"Lahore"`), use that.
3. Filter providers where `home_city == target_city` AND `category == intent["service_type"]`.
4. If zero candidates → **fallback**: broaden to all providers of that `service_type` nationwide. Set `fallback_used = True` with a reason string.
5. If still zero (service_type is None or truly no providers of that type) → return empty list with `no_candidates_reason` populated.

**Output schema (Pydantic):**

```python
class DiscoveryResult(BaseModel):
    candidates: list[dict]         # full provider dicts
    total_found: int
    city_searched: str | None
    fallback_used: bool
    fallback_reason: str | None    # e.g. "No AC Technician found in Islamabad; broadened to nationwide"
    no_candidates_reason: str | None
```

**Trace:** Write `discovery_<timestamp>.json` via trace_writer. New function `write_discovery_trace()` in trace_writer.py — follows the same structure pattern as `write_intent_trace()`.

> [!IMPORTANT]
> Islamabad has zero Tutors and zero Electricians in the current dataset. Peshawar has zero Plumbers and zero Electricians. These are natural fallback test scenarios — no data modification needed.

---

### Component 3: Ranking Agent (`backend/agents/ranking_agent.py`)

#### [MODIFY] [ranking_agent.py](file:///d:/Infromal%20Economy/backend/agents/ranking_agent.py)

Replace the Phase 0 stub with the LLM-driven ranking centerpiece.

**Input:** Full `IntentResult` dict + `DiscoveryResult.candidates` list.

**Pre-LLM processing:**
1. Resolve user location via `geo_service.resolve_user_location(intent["location_sector"], intent.get("home_city"))`.
2. For each candidate, compute `distance_km` using `geo_service.get_distance_km()`. If user location is `None`, set `distance_km` to `None`.
3. Build a candidate payload list with the fields the LLM needs: `provider_id`, `name`, `category`, `sector`, `rating`, `rating_count`, `price_range`, `available_slots` (count only), `verified`, `languages_spoken`, `bio`, `years_experience`, `cultural_background`, `distance_km`.

**LLM call:** Gemini 2.5 Flash, JSON-mode, Pydantic response schema. Same `google-genai` SDK pattern as Intent Agent. Temperature 0.3 (slightly higher than Intent's 0.2 to allow stylistic variation in reasoning).

**Output schema (Pydantic):**

```python
class RankedProvider(BaseModel):
    provider_id: str
    score: float              # 0.0–1.0
    reasoning: str            # 2–4 sentences, tone-mirrored

class RejectedProvider(BaseModel):
    provider_id: str
    reason: str               # short rejection reason

class RankingResult(BaseModel):
    top_3: list[RankedProvider]
    rejected: list[RejectedProvider]
```

**System prompt design — 5 pillars:**

**(a) TONE MIRRORING.** The prompt will receive `detected_language` and `formality_level` from the intent. Instructions:
- `detected_language="roman_urdu"` + `formality_level="slang"` → write reasoning in casual Roman Urdu with slang
- `detected_language="urdu"` + `formality_level="formal"` → write reasoning in formal Urdu script
- `detected_language="english"` → write reasoning in English
- Code-switched input (`code_switching=true`) → mirror the English/Urdu mix
- Include 3 few-shot examples: one slang Roman Urdu, one formal Urdu script, one English

**(b) READ THE BIO.** Explicit instruction: "The `bio` field carries human signal that ratings don't. Reference specific bio details when they inform the ranking. If a provider's bio implies a different specialty than their listed category (e.g., a 'Tutor' whose bio is about bridal lehengas), flag this as a concern in the reasoning and deprioritize."

**(c) LANGUAGE & REGIONAL COMPATIBILITY.** Instruction: "When a provider's `languages_spoken` overlaps with the user's detected language, or when the provider is from the same locality as the user's requested area, you may note this as a practical communication or local-knowledge advantage. NEVER frame this as ethnicity matching. Talk about language and locality, not ethnicity. If the user explicitly stated a language preference, honor it as a hard preference."

**(d) CONSISTENCY REASONING.** Instruction: "If `requested_time` and `urgency` appear inconsistent (e.g., requested_time='tomorrow morning' but urgency='this_week'), reason about which signal is more specific and use that one. Mention the reconciliation briefly."

**(e) GROUNDED REASONING.** Instruction: "Each reasoning paragraph must be 2–4 sentences. Name specific facts: distance, rating, slot count, bio detail, price range. No generic platitudes. No performative empathy."

**Retry logic:** Same pattern as Intent Agent — retry on 429/503 with exponential backoff (we'll add this as a shared utility or inline, matching the existing pattern).

**Trace:** Write `ranking_<timestamp>.json` via trace_writer. New function `write_ranking_trace()` — captures input intent, candidates with distances, prompt, raw LLM response, parsed result, summary line.

---

### Component 4: Trace Writer Updates (`backend/services/trace_writer.py`)

#### [MODIFY] [trace_writer.py](file:///d:/Infromal%20Economy/backend/services/trace_writer.py)

Add two new trace functions following the existing `write_intent_trace()` pattern:

```python
def write_discovery_trace(
    intent_input: dict,
    filter_applied: dict,          # {"city": ..., "service_type": ...}
    candidates_returned: list,
    fallback_used: bool,
    fallback_reason: str | None,
    no_candidates_reason: str | None,
) -> str:
    """Write discovery_<timestamp>.json. Returns relative path."""

def write_ranking_trace(
    intent_input: dict,
    candidates_with_distances: list,
    prompt_sent: str,
    raw_llm_response: str,
    parsed_output: dict,
    model_name: str,
    latency_ms: float,
) -> str:
    """Write ranking_<timestamp>.json. Returns relative path."""
```

Each includes a `_build_*_summary()` helper for the human-readable summary line.

- Discovery summary: `"Found 4 AC Technicians in Lahore (no fallback)"` or `"[FALLBACK] No Tutor in Islamabad; broadened nationwide, found 29"`
- Ranking summary: `"Ranked 4 candidates -> top 3: P0021(0.92), P0024(0.85), P0019(0.78) | 1 rejected"`

---

### Component 5: Main API Pipeline (`backend/main.py`)

#### [MODIFY] [main.py](file:///d:/Infromal%20Economy/backend/main.py)

**Chain: Intent → Discovery → Ranking on `POST /request`.**

Update `ServiceResponse` model:

```python
class ServiceResponse(BaseModel):
    status: str
    message: str
    intent: Optional[dict] = None
    discovery: Optional[dict] = None
    ranking: Optional[dict] = None
    trace_files: Optional[dict] = None    # {"intent": "...", "discovery": "...", "ranking": "..."}
```

**Orchestration logic in `handle_request()`:**
1. Run Intent Agent → get `intent_result`
2. Run Discovery Agent → get `discovery_result`
3. If `discovery_result["candidates"]` is empty → skip Ranking, return structured "no candidates" response
4. Run Ranking Agent → get `ranking_result`
5. Return full `{intent, discovery, ranking, trace_files}`

**Version bump:** `0.3.0` → `0.4.0` (health check + FastAPI constructor).

---

### Component 6: Test Suite

#### [NEW] [test_geo_service.py](file:///d:/Infromal%20Economy/tests/test_geo_service.py)

Pure unit tests, no LLM calls, no rate limit delays needed:

1. **Haversine accuracy:** Distance between Islamabad centroid and Lahore centroid ≈ 375 km (±20 km tolerance).
2. **Neighborhood resolution:** `resolve_user_location("Lyari, Karachi", "Karachi")` returns a valid coordinate tuple.
3. **City-only resolution:** `resolve_user_location("Lahore", None)` returns Lahore centroid.
4. **None input:** `resolve_user_location(None, None)` returns `None`.

---

#### [NEW] [test_discovery_agent.py](file:///d:/Infromal%20Economy/tests/test_discovery_agent.py)

No LLM calls — deterministic tests, no rate limit delays:

1. **Happy path:** Intent for "AC Technician" in "Lahore" → returns 3 candidates (all Lahore AC Techs), `fallback_used=False`.
2. **Fallback trigger:** Intent for "Tutor" in "Islamabad" → Islamabad has zero tutors → `fallback_used=True`, candidates come from other cities.
3. **Service type None:** Intent with `service_type=None` → returns empty list with `no_candidates_reason`.
4. **Trace file created:** Verify `discovery_<timestamp>.json` exists after each run.

---

#### [NEW] [test_ranking_agent.py](file:///d:/Infromal%20Economy/tests/test_ranking_agent.py)

Real Gemini calls with 13-second delays between tests:

1. **Slang Roman Urdu tone-mirroring:** Input `"AC bana de yaar Lahore mein, jaldi"` → assert reasoning text contains Roman Urdu characters (check for common Urdu-romanized words like "hai", "wala", "ke", "ka", etc. — give LLM latitude, don't over-constrain).
2. **Formal Urdu tone-mirroring:** Formal Urdu script input → assert reasoning contains Urdu script characters (check `\u0600-\u06FF` range).
3. **Explicit language preference:** `"Pashto bolne wala electrician chahiye Quetta mein"` → assert top-1 provider's `languages_spoken` includes `"Pashto"` and reasoning mentions language/Pashto.
4. **Time inconsistency reasoning:** `requested_time="kal subah"` + `urgency="this_week"` → assert the trace or reasoning text references the reconciliation (look for "kal" or "tomorrow" or "subah" in the reasoning/trace).
5. **Bio-vs-category edge case:** Request a Tutor in the city where P0050 (Nasreen Akhtar, bio about bridal lehengas) exists → assert she is NOT in `top_3` OR if present, the reasoning explicitly flags the bio mismatch (search for "lehenga" or "bridal" or "stitching" in reasoning text).

**Test structure:**
- Module-scoped fixtures for `IntentAgent`, `DiscoveryAgent`, `RankingAgent`
- Helper to run the full intent→discovery→ranking pipeline for a given query
- 13-second `autouse` delay between tests
- REQUIRED_KEYS check on ranking output

---

## Execution Order

1. **geo_service.py** — standalone, no dependencies on other new code
2. **trace_writer.py** — add `write_discovery_trace()` and `write_ranking_trace()`
3. **discovery_agent.py** — depends on geo_service (for city extraction), trace_writer
4. **ranking_agent.py** — depends on geo_service, trace_writer, Intent Agent schemas
5. **main.py** — wire the pipeline, update response model, version bump
6. **test_geo_service.py** — run immediately (no LLM)
7. **test_discovery_agent.py** — run immediately (no LLM)
8. **test_ranking_agent.py** — run (5 LLM calls × ~15s each + 13s delays = ~3–4 min)
9. **Git commit + push**

## Verification Plan

### Automated Tests
```
.venv\Scripts\python.exe -m pytest tests/test_geo_service.py -v --tb=short
.venv\Scripts\python.exe -m pytest tests/test_discovery_agent.py -v --tb=short
.venv\Scripts\python.exe -m pytest tests/test_ranking_agent.py -v --tb=short
```

### Manual Verification
- Start server → POST `/request` with `"AC bana de yaar Lahore mein, jaldi"`
- Confirm response has all three stages: `intent`, `discovery`, `ranking`
- Verify `ranking.top_3` reasoning is in Roman Urdu with casual tone
- Inspect the three trace files (intent, discovery, ranking)
- Confirm no Haversine code exists outside `geo_service.py`

### Commit
```
git add .
git commit -m "Phase 2: Discovery + Ranking agents with geo_service abstraction, tone-mirroring, and consistency reasoning"
git push origin main
```
