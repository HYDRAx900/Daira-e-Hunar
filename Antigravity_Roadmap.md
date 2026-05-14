# AI Seekho 2026 — Challenge 2 Roadmap
## AI Service Orchestrator for the Informal Economy

> **Your role:** architect & reviewer.
> **Antigravity's role:** implementer.
> **My role (already done):** translator from "problem statement" to "buildable plan."

---

## 1. What you're actually building (plain English)

A **mobile app** where someone can type something like *"Mujhe kal subah G-13 mein AC technician chahiye"* and an **AI agent system** running behind the scenes will:

1. **Understand** the request (in Roman Urdu, Urdu, or English).
2. **Find** matching service providers near that location.
3. **Reason** about which provider is the best fit and explain *why*.
4. **Book** a slot (simulated — writing to a mock booking log).
5. **Follow up** (set a reminder, send a confirmation message, prompt for a rating after the job).

The catch: **the system must visibly think.** Not "if user types 'AC' return list-of-AC-guys." Every decision must come from an LLM-driven agent that observes → reasons → decides → acts → evaluates → adapts. The judges will read the logs. The logs are the product.

---

## 2. Decisions to confirm (or override before you start)

| Decision | My default | Why | Override only if |
|---|---|---|---|
| Mobile platform | **Flutter** (Android + web). Develop on web preview, demo primarily on a real Android phone (cut in 20–30s of emulator as backup) | One Flutter codebase covers all three. Web preview is the fastest dev loop. Real phone on screen satisfies "mobile app mandatory" visibly | You already know React Native better |
| Backend language | **Python** (FastAPI server) | Google ADK only really exists in Python; trace/log story is best here | You can't run Python locally |
| Agent framework | **Google ADK** (Agent Development Kit) | Native multi-agent framework from Google, produces structured traces automatically, pairs perfectly with Antigravity | None — this is the right choice |
| LLM | **Gemini 3 Flash** for agent reasoning (Gemini 3 Pro for Antigravity itself) | Flash is ~10x cheaper, fast enough for this. Pro for code generation in Antigravity | None |
| Data source | **Mock data only for v1.** Geo logic is abstracted behind a small service module so Google Maps can be swapped in as a stretch goal (Phase 6.5) | Hackathon rules explicitly allow; mock keeps you shippable. The abstraction is 20 lines of code and unlocks easy Maps integration later | None |
| Hosting | **Everything local** during demo | No DevOps for a 2nd-semester student. Run `uvicorn` + `flutter run` on your laptop | You actually want to deploy (skip for v1) |

---

## 3. System architecture

```
┌─────────────────────────────────────────────────────────────┐
│  FLUTTER MOBILE APP (user-facing)                           │
│  ─ Chat input (multilingual)                                │
│  ─ Message bubbles                                          │
│  ─ Reasoning panel (expandable: "see how the agent thought")│
│  ─ Booking confirmation card                                │
└────────────────────────┬────────────────────────────────────┘
                         │  HTTP (localhost:8000)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  PYTHON BACKEND  (FastAPI + Google ADK)                     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Intent Agent │→ │ Discovery    │→ │ Ranking      │       │
│  │ (parse NL)   │  │ Agent        │  │ Agent (LLM   │       │
│  │              │  │ (filter mock │  │ reasoning)   │       │
│  │              │  │ DB by sector │  │              │       │
│  │              │  │ + service)   │  │              │       │
│  └──────────────┘  └──────────────┘  └──────┬───────┘       │
│                                              │              │
│                       ┌──────────────────────▼──────────┐   │
│                       │ Action Agent                    │   │
│                       │ (write booking, gen confirmation│   │
│                       │ schedule follow-up)             │   │
│                       └─────────────────────────────────┘   │
│                                                              │
│  Every step writes structured logs → trace/                 │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  mock_data/  │
                  │  providers.json (50 synthetic)│
                  │  bookings.json (gets appended)│
                  │  trace/      (one file per request)│
                  └──────────────┘
```

The four agents are real, separate ADK agents — not just function calls. That's how you defensibly claim "multi-agent" in the README.

---

## 4. The six Antigravity prompts (THE roadmap)

For each phase: **switch Antigravity to Planning Mode**, paste the prompt, **review the plan artifact and add comments before approving execution.** Do not let it run on Fast Mode. Planning artifacts are what the judges grade.

After each phase: commit to git (Antigravity can do this for you — just say "commit the changes with a descriptive message").

---

### PHASE 0 — Project scaffolding

```
We are building Challenge 2 of the AI Seekho 2026 Antigravity Hackathon: an
agentic AI system that orchestrates service requests for Pakistan's informal
economy (plumbers, electricians, AC technicians, tutors, beauticians).

Scaffold a clean monorepo with two top-level folders:

1. `backend/` — Python 3.11 project using FastAPI and the Google Agent
   Development Kit (ADK). It will host four agents (intent, discovery,
   ranking, action) and expose a single POST /request endpoint. Use
   `uv` or `pip` with a requirements.txt; whichever is simpler.
   IMPORTANT: the FastAPI server must bind to host="0.0.0.0" port=8000
   (NOT 127.0.0.1). This is required so that a real Android phone on
   the same WiFi can reach the backend. Default uvicorn behavior will
   not work for a real device.

2. `frontend/` — Flutter project (Android + web targets). Single chat
   screen for now; we'll flesh it out later.

3. `mock_data/` — folder for synthetic provider data and booking logs
   (JSON files, no database).

4. `trace/` — folder where every agent run writes a structured JSON log
   of its workplan, observations, reasoning, tool calls, decisions, and
   final outcome. This folder is the most important deliverable for the
   judges — design it for human readability.

5. `README.md` — placeholder with section headers we'll fill in later:
   Architecture, Data Schemas, Tools/APIs, Antigravity Role, Setup,
   Assumptions, Privacy, Cost & Latency, Scalability, Baseline
   Comparison, Limitations.

Use Gemini 3 Flash via the google-genai SDK for the agents (key will be
in .env — generate a .env.example).

Do NOT install or call any real third-party APIs (no Google Maps, no
Places, no Twilio). All external data must come from mock_data/.

Generate the plan artifact first and wait for my approval.
```

---

### PHASE 1 — Mock data + Intent Agent

```
Phase 1 of the build.

(a) MOCK DATA. Generate `mock_data/providers.json` with exactly 50
synthetic service providers across Islamabad and Rawalpindi. Distribution:
  - 5 categories: AC Technician, Plumber, Electrician, Tutor, Beautician
  - At least 8 sectors covered: G-13, G-11, F-10, F-11, I-8, I-10, Blue
    Area, DHA Phase 2 Rawalpindi (mix urban + suburban)
  - Each entry: id (P0001–P0050), name (plausibly Pakistani), category,
    sector, lat, lng (real coordinates for that sector), rating
    (1.0–5.0, skew realistic — mean ~4.2), rating_count, price_range
    (PKR), available_slots (next 7 days, 3–8 slots per provider),
    verified (boolean), languages_spoken (mix of Urdu/English/Punjabi),
    _synthetic: true (REQUIRED — judges check for this flag).
  - Include intentional realism: one provider with a 2.1 rating, one
    with 0 available slots in the next 24h, two with overlapping
    expertise, one whose name implies a service different from their
    actual category. The Ranking Agent needs to handle messy real-world
    data.

(b) INTENT AGENT. Build the first ADK agent: takes a free-form text
input in English, Urdu, OR Roman Urdu, and returns a structured JSON:
  {
    "service_type": "AC Technician" | "Plumber" | ...,
    "location_sector": "G-13" | null,
    "requested_time": ISO datetime | "tomorrow morning" | etc.,
    "urgency": "now" | "today" | "this_week" | "flexible",
    "constraints": {"gender_preference": ..., "budget_max_pkr": ...},
    "raw_input": "<original user text>",
    "detected_language": "english" | "urdu" | "roman_urdu",
    "confidence": 0.0–1.0,
    "needs_clarification": boolean,
    "clarification_question": "..." | null
  }

Use Gemini 3 Flash with a JSON-mode response. Prompt should give it 5
examples covering all three languages (e.g. "Mujhe kal subah G-13 mein
AC technician chahiye", "G-11 mein plumber chahiye abhi", "I need a
tutor for O-level math in F-10 this weekend", "بیوٹیشن چاہیے DHA میں",
"electrician F-11 jaldi").

(c) TRACE. Every Intent Agent invocation must write
trace/intent_<timestamp>.json with: input, prompt sent to LLM,
raw LLM response, parsed output, and a human-readable summary line.

(d) TESTS. Write 8 unit-test cases covering all three languages,
ambiguous inputs ("koi banda chahiye for tap fix"), and a deliberately
nonsense input ("xkcd flibble plumber").

Generate the plan artifact and wait for my approval before coding.
```

---

### PHASE 2 — Discovery Agent + Ranking Agent

```
Phase 2.

(a') GEO SERVICE ABSTRACTION. Before either agent, create
`backend/services/geo_service.py` with TWO functions:
  - get_distance_km(sector_a: str, sector_b: str) -> float
  - is_adjacent(sector_a: str, sector_b: str) -> bool
For v1, implement these against a hardcoded Python dict of Islamabad
sector coordinates and an adjacency map. Use a Haversine-formula helper
for distances. Both Discovery and Ranking agents MUST call this service
— do NOT compute distances inline. This is a clean abstraction layer
so we can swap to Google Maps Distance Matrix API in Phase 6.5 without
touching agent code.

(a) DISCOVERY AGENT. Given a parsed intent, query mock_data/providers.json
and return all providers that match `service_type` AND are in the
requested sector OR an adjacent sector (use geo_service.is_adjacent
from step a'). The adjacency map inside geo_service should encode
sensible Islamabad sector neighbors: G-13 ↔ G-11 ↔ F-11 ↔ F-10, etc.
  Output: a list of candidate provider dicts.
  Edge case: if zero candidates in requested sector, widen to all sectors
  within ~5km AND set fallback_used: true in the trace.
  Edge case: if still zero, return an empty list AND set
  no_candidates_reason: "..." for the next agent to handle.

(b) RANKING AGENT. CRITICAL — this is where the "agentic reasoning" score
is won or lost. Given a candidate list, the agent must use Gemini 3 Flash
to produce a ranked top-3 with a NATURAL-LANGUAGE JUSTIFICATION per
provider. Do NOT use a hard-coded weighted formula. The LLM is the ranker.
  The prompt should explain the user's full context (urgency, location,
  constraints) and ask the model to reason about tradeoffs. Example
  output:
  {
    "top_3": [
      {
        "provider_id": "P0042",
        "score": 0.91,
        "reasoning": "Ali AC Services is 2.1km away in the same sector,
          has the highest rating (4.7) among available providers, and
          has a slot at 10am tomorrow matching the user's 'kal subah'
          request. Slightly higher price than P0017 but the 3-year
          experience and 128 reviews justify it."
      },
      ...
    ],
    "rejected": [
      {"provider_id": "P0019", "reason": "Rating only 2.1, multiple
        recent low reviews — risky pick."},
      ...
    ]
  }

(c) TRACE. Write trace/ranking_<timestamp>.json with the prompt, the
candidate set, the LLM's full reasoning output, and the parsed result.

(d) Update the FastAPI route to chain Intent → Discovery → Ranking.
At this point, POST /request should return {intent, candidates, top_3}.

Plan artifact first, then approve.
```

---

### PHASE 3 — Action Agent + Follow-Up

```
Phase 3.

(a) ACTION AGENT. Given a selected provider (default: top-1 from ranking,
but the API should accept a user override), perform the BOOKING SIMULATION:

  1. Reserve a slot from the provider's available_slots in providers.json
     (remove that slot, mark the provider as having one fewer free slot).
  2. Append a new entry to mock_data/bookings.json with: booking_id,
     user_query, provider_id, scheduled_datetime, status: "confirmed",
     created_at, language_for_communication (matches detected_language
     from Intent), _synthetic: true.
  3. Generate a confirmation message IN THE SAME LANGUAGE the user wrote
     in (Urdu, Roman Urdu, or English — use the LLM for translation).
  4. Schedule a follow-up entry in mock_data/followups.json with: a
     reminder 1 hour before appointment, a post-job rating prompt 2
     hours after appointment.
  5. Generate a "booking receipt" as a small text artifact in
     trace/receipt_<booking_id>.txt.

(b) ROBUSTNESS — handle these edge cases explicitly:
  - Provider has no slots remaining → propose alternate slot from same
    provider OR escalate back to Ranking Agent for next-best provider.
  - Discovery returned zero candidates → the Action Agent must produce a
    graceful "no providers available right now, here's what we'd
    suggest" response in the user's language. This is your robustness
    evidence — make it visible in the trace.
  - Race condition: if two requests try to book the same slot, second
    one fails cleanly with a clear error.

(c) ORCHESTRATOR. Wrap all four agents in a top-level orchestrator that:
  - Writes a master trace/run_<timestamp>.json with the full workplan,
    each agent's contribution, and the final outcome.
  - Has a `--mode=agentic` (default) and `--mode=baseline` flag (we'll
    use baseline in Phase 5).

Plan first, approve, then build.
```

---

### PHASE 4 — Flutter mobile app

```
Phase 4 — build the Flutter UI that talks to the backend.

Pages:
1. Chat screen (single-screen app, no auth, no login):
   - Top: app bar "ServiceWala" (or whatever clean name fits)
   - Middle: scrollable list of message bubbles. User messages on right
     (blue), system messages on left (gray)
   - Bottom: text input + send button
   - When the user sends, show a "thinking…" indicator with sub-status:
     "Understanding…", "Finding providers…", "Choosing best match…",
     "Booking…" (mapped to the four agents — backend should stream
     status events via Server-Sent Events or just simulate this).

2. Reasoning panel (expandable card under each agent response):
   - Tap to expand and see the trace for that request
   - Show intent extraction → candidates → ranking reasoning → booking
     confirmation
   - This is what you'll show in the demo video; make it visually clean

3. Booking card (when a booking is confirmed):
   - Provider name, photo placeholder, scheduled time, confirmation
     number, "what happens next" (follow-up schedule preview)

UX rules:
- Roman Urdu / Urdu input must render correctly in the input field
- Confirmation messages render right-to-left if Urdu
- No real auth, no real payment, no real maps — but include a static
  Google Maps thumbnail mock (just an image with a pin) on the booking
  card for visual polish

Connect to backend via a configurable base URL. Set up
`frontend/lib/config.dart` with three constants and a runtime picker:
  - BASE_URL_WEB = "http://localhost:8000"
  - BASE_URL_EMULATOR = "http://10.0.2.2:8000"  // Android emulator's
    loopback alias to the host machine
  - BASE_URL_PHONE = "http://<YOUR_LAPTOP_LAN_IP>:8000"  // for a real
    phone on the same WiFi network

In api_service.dart, write a getBaseUrl() helper that picks the right
one at runtime: kIsWeb → web, Platform.isAndroid && isEmulator → emulator,
otherwise phone. (Use io.Platform; for "is emulator" detection use the
`device_info_plus` package — emulator returns isPhysicalDevice = false.)

The phone URL has a placeholder we'll fill in at demo time after running
`ipconfig` (Windows) / `ifconfig` (Mac/Linux) / `ip a` (Linux) to find
the laptop's LAN IP. Leave a clear TODO comment so it's easy to find.

Plan first.
```

---

### PHASE 5 — Baseline comparison + Robustness tests

```
Phase 5 — these are direct hackathon scoring items.

(a) BASELINE MODE. Add a `--mode=baseline` orchestrator path that does
the same job WITHOUT the LLM agents:
  - Intent: simple keyword matching ("AC" → AC Technician, "plumber" →
    Plumber, etc.). Picks first sector name found in input.
  - Discovery: same filter as before.
  - Ranking: hard-coded formula: score = (rating × 0.5) + (1 / distance
    × 0.3) + (has_slot ? 0.2 : 0). No reasoning text.
  - Action: same booking write, but confirmation message is a
    template in English only.

(b) BASELINE-VS-AGENTIC COMPARISON SCRIPT. Write
  `scripts/compare_modes.py` that runs both modes against these 10
  test queries and writes results to `comparison_report.md`:
  1. "Mujhe kal subah G-13 mein AC technician chahiye"  (Roman Urdu)
  2. "G-11 mein plumber chahiye abhi"  (Roman Urdu, urgent)
  3. "I need a math tutor in F-10 this weekend"  (English)
  4. "بیوٹیشن چاہیے ڈی ایچ اے میں"  (Urdu)
  5. "Koi banda chahiye for tap fix in I-8"  (Roman Urdu, ambiguous —
     should infer plumber)
  6. "Electrician F-99 abhi"  (invalid sector — fallback test)
  7. "Bahot urgent — AC band ho gaya hai, G-13"  (Roman Urdu, distress)
  8. "Tutor needed for O-level Physics, F-11, but no male tutors please"
     (constraint)
  9. "xkcd flibble plumber"  (nonsense)
 10. "Plumber chahiye G-13 — budget under 2000 PKR"  (budget constraint)

The script should show, for each query, both outputs side-by-side and
flag where they differ. The expected outcomes:
  - Baseline fails on #1, #2, #4, #5 (no Roman Urdu / Urdu / ambiguous
    handling)
  - Baseline picks lower-rated providers in some cases (no nuance)
  - Baseline cannot handle #6, #8, #9 gracefully
The README will reference this report.

(c) ROBUSTNESS LOG. Run the agentic mode against queries #6, #9, #10
specifically and confirm trace files show: error detection, fallback
reasoning, graceful failure. Take screenshots — these become your
"robustness evidence" deliverable.

Plan first.
```

---

### PHASE 6 — Documentation, demo prep, final polish

```
Phase 6 — make it submittable.

(a) FILL THE README. Use this exact structure (the submission checklist
demands every one of these):
  1. Project Overview (2 paragraphs, plain English)
  2. Architecture (insert the ASCII or mermaid diagram I'll paste in;
     describe the four-agent flow)
  3. Data Schemas (paste the providers.json and bookings.json schemas)
  4. Tools / APIs Used (FastAPI, Google ADK, Gemini 3 Flash via
     google-genai, Flutter. List Antigravity as our development
     platform — judges grade this!)
  5. The Role of Antigravity (DO NOT skim this — judges weight it 25%):
     - "We used Antigravity in Planning Mode for all six build phases."
     - "Antigravity generated the implementation plan as an artifact
       for each phase, which we reviewed and commented on before
       approving execution."
     - "Antigravity's Agent Manager spawned parallel agents to scaffold
       the backend and frontend simultaneously."
     - "Antigravity's built-in browser was used to verify the Flutter
       web build during development, producing screenshot artifacts
       which are included in submission/antigravity_artifacts/."
     - "All terminal commands, file edits, and verifications were
       orchestrated through Antigravity; we never left the IDE."
  6. Setup Instructions (clone, .env, `pip install -r requirements.txt`,
     `uvicorn main:app`, `flutter run`)
  7. Assumptions (all data synthetic; no real bookings; latency
     measured locally; etc.)
  8. Privacy Note (no real personal data; mock provider names are
     fictional; no real phone numbers, addresses, or payment info)
  9. Cost & Latency Analysis:
     - Per-request: ~3-4 Gemini 3 Flash calls × ~$0.0001 each ≈
       $0.0004 per service request
     - Latency: typically 2-4 seconds end-to-end on Wi-Fi
     - 100 requests ≈ $0.04. 10,000 requests ≈ $4.
 10. Scalability (10x and 100x):
     - 10x scale: same architecture, no changes needed; provider DB
       in JSON works to ~1000 entries; ADK is stateless so horizontal
       scale is trivial
     - 100x scale: migrate provider data to Postgres + PostGIS for
       geo queries; add Redis cache for intent embeddings; consider
       fine-tuning a smaller model for intent classification to cut
       cost by ~80%
 11. Baseline Comparison (link to comparison_report.md and summarize
     the win rate)
 12. Limitations (no real-time provider availability; mock geocoding;
     no payment integration; trust signals are synthetic)

(b) EXPORT THE ARTIFACTS. Inside Antigravity: File > Export Artifacts
for each phase. Save them to submission/antigravity_artifacts/phaseN/.
These are the workplans, task plans, and screenshots. They prove use
of Antigravity.

(c) DEMO VIDEO PREP. Write `submission/demo_script.md` with the
exact narration for a 4-minute demo (script provided separately by
the user; ask if needed).

(d) FINAL CHECK. Run `scripts/compare_modes.py` one more time and
confirm comparison_report.md is current. Run the agentic flow against
all 10 test queries and confirm every trace file is well-formed.

Plan first, then execute.
```

---

### PHASE 6.5 — (OPTIONAL) Google Maps integration as stretch goal

> Do this ONLY if you have ≥4 hours left after Phase 6 and everything
> in the main build works end-to-end. Do NOT start this if it might
> destabilize a working submission.

```
Phase 6.5 — OPTIONAL stretch goal. Wire up real Google Maps APIs in
place of mock geo logic.

Prerequisite I will provide BEFORE you start:
  - A GOOGLE_MAPS_API_KEY in .env (the user will get this from Google
    Cloud Console with billing enabled and Places API + Distance Matrix
    API + Geocoding API enabled).
  - If the key is not provided yet, STOP and ask. Do not proceed.

What to do:

(a) In `backend/services/geo_service.py`, add a `RealGeoService`
implementation that uses the Google Maps Distance Matrix API for
get_distance_km() and a hardcoded sector centroid map + reverse
geocoding for is_adjacent(). Keep the mock implementation as
`MockGeoService`. Use a feature flag in config (GEO_PROVIDER=mock|real,
default=mock) to pick at startup.

(b) In the Discovery Agent, add an optional second step: after filtering
by sector, optionally enrich each candidate with a real Places API
lookup (search "Ali AC Services near G-13 Islamabad") to verify the
provider exists. Cache results in mock_data/places_cache.json so we
don't pay for the same query twice. Tag enriched providers with
"places_verified": true in the candidate output — the Ranking Agent
should mention this in its reasoning when present.

(c) In the Flutter booking card, replace the static Google Maps
thumbnail image with the actual google_maps_flutter widget showing the
provider's pin. Use a free tier API key (do NOT commit it to git;
inject via --dart-define at build time).

(d) Update the README cost section: with real Maps, each request now
costs ~$0.005 (intent + ranking + 1 distance call + 1 places lookup).
At 100x scale this becomes meaningful and the cache becomes critical.

(e) IMPORTANT: in the demo video, still show the mock-mode flow as the
primary demo. Only show real-Maps mode for the "innovation & UX"
section so a network outage at demo time doesn't kill the whole thing.

Plan first.
```

---

## 5. How to actually work with Antigravity (key instructions for YOU)

These are habits that protect the project from going sideways.

### Always use Planning Mode for these six phases.
Fast Mode is for typos and one-liners. Each of the six prompts above is multi-file, multi-component work — Planning Mode produces the artifacts the judges will literally grade. Toggle is at the bottom of the chat input.

### Read the plan artifact before approving.
When you paste a phase prompt, Antigravity will generate a plan artifact (a structured document showing what it intends to do, file by file). **Read it.** If something looks off — wrong library, wrong file path, missing edge case — **comment on that line directly** (highlight, click comment, Google-Docs style). The agent reads your comments and adjusts before writing any code. Iterating on a plan is 100x cheaper than fixing built code.

### Pick the strongest coding model available in Antigravity.
Open the model selector (near the chat input). **Claude Opus 4.6** is currently the strongest coding model offered; pick that. If unavailable, fall back to **Gemini 3 Pro**. This is the model Antigravity uses to write your code — totally separate from the **Gemini 3 Flash** your runtime agents will call from the backend. Don't conflate the two. The hackathon rule mandates the *platform* (Antigravity), not the *model inside it*; any of the supported models is fine.

### Run one phase at a time. Do not paste multiple phases in one prompt.
The single most common mistake is asking for too much at once. Each phase above is sized to fit comfortably in one planning cycle. Stick to one. Commit after each. Move on.

### When something breaks, ask Antigravity to debug it.
"The Intent Agent is returning null for Urdu input — read the trace file at trace/intent_xxx.json and figure out why." Don't try to read code yourself. Make the agent explain itself.

### Use Antigravity's built-in browser for the demo recording.
For the 2-3 min "how we used Antigravity" video, just screen-record Antigravity itself: show the Agent Manager, show a plan artifact, show the agent executing a task, show the built-in browser previewing the Flutter app. That video writes itself.

### Save artifacts proactively.
After each phase finishes, manually export the plan artifact and screenshots to `submission/antigravity_artifacts/phaseN/`. Don't wait until the end — Antigravity's history can get cluttered.

### Don't fight the agent on architecture.
If Antigravity suggests a slightly different file structure than I've outlined, and its reasoning is good — let it. The exact folder names don't matter. What matters is that the four agents are real, the trace files exist, and the baseline comparison works.

---

## 6. Submission checklist → where each item lives in this plan

| Required item | Comes from |
|---|---|
| Working mobile prototype | Phase 4 (Flutter app) |
| Demo video 3–5 min showing agentic flow end-to-end | Phase 6 (script) + record after Phase 5 |
| Demo video 2–3 min showing use of Antigravity | Screen-record Antigravity during any phase |
| Antigravity trace/logs (workplan, observations, reasoning, tool calls, outcomes) | All phases — `trace/` folder + exported Antigravity artifacts |
| README documentation | Phase 6, section (a) |
| Baseline comparison | Phase 5, comparison_report.md |
| Robustness evidence | Phase 5, robustness section + Phase 3 edge cases |
| Cost and scalability note | Phase 6, README sections 9 and 10 |
| Working prototype shows observe → reason → decide → act → evaluate → adapt | This is the entire agentic flow — Phases 1–3 |
| Mock data clearly labeled synthetic | `_synthetic: true` flag in every record (Phase 1) |
| No personal/sensitive data | Phase 1 mock generation — all names fictional |
| Reliable end-to-end workflow > broad but shallow | Plan deliberately keeps scope at 5 service types, 8 sectors |

---

## 7. Demo video script outline (4 minutes — record this AFTER Phase 5)

**0:00–0:20 — Hook.** "This is ServiceWala — an agentic AI system for Pakistan's informal economy. Watch what happens when I send it a request in Roman Urdu."

**0:20–0:50 — Live demo: happy path.** Type `Mujhe kal subah G-13 mein AC technician chahiye`. Show the four-stage "thinking" indicator. Show the booked confirmation. Show the booking card with provider, time, follow-up schedule.

**0:50–1:50 — Open the reasoning panel.** "But the booking isn't the interesting part. *This* is." Expand the trace. Walk through:
- Intent Agent's extraction (highlight: detected Roman Urdu, parsed "kal subah" as tomorrow morning)
- Discovery Agent's candidates (mention sector adjacency fallback if relevant)
- Ranking Agent's natural-language reasoning ("notice it didn't just pick the closest — it weighed rating against price")
- Action Agent's confirmation in the user's original language

**1:50–2:30 — Edge case.** Type `xkcd flibble plumber`. Show the system gracefully detecting nonsense, asking a clarification, NOT crashing.

**2:30–3:10 — Baseline comparison.** Pull up `comparison_report.md` on screen. Walk through one row: same input, baseline picks worse provider OR fails entirely on Roman Urdu, agentic picks correctly. "This is why agentic reasoning matters — not because it's fancy, but because the simple heuristic fails the moment the input doesn't fit a pattern."

**3:10–3:50 — Antigravity role.** "Every line of this code was orchestrated through Google Antigravity in Planning Mode. Here's the plan artifact for Phase 3." Quick scroll. "Antigravity didn't just write code — it planned, executed, verified, and produced auditable artifacts at every step."

**3:50–4:00 — Close.** "Mock data, local backend, four real agents, full trace. Thank you."

---

## 8. Pitfalls that will tank your score

1. **Hard-coding the ranking logic.** If your Ranking Agent has `score = rating * 0.5 + ...`, you've failed the "agentic reasoning" criterion. The LLM must produce the reasoning text. The heuristic version goes in the baseline, not the main system.

2. **Letting Antigravity use Fast Mode.** No plan artifacts → no proof of agentic workflow → 25% of your score evaporates.

3. **A pretty UI with a dumb backend.** The judges explicitly say "focus on agentic automation, not UI complexity." Spend 70% of your effort on the agents and traces, 30% on Flutter.

4. **Forgetting `_synthetic: true`.** The rules ask for clearly-labeled mock data. One missing flag, judges raise an eyebrow.

5. **No edge case handling.** If every demo query is the happy path, you'll lose the robustness points. Phase 3 + Phase 5 specifically force this — don't skip them.

6. **Submitting without the Antigravity artifacts folder.** The trace logs from Antigravity itself (plans, screenshots, walkthroughs) are a required deliverable. Export them after every phase.

7. **A baseline that's barely worse than agentic.** Make the baseline genuinely dumb. Keyword matching only. English only. Hard-coded weights. The contrast is the point.

8. **Trying to deploy to the cloud.** You don't have time. Everything runs on your laptop during the demo. That's fine and normal for a hackathon.

---

## 9. Quick-start sequence (literally what to do right now)

1. Install Antigravity (antigravity.google → download for your OS).
2. Sign in with personal Gmail. Choose Gemini 3 Pro as the model. Choose "Review-driven development" or "Agent-assisted development" — NOT autopilot.
3. Open a new folder named `service-wala` somewhere on your laptop.
4. Open it in Antigravity.
5. Switch the agent panel to **Planning Mode**.
6. Paste **Phase 0** from this document. Read the plan artifact. Comment if anything's off. Approve.
7. Once Phase 0 is done, commit (`Antigravity, commit the changes with message "Phase 0: scaffolding"`).
8. Paste **Phase 1**. Repeat.
9. Keep going. One phase at a time. Don't skip the review step.

**One housekeeping task before Phase 4:** find your laptop's LAN IP, because the Flutter app on your real phone needs it. Open a terminal and run:
- Windows: `ipconfig` → look for "IPv4 Address" under your active WiFi adapter (usually `192.168.x.x`)
- Mac: `ipconfig getifaddr en0` (or `en1` if you're on WiFi via a different interface)
- Linux: `ip a` → look for the `inet` line under your WiFi adapter

Copy that IP into `BASE_URL_PHONE` in `frontend/lib/config.dart`. It only changes if you switch WiFi networks. Don't commit it to git — leave the placeholder there.

You're the project manager. Antigravity is the senior engineer. Your job is to read plans, ask questions, approve work, and own the final submission. You don't need to write code. You do need to read what gets built and make sure it matches the plan.

Good luck. The roadmap is here for a reason — when you feel lost, come back to it.
