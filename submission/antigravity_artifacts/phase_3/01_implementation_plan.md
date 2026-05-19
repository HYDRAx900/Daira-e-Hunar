# Phase 3: Action Agent + Orchestrator + End-to-End Loop

Closes the observe → reason → decide → act → evaluate → adapt pipeline. After Phase 3, `POST /request` accepts a query and returns a confirmed (mock) booking with scheduled follow-ups and a complete run trace.

## User Review Required

> [!IMPORTANT]
> **Slot timestamps are hardcoded to May 20-28 2026 in providers.json.** The canonical demo query for May 21 morning has been verified to work with the mock data and will produce a non-negotiated booking. However, note that dynamic `urgency="now"/"today"` queries will exercise the `time_negotiated: true` fallback if the system date is outside the May 20-28 window. This is intentional — the mock data is synthetic.

> [!WARNING]
> **providers.json is mutated on every booking.** Each successful `POST /request` removes a slot from the file. Repeated runs will exhaust slots. This is by design for the demo — the file is restored by `git checkout`.

## Proposed Changes

### Action Agent

#### [MODIFY] [action_agent.py](file:///d:/Infromal%20Economy/backend/agents/action_agent.py)

Complete rewrite of the Phase 0 stub. The file grows from 43 lines to ~350 lines.

**Pydantic schemas** (top of file):
- `ConfirmationMessage(BaseModel)` — `text: str`, `language: str`. Used as the JSON-mode response schema for the LLM call.
- `BookingResult(BaseModel)` — the full output schema as specified in the request (status, booking_id, provider_id, provider_name, scheduled_datetime, confirmation_message, confirmation_language, time_negotiated, followups_scheduled, receipt_path, error_reason).

**Class `ActionAgent`:**
- `__init__`: Initialize genai client (same pattern as IntentAgent/RankingAgent). Store `MOCK_DATA_DIR` paths.
- `async def run(self, intent: dict, ranking: dict, selected_provider_id: str | None = None) -> dict`:
  - Signature change from stub: takes `intent`, full `ranking` dict (not just a provider), and optional `selected_provider_id` (defaults to `ranking["top_3"][0]["provider_id"]`).
  - Calls the private methods below in sequence.

**Deterministic private methods:**
- `_load_providers() -> list[dict]`: Read providers.json from disk (fresh read every call — needed for race-condition correctness).
- `_find_provider(providers, provider_id) -> dict | None`: Linear scan by ID.
- `_select_slot(provider, intent) -> tuple[str | None, bool]`: Returns `(slot_iso, time_negotiated)`.
  - Parses `intent["requested_time"]` and `intent["urgency"]` to determine a window.
  - Window logic:
    - `requested_time` containing "morning" → 06:00-11:59 filter on the relevant date.
    - `requested_time` containing "afternoon" → 12:00-16:59.
    - `requested_time` containing "evening" → 17:00-21:00.
    - `urgency="now"/"today"` → today's date only.
    - `urgency="this_week"` → next 7 days.
    - `urgency="flexible"` or no match → any available slot.
  - If no slot matches the window, fall back to earliest available + set `time_negotiated=True`.
  - If zero slots at all, return `(None, False)`.
- `_race_check_and_reserve(provider_id, chosen_slot) -> bool`: Re-reads providers.json, confirms slot exists, removes it, writes atomically (`.tmp` + `os.replace`). Returns `True` if success, `False` if slot was taken.
- `_write_booking(booking_data) -> None`: Reads bookings.json (creates `[]` if missing), appends, writes back.
- `_write_followups(booking_id, scheduled_datetime) -> list[str]`: Creates 2 followup entries (reminder 1h before, rating_prompt 2h after). Reads/creates followups.json. Returns list of followup IDs.
- `_write_receipt(booking_id, booking_data, confirmation_text, followups) -> str`: Writes `trace/receipt_<booking_id>.txt` — plain text receipt. Returns relative path.

**LLM method:**
- `_generate_confirmation(intent, provider, scheduled_datetime, time_negotiated) -> tuple[str, str]`: Single gemini-2.5-flash call with JSON-mode + `ConfirmationMessage` schema. Tone-mirroring prompt mirrors the same language/formality/code-switching constraints from Ranking. 3-attempt retry on 429/503. Returns `(text, language)`.

**Edge-case returns:**
- No provider found in providers.json → `BookingResult(status="no_provider", ...)`
- Provider has zero slots → `BookingResult(status="no_slots_available", error_reason="...")`
- Race condition (slot taken between select and reserve) → `BookingResult(status="slot_taken", error_reason="...")`

**Trace:** Calls `write_action_trace()` at the end of `run()` before returning.

---

### Trace Writer Extensions

#### [MODIFY] [trace_writer.py](file:///d:/Infromal%20Economy/backend/services/trace_writer.py)

Add two new functions at the end of the file. No existing functions are modified.

**`write_action_trace(...) -> str`:**
- Parameters: `intent_input`, `selected_provider`, `slot_chosen`, `race_check_result`, `confirmation_prompt`, `raw_llm_response`, `parsed_booking_result`, `latency_ms`.
- Writes `trace/action_<timestamp>.json` with the same pattern as existing trace functions.
- Summary line: `"ACTION booking_id=B... | provider=... | slot=... | status=confirmed | negotiated=false"`.

**`write_run_trace(workplan: dict) -> str`:**
- Writes `trace/run_<run_id>.json`.
- Includes the full workplan dict, final status, and a top-level summary line.
- Summary format: `"AGENTIC RUN run_... | query: '...' | status: confirmed | provider: ... | latency: ...ms | N stages OK"`.

---

### Mock Data Scaffolding

#### [MODIFY] [bookings.json](file:///d:/Infromal%20Economy/mock_data/bookings.json)

Already exists with `[]`. No change needed — the Action Agent creates entries at runtime.

#### [NEW] [followups.json](file:///d:/Infromal%20Economy/mock_data/followups.json)

Create with `[]` as initial content. The Action Agent appends entries at runtime.

---

### Orchestrator

#### [NEW] [orchestrator.py](file:///d:/Infromal%20Economy/backend/orchestrator.py)

**Function `run_request(user_query: str, mode: str = "agentic") -> dict`:**

```
1. If mode == "baseline": raise NotImplementedError("Baseline mode is Phase 5")
2. Generate run_id = f"run_{timestamp}"
3. Initialize workplan = { run_id, user_query, mode, started_at, stages: [] }
4. Run IntentAgent.run(user_query)
   → append to stages: { agent: "intent", trace_file, summary, success, latency_ms }
   → if intent.needs_clarification: short-circuit, write run trace, return
5. Run DiscoveryAgent.run(intent)
   → append to stages
   → if zero candidates: invoke ActionAgent with graceful "no providers" path,
     write run trace, return
6. Run RankingAgent.run(candidates, intent)
   → append to stages
   → if empty top_3: same short-circuit as zero candidates
7. Run ActionAgent.run(intent, ranking, top_3[0].provider_id)
   → append to stages
8. Write trace/run_<run_id>.json via write_run_trace
9. Return full result dict
```

The orchestrator instantiates all four agents in its own `__init__` or as module-level singletons. Since `main.py` currently creates agents at module level, the orchestrator will import and reuse those instances — no, actually, the orchestrator will own its own agent instances to keep it self-contained. `main.py` will create one `Orchestrator` instance and delegate.

- The Action Agent owns ALL user-facing message generation, including no-providers and needs-clarification fallback messages.
- The orchestrator invokes Action even on short-circuit paths, passing an empty ranking or a sentinel flag.
- We will add `_generate_no_provider_message()` as an explicit private method in ActionAgent.
- The `BookingResult` schema accommodates non-booking outputs (the "no_provider" status field already exists).

---

### API Update

#### [MODIFY] [main.py](file:///d:/Infromal%20Economy/backend/main.py)

- Version bump `0.4.0` → `0.5.0` in `FastAPI()` constructor and health check.
- Replace the inline pipeline logic in `handle_request()` with a single call to `orchestrator.run_request(request.query, request.mode)`.
- Update `ServiceResponse` to add: `booking: Optional[dict] = None`, `run_trace: Optional[str] = None`.
- Remove individual agent imports; import only `Orchestrator` (or import from `backend.orchestrator`).
- The orchestrator returns a dict that `handle_request()` maps to `ServiceResponse`.

---

### Test Suite — Action Agent

#### [NEW] [test_action_agent.py](file:///d:/Infromal%20Economy/tests/test_action_agent.py)

**All tests are DETERMINISTIC — no real LLM calls.** The LLM call for confirmation is mocked using `unittest.mock.patch`.

**Fixtures:**
- `tmp_mock_dir(tmp_path)`: Creates a temporary copy of `providers.json` in `tmp_path/mock_data/`. Patches `backend.config.MOCK_DATA_DIR` to point to `tmp_path/mock_data/`. Also creates empty `bookings.json` and `followups.json`.
- `mock_intent`: Returns a realistic IntentResult dict (roman_urdu, casual, AC Technician, Islamabad, tomorrow morning, this_week).
- `mock_ranking`: Returns a realistic RankingResult dict with `top_3` containing `P0003` (an Islamabad AC Technician from providers.json).
- `mock_llm_confirmation`: Patches `genai.Client.models.generate_content` to return a canned `ConfirmationMessage` JSON response.

**Tests:**
1. **`test_happy_path`**: Run action → assert `status="confirmed"`, booking_id starts with "B", bookings.json has 1 entry, providers.json lost 1 slot for P0003, followups.json has 2 entries, receipt file exists.
2. **`test_slot_taken_race_condition`**: After slot selection but before reservation, modify providers.json to remove the slot. Assert `status="slot_taken"`.
   - Implementation: Explicitly call `_select_slot` to get a slot, directly mutate the temp `providers.json` to remove that slot from the provider's `available_slots`, then call `_race_check_and_reserve` and assert it returns False.
3. **`test_no_slots_available`**: Modify temp providers.json to set the target provider's `available_slots` to `[]`. Assert `status="no_slots_available"`.
4. **`test_time_negotiation`**: Set intent urgency to "today" but ensure the provider only has slots on future dates (not today). Assert booking succeeds with `time_negotiated=true`.
5. **`test_atomicity`**: Verify that after a successful booking, providers.json is valid JSON (not corrupted). This is a structural test — the `.tmp + rename` pattern guarantees atomicity, and we verify the file remains parseable.

---

### Test Suite — Orchestrator

#### [NEW] [test_orchestrator.py](file:///d:/Infromal%20Economy/tests/test_orchestrator.py)

**All tests are DETERMINISTIC — mock all four agent calls.** Use `unittest.mock.AsyncMock` to replace each agent's `.run()` method.

**Fixtures:**
- `mock_orchestrator`: Creates an `Orchestrator` instance with all four agents' `.run()` methods replaced by `AsyncMock`s returning realistic canned responses.

**Tests:**
1. **`test_full_happy_path`**: All 4 agents return success → run trace has 4 stages, all with `success=True`. Final result contains booking data.
2. **`test_needs_clarification_short_circuit`**: IntentAgent returns `needs_clarification=True` → only 1 stage in run trace, no Discovery/Ranking/Action calls.
3. **`test_zero_discovery_candidates`**: Discovery returns `candidates=[]` → short-circuits, ActionAgent is called with empty ranking for graceful message, run trace has appropriate stages. Assert the response language matches `intent["detected_language"]`.
4. **`test_baseline_mode_raises`**: `mode="baseline"` → raises `NotImplementedError`.

---

## Verification Plan

### Automated Tests

```bash
# Run only Phase 3 tests (fast, no LLM)
python -m pytest tests/test_action_agent.py tests/test_orchestrator.py -v

# Run full suite (includes Phase 1/2 LLM tests — slower)
python -m pytest tests/ -v
```

### Manual Smoke Test

After tests pass, start the server and hit `POST /request` with:

1. **Happy path**: `{"query": "Mujhe kal subah G-13 mein AC technician chahiye"}`
   - Expect: full run trace with 4 stages, confirmed booking, receipt file.

2. **Nonsense input**: `{"query": "asdfghjkl potato moon"}`
   - Expect: needs_clarification short-circuit, partial trace.

3. **Empty category/city combo**: `{"query": "I need a tutor in Gilgit"}` (Gilgit has tutors — pick a combo known to be empty after fallback)
   - Better: `{"query": "I need a beautician in Quetta"}` — check if Quetta has beauticians; if not, it'll trigger fallback. If fallback also finds none, we get the zero-candidates path.

### Files Changed Summary

| File | Action | Lines (est.) |
|------|--------|-------------|
| `backend/agents/action_agent.py` | Rewrite | ~350 |
| `backend/services/trace_writer.py` | Extend | +80 |
| `backend/orchestrator.py` | New | ~200 |
| `backend/main.py` | Modify | ~50 changed |
| `mock_data/followups.json` | New | 1 |
| `tests/test_action_agent.py` | New | ~250 |
| `tests/test_orchestrator.py` | New | ~180 |

**No new dependencies.** No changes to requirements.txt. All file I/O uses stdlib (`json`, `os`, `pathlib`, `datetime`, `random`, `time`).
