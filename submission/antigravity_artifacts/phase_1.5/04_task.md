# Phase 1.5 — Daira-e-Hunar Execution Tracker

- [ ] **1. Archive Phase 1 traces** → move `trace/intent_*.json` to `trace/archive/phase_1/`
- [ ] **2. Rename project identity** → config.py, main.py, conftest.py, agents/__init__.py docstrings
- [ ] **3. Regenerate providers.json** → 100 providers, 8 cities, expanded schema, edge cases
- [ ] **4. Expand Intent Agent** → 3 new IntentResult fields, updated system prompt with sector format rules + new few-shot examples
- [ ] **5. Update trace writer** → summary line includes formality/register/code_switching
- [ ] **6. Update test suite** → 2 new tests, existing tests assert new fields, REQUIRED_KEYS expanded
- [ ] **7. Rewrite README.md** → Project Overview + Privacy Note + tagline
- [ ] **8. Run pytest** → all 10 tests pass
- [ ] **9. Smoke test 1** → "AC bana de yaar Lahore mein, jaldi"
- [ ] **10. Smoke test 2** → "Mohtarma, mujhe Karachi ke Lyari ilaaqe mein ek aitbaari plumber ki zaroorat hai is hafte."
- [ ] **11. Validate providers.json** → count, distribution, schema, edge cases
- [ ] **12. Git commit + push** → single commit, verify .env not staged, clean state
