# Phase 1.5 — Realignment to Daira-e-Hunar

Patch the Phase 1 codebase to align with the new project identity, expand the provider dataset from 50 → 100 across 8 Pakistani cities, and add multi-signal extraction to the Intent Agent. No new architecture — primarily data regeneration, schema updates, and prompt engineering.

---

## Proposed Changes

### Component 1: Project Identity Rename

All "ServiceWala" references in **active source code** become "Daira-e-Hunar". Trace files in `trace/` are archived (not edited).

#### [MODIFY] [README.md](file:///d:/Infromal%20Economy/README.md)
- Title line → `# Daira-e-Hunar (دائرۂ ہنر) — AI Service Orchestrator for Pakistan's Informal Economy`
- Add tagline block (all three forms: Roman Urdu primary, Urdu script primary, English parenthetical)
- Rewrite "Project Overview" section with the Daira-e-Hunar vision (provider dignity, leveling economic reach, cultural unity)
- Rewrite "Privacy Note" section — explicitly state ALL provider data is synthetic (`_synthetic: true`), frame as ethical choice

#### [MODIFY] [main.py](file:///d:/Infromal%20Economy/backend/main.py)
- Docstring: "ServiceWala API" → "Daira-e-Hunar API"
- `FastAPI(title=...)`: → `"Daira-e-Hunar API"`
- `description`: → `"Daira-e-Hunar — AI Service Orchestrator for Pakistan's Informal Economy"`
- Health check `service` field: → `"Daira-e-Hunar API"`

#### [MODIFY] [config.py](file:///d:/Infromal%20Economy/backend/config.py)
- Docstring: "ServiceWala" → "Daira-e-Hunar"

#### [MODIFY] [conftest.py](file:///d:/Infromal%20Economy/tests/conftest.py)
- Docstring: "ServiceWala" → "Daira-e-Hunar"

#### [MODIFY] [intent_agent.py](file:///d:/Infromal%20Economy/backend/agents/intent_agent.py)
- `SYSTEM_PROMPT` opening: "ServiceWala" → "Daira-e-Hunar"

> [!NOTE]
> The `Antigravity_Roadmap.md` and `submission/` artifacts are historical references — they will NOT be edited. Old trace JSON files contain "ServiceWala" in `prompt_sent_to_llm` — these are archived, not modified.

---

### Component 2: Provider Data Regeneration (`providers.json`)

#### [MODIFY] [providers.json](file:///d:/Infromal%20Economy/mock_data/providers.json)

Replace the existing 50-provider file with exactly **100 synthetic providers** across 8 cities.

**City distribution:**

| City | Count | Neighborhoods (real working-class areas) |
|------|-------|------------------------------------------|
| Islamabad | 5 | G-7, G-9, I-9, I-10 |
| Rawalpindi | 15 | Tench Bhata, Dhok Khabba, Raja Bazaar, Pirwadhai, Saddar |
| Lahore | 20 | Misri Shah, Shadbagh, Garhi Shahu, Daroghewala, Walled City (Mochi Gate, Lohari Gate, Bhatti Gate) |
| Faisalabad | 20 | Ghulam Mohammadabad, Madina Town outskirts, Jhang Bazaar, D-Ground area, Rail Bazaar |
| Karachi | 10 | Lyari, Orangi, Korangi, Landhi, Baldia Town |
| Quetta | 10 | Pashtunabad, Hazara Town, Kandahari Bazaar, Jinnah Road area |
| Peshawar | 10 | Hashtnagri, Kohati Gate, Inner City (Qissa Khwani), Faqirabad |
| Gilgit | 10 | Konodas, Jutial, Kashrote, Danyor, Main Bazaar |

**Schema changes (new fields added to every provider):**

```json
{
  "id": "P0001",
  "name": "Muhammad Aslam",
  "category": "AC Technician",
  "sector": "Misri Shah, Lahore",
  "home_city": "Lahore",
  "lat": 31.5780,
  "lng": 74.3190,
  "rating": 4.3,
  "rating_count": 87,
  "price_range": { "min": 1500, "max": 4000, "currency": "PKR" },
  "available_slots": ["2026-05-20T09:00:00+05:00", ...],
  "verified": true,
  "languages_spoken": ["Urdu", "Punjabi"],
  "bio": "15 years fixing ACs across Pindi. Trained his son in the trade.",
  "years_experience": 15,
  "cultural_background": null,
  "_synthetic": true
}
```

**New fields:**
- `bio` (string) — 1–2 sentence human story, varied in tone/length/specificity
- `years_experience` (int, 1–40, weighted toward 5–20)
- `home_city` (string) — one of the 8 cities
- `cultural_background` (string|null) — ~40% non-null, matching realistic regional demographics:
  - Quetta: mostly Pashtun, Baloch, Hazara
  - Karachi: Muhajir, Sindhi, Baloch, Sheedi (in Lyari)
  - Peshawar: Pashtun
  - Gilgit: Gilgiti, some Balti
  - Lahore/Faisalabad: Punjabi, Saraiki
  - Rawalpindi/Islamabad: Punjabi, Pashtun mix

**Coordinate sourcing:** Real centroids of named neighborhoods from OpenStreetMap/Google Maps knowledge. Each provider's lat/lng will be placeable on a real map.

**Name pool:** Realistic working-class Pakistani names — mixed gender, mixed ethnicity. No generic "Muhammad X" patterns. Mix of:
- Common: Muhammad Aslam, Ali Raza, Fatima Bibi, Saima Bano
- Regional: Saifullah Achakzai, Gul Bibi, Niaz Hussain Hazara, Imran Sheedi
- Working-class patterns: patronymics, no "Syed", fewer status-surnames

**Preserved edge cases (re-implemented with new IDs):**

| Phase 1 ID | Edge Case | Phase 1.5 Equivalent |
|------------|-----------|---------------------|
| P0017 | Low rating (2.1, 9 reviews) — tests ranking filter | Re-implemented in new dataset |
| P0033 | No available slots (or very few) — tests Action Agent | Re-implemented (fully booked) |
| P0008/P0029 | Overlapping expertise (AC tech who does electrical) | Re-implemented via `bio` + `notes` |
| P0047 | Misleading name ("Noor Electric" → Beautician) | Re-implemented with similarly misleading name |

**New edge case (req #7):**
- A provider whose `bio` strongly implies one specialty (e.g., "Famous for stitching bridal lehengas for Lahori weddings") but whose `category` is "Tutor" (she also tutors Urdu literature). Tests that future Ranking Agent reads bio context.

---

### Component 3: Intent Agent Expansion

#### [MODIFY] [intent_agent.py](file:///d:/Infromal%20Economy/backend/agents/intent_agent.py)

**IntentResult Pydantic schema — 3 new fields:**

```python
formality_level: Literal["formal", "casual", "slang"] = Field(
    description="The formality level of the user's input..."
)
literacy_register: Literal["high", "medium", "low"] = Field(
    description="Inferred literacy register for response calibration..."
)
code_switching: bool = Field(
    description="True if the input mixes English and Urdu/Roman Urdu..."
)
```

**SYSTEM_PROMPT updates:**
- "ServiceWala" → "Daira-e-Hunar"
- Scope broadened from "Islamabad and Rawalpindi" → "across Pakistan (Islamabad, Rawalpindi, Lahore, Faisalabad, Karachi, Quetta, Peshawar, Gilgit)"
- Known sectors/areas expanded to include neighborhoods from all 8 cities
- New section: `## Formality and register detection` with:
  - Explicit definitions and examples for each `formality_level` value
  - Respectful framing of `literacy_register` ("matching register so the response feels natural")
  - `code_switching` detection rules
- Few-shot examples updated/expanded to demonstrate the new fields
- `location_sector` description updated to include the broader geography

**Fallback parse dict** in `except json.JSONDecodeError` updated to include `formality_level`, `literacy_register`, `code_switching` defaults.

---

### Component 4: Trace Writer Update

#### [MODIFY] [trace_writer.py](file:///d:/Infromal%20Economy/backend/services/trace_writer.py)

- `_build_summary()` updated to include new signals when present in `parsed_output`
- Example output: `"Parsed casual roman_urdu request (code_switched) -> AC Technician in G-13, tomorrow morning, confidence 0.92"`
- The `parsed_output` dict already flows through — no schema change needed in the trace JSON structure itself, just the summary line

---

### Component 5: Test Suite Updates

#### [MODIFY] [test_intent_agent.py](file:///d:/Infromal%20Economy/tests/test_intent_agent.py)

**New test cases (2):**

```python
# Test 9: Casual slang
async def test_formality_casual_slang(agent):
    text = "AC bana de bhai G-13 mein kal subah"
    # asserts formality_level == "slang" (or "casual" — slang is acceptable)
    # asserts new fields exist

# Test 10: Code-switching
async def test_code_switching(agent):
    text = "Mujhe ek good plumber chahiye urgent F-10 mein"
    # asserts code_switching == true
    # asserts new fields exist
```

**Existing test updates:**
- `REQUIRED_KEYS` set expanded with `"formality_level"`, `"literacy_register"`, `"code_switching"`
- `test_english_clear`: additionally assert `formality_level` is `"formal"` and `code_switching` is `False`
- `test_urdu_script`: additionally assert the three new fields exist with valid values
- 13-second inter-test delay preserved

---

### Component 6: Trace Archiving

#### [NEW] `trace/archive/phase_1/` directory

- Move all 15 existing `trace/intent_*.json` files to `trace/archive/phase_1/`
- Keep `trace/.gitkeep` in place
- New traces from Phase 1.5+ will be written to `trace/` root using the new schema

---

## Execution Order

1. **Archive traces** → `trace/archive/phase_1/` (move files, non-destructive)
2. **Rename project identity** → config.py, main.py, conftest.py (simple find-replace)
3. **Regenerate providers.json** → 100 providers, new schema, all edge cases
4. **Expand IntentResult schema + system prompt** → intent_agent.py
5. **Update trace writer** → trace_writer.py summary line
6. **Update test suite** → test_intent_agent.py (new tests + existing test assertions)
7. **Rewrite README.md** → Project Overview + Privacy Note + tagline
8. **Run pytest** → verify all 10 tests pass
9. **Manual smoke test** → POST `/request` with "AC bana de yaar Lahore mein, jaldi"
10. **Validate providers.json** → count, city distribution, schema, edge cases
11. **Git commit + push**

## Verification Plan

### Automated Tests
- `d:\Infromal Economy\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short` — all 10 tests pass
- Confirm `REQUIRED_KEYS` now includes the 3 new fields

### Manual Verification
- Start server with `uvicorn backend.main:app --reload`
- POST `/request` with `{"query": "AC bana de yaar Lahore mein, jaldi"}` 
- Confirm response includes `formality_level`, `literacy_register`, `code_switching` with sensible values
- Show the new trace file contents
- Validate providers.json: exactly 100 entries, correct city distribution (5+15+20+20+10+10+10+10), all new fields present, edge cases intact
- `git ls-files --cached | Select-String "\.env$"` → must be empty
- Final `git status` → clean working tree
