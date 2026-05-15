# Phase 1 — Task Tracker

## Mock Data
- [x] Generate `mock_data/providers.json` with 50 synthetic providers
- [x] Verify all edge cases (P0017 low rating, P0033 no slots, P0008/P0029 overlap, P0047 misleading name)

## Trace Writer
- [/] Create `backend/services/trace_writer.py`

## Intent Agent
- [ ] Implement `backend/agents/intent_agent.py` with google-genai SDK + JSON mode
- [ ] System prompt with 5 few-shot examples + conservative confidence guidance

## API Wiring
- [ ] Update `backend/main.py` — wire POST /request to Intent Agent

## Dependencies
- [ ] Update `backend/requirements.txt` with pytest, pytest-asyncio

## Tests
- [ ] Create `tests/__init__.py`, `tests/conftest.py`
- [ ] Create `tests/test_intent_agent.py` with 8 test cases
- [ ] Run tests and verify all pass

## Verification
- [ ] Manual smoke test via /docs endpoint
