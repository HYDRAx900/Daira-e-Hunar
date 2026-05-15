# Phase 1 Walkthrough: Mock Data + Intent Agent

Phase 1 of the Antigravity Roadmap is complete. We've laid the data foundation and built the first LLM-powered agent for the ServiceWala orchestrator.

## What Was Accomplished

1. **Mock Data Generation (`mock_data/providers.json`)**
   - Wrote a reproducible script to generate exactly 50 synthetic service providers across 8 sectors.
   - Enforced strict schema adherence, including structured `price_range` and ISO 8601 datetimes for `available_slots`.
   - Embedded intentional realism for later phases:
     - `P0017`: A provider with a low rating (2.1).
     - `P0033`: A provider with 0 available slots in the next 24 hours.
     - `P0008` & `P0029`: Providers with overlapping expertise (via a `notes` field).
     - `P0047`: A provider named "Noor Electric" who is actually a Beautician.
   - Verified that all entries carry the mandatory `_synthetic: true` flag.

2. **Trace Writer (`backend/services/trace_writer.py`)**
   - Implemented a robust logging utility to capture the full LLM pipeline.
   - Traces include the raw user input, the complete prompt sent, the raw JSON string returned by Gemini, and the final parsed Pydantic object.
   - Added a human-readable `summary` line to make judge review easy.
   - Traces are saved in `trace/` using UTC timestamps for sortability.

3. **Intent Agent (`backend/agents/intent_agent.py`)**
   - Built a robust single-call agent using `google-genai`.
   - Used `response_mime_type="application/json"` combined with a Pydantic `response_schema` (`IntentResult`) to guarantee structured extraction.
   - Crafted a detailed system prompt with 5 multilingual few-shot examples (English, Urdu script, Roman Urdu).
   - Instructed the model to be conservative with confidence scoring and aggressively surface ambiguities via `needs_clarification`.

4. **API Wiring (`backend/main.py`)**
   - Updated the FastAPI POST `/request` endpoint to call the Intent Agent.
   - The endpoint now returns the successfully parsed intent and a link to the generated trace file.

5. **Test Suite (`tests/test_intent_agent.py`)**
   - Wrote 8 comprehensive `pytest` cases covering various languages and edge cases (ambiguous inputs, nonsense).
   - Tests execute real API calls against Gemini to validate the prompt and schema.
   - Implemented a 13-second auto-delay fixture to successfully navigate Gemini's 5 req/min free-tier rate limits.

## Validation Results

- **Data Generator:** Sanity checks confirmed 50 distinct providers, 8 sectors, and expected edge cases.
- **Test Suite:** All 8 tests passed successfully after addressing rate limits.
- **Manual Smoke Test:** Pinging `/request` with `"Mujhe G-13 mein AC technician chahiye abhi"` successfully yielded a parsed intent identifying an AC Technician in G-13 with urgent priority ("now"), and generated a clean, readable trace file.

## Next Steps

We are now ready for Phase 2: Building the Discovery Agent to match parsed intents against the mock data.
