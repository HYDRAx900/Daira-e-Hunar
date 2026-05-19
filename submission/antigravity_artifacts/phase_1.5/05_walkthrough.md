# Phase 1.5 — Realignment to Daira-e-Hunar

The realignment patch is complete! We have updated the codebase from "ServiceWala" to "**Daira-e-Hunar**" (دائرۂ ہنر) and significantly expanded both the provider dataset and the Intent Agent's capabilities.

## Changes Made

### 1. Project Identity Update
- Renamed all instances of "ServiceWala" in `config.py`, `main.py`, `conftest.py`, and the `intent_agent.py` system prompt.
- Bumped API version to `0.3.0`.
- Rewrote the `README.md` to include the new project name, cultural tagline (in Roman Urdu, Urdu Script, and English), and an ethical privacy note explicitly stating all provider data is synthetic.

### 2. Provider Data Expansion (`providers.json`)
- Replaced the initial 50 providers with exactly **100 synthetic providers** spread across 8 Pakistani cities (Islamabad, Rawalpindi, Lahore, Faisalabad, Karachi, Quetta, Peshawar, Gilgit).
- Used realistic, working-class neighborhood coordinates (e.g. `Lyari, Karachi`, `Misri Shah, Lahore`).
- Added new fields:
  - `bio`: Humanized stories for each provider (e.g., "15 years fixing ACs across Pindi.").
  - `years_experience`: (1–40 years).
  - `home_city`: The provider's home city.
  - `cultural_background`: Regional demographics matched with cities (e.g., Punjabi, Pashtun, Baloch).
- Re-implemented all 4 previous edge cases and added a 5th: A tutor who makes bridal lehengas, which tests the Ranking Agent's ability to discern category versus bio context.

### 3. Intent Agent Enhancement
- Upgraded the Pydantic schema (`IntentResult`) to extract three new socio-linguistic signals:
  - `formality_level`: formal, casual, slang
  - `literacy_register`: high, medium, low
  - `code_switching`: true/false (detects English/Urdu mixing)
- Broadened the `location_sector` parsing to handle `Neighborhood, City` output format (e.g. `G-13, Islamabad`) and city-only format (e.g. `Lahore`).
- Updated `trace_writer.py` to embed these new fields in the top-level trace summary line.

### 4. Trace Archiving
- Safely moved all 15 old `trace/intent_*.json` files to `trace/archive/phase_1/`.
- New traces now write cleanly to the `trace/` directory.

### 5. Validation & Testing
- Added new tests for `test_formality_casual_slang` and `test_code_switching`.
- Fixed existing location assertions to match the new `Neighborhood, City` format.
- Ran the test suite against the Gemini 2.5 Flash model and **all 10 tests passed**.

## Validation Results

We executed two targeted smoke tests directly against the Intent Agent to verify the new fields.

**Smoke Test 1: Casual/Slang**
*Input*: `"AC bana de yaar Lahore mein, jaldi"`
*Parsed*:
- `service_type`: "AC Technician"
- `location_sector`: "Lahore"
- `urgency`: "now"
- `formality_level`: **"slang"**
- `literacy_register`: **"low"**
- `code_switching`: **false**

**Smoke Test 2: Formal Code-Switched**
*Input*: `"Mohtarma, mujhe Karachi ke Lyari ilaaqe mein ek aitbaari plumber ki zaroorat hai is hafte."`
*Parsed*:
- `service_type`: "Plumber"
- `location_sector`: "Lyari, Karachi"
- `urgency`: "this_week"
- `formality_level`: **"formal"**
- `literacy_register`: **"high"**
- `code_switching`: **false**

All changes have been successfully committed to `main` with a clean working tree. The foundation for Daira-e-Hunar is now ready for the Phase 2 agents.
