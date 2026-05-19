# Phase 2 — Execution Tracker

- [ ] **1. geo_service.py** — Haversine, KNOWN_LOCATIONS (38 neighborhoods), CITY_CENTROIDS, resolve_user_location
- [ ] **2. trace_writer.py** — add write_discovery_trace() and write_ranking_trace()
- [ ] **3. discovery_agent.py** — deterministic filter by home_city + service_type, fallback logic
- [ ] **4. ranking_agent.py** — LLM-driven ranking, 5-pillar system prompt, tone mirroring
- [ ] **5. main.py** — chain Intent → Discovery → Ranking, update ServiceResponse, version 0.4.0
- [ ] **6. test_geo_service.py** — 4 unit tests (no LLM)
- [ ] **7. test_discovery_agent.py** — 4 deterministic tests (no LLM)
- [ ] **8. test_ranking_agent.py** — 5 LLM tests with 13s delays
- [ ] **9. Run all tests** — verify all pass
- [ ] **10. Manual smoke test** — POST /request, inspect 3 trace files
- [ ] **11. Git commit + push**

## User Adjustments Applied
1. Roman Urdu assertion: ≥3 whole-word matches from curated marker list via `\b` regex
2. Urdu script assertion: ≥20 characters in U+0600–U+06FF range
3. Pashto test: VERIFIED — P0078 (Dost Muhammad, Quetta Electrician) speaks Pashto
4. Ranking payload: include next 2–3 slot timestamps, not just count
5. top_3 → up to 3 (1–3 items), explicit prompt instruction, no padding
