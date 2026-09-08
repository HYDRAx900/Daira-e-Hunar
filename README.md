# Daira-e-Hunar (دائرۃ ہنر) — AI Service Orchestrator for Pakistan's Informal Economy

> *Har shehr ka apna daira, har banday ka apna hunar.*
> (Every city its own circle, every person their own skill.)

An agentic AI system that lets someone find and book a plumber, electrician, tutor, or AC technician by typing the way they actually talk — in English, Urdu script, or Roman Urdu — and get an answer back in that same language and register.

```
User:   "AC bana de yaar Lahore mein, jaldi"
System: "Lahore mein abhi 3 AC technician available hain. Sab se qareeb
         Misri Shah mein hai — 20 minute mein pohnch sakta hai."
```

No app to learn, no form to fill, no English required.

---

## Why

Pakistan's informal service economy runs on WhatsApp messages, phone calls, and word of mouth — tens of millions of skilled workers who are invisible to formal digital infrastructure. The barrier usually isn't skill or demand. It's that existing platforms assume a literate, English-comfortable user filling out structured forms.

Daira-e-Hunar treats language diversity as the interface rather than a problem to flatten. A user writing casual Roman Urdu gets casual Roman Urdu back. A user writing formal Urdu gets formal Urdu back. That mirroring is the core design principle, not decoration.

## How it works

Four LLM-powered agents in an end-to-end pipeline, wrapped by an orchestrator that short-circuits gracefully at any stage.

**Intent Agent** — parses free-form multilingual input into a typed schema (service type, location, timing, urgency, constraints), while separately extracting formality level, literacy register, and code-switching signals. Pydantic response schemas with JSON-mode enforcement.

**Discovery Agent** — deterministic filtering across 100 synthetic providers in 8 Pakistani cities, with coordinates placed in real working-class neighbourhoods. When no provider matches the requested city and category, it broadens the search nationwide and sets a `fallback_used` flag rather than failing silently.

**Ranking Agent** — the centrepiece. Ranks candidates through natural-language reasoning rather than a weighted formula, producing a short justification per provider in the user's own language and register. Reads provider bios as human signal instead of scoring ratings alone, flags bio-versus-category mismatches, and reconciles conflicts between requested time and stated urgency.

**Action Agent** — simulates end-to-end booking: atomic slot reservation via `.tmp` + `os.replace`, race-condition detection by re-read-and-verify, an append-only bookings ledger, two scheduled follow-ups, and a tone-mirrored confirmation message with hardcoded templates in all three registers so confirmations never depend on API quota.

## Design decisions worth naming

**Honest refusal over a scripted happy path.** The demo query hit a real supply constraint — no morning AC technician in G-13 Islamabad. The easy fix was editing the provider data to force a match. Instead the system tells the user, in their own language, that nobody is available. A system that misrepresents its own capabilities doesn't deserve to be trusted with anything real.

**Hardcoded confirmations.** Early testing showed confirmations returning in English regardless of input language. Rather than chase an LLM prompting bug, confirmations became three fixed templates. More reliable, more culturally consistent, no quota dependency.

**Tightened test assertions.** Generated tests checked for common Roman Urdu tokens like `hai`, `ka`, `wala`. But `ka` matches inside *package* and *Karachi* — so a broken language-mirroring feature would still pass. Assertions now require at least three distinct whole-word matches via `\b` boundaries.

**No cultural cosplay.** Explicit anti-patterns: no glassmorphism, no token Urdu sprinkled into an English UI, no flag colours, no performative empathy. Urdu typography carries the cultural weight instead.

## Stack

- Python 3.12, FastAPI
- Gemini 2.5 Flash via the `google-genai` SDK for runtime reasoning
- Pydantic response schemas
- Custom Haversine module in pure stdlib, abstracted so a real distance API can swap in without touching agent code
- Frontend prototype in Claude Design

Built in a review-driven agentic workflow in Google Antigravity, with Claude as the selected model. Every phase followed the same protocol: write a detailed prompt, review the generated implementation plan against four clauses — state change, reversibility, provenance, plan consistency — comment inline, then approve execution. The human role is architect and reviewer rather than typist.

## Status

The backend pipeline is complete end-to-end — Intent through Action — with reviewable JSON traces at every stage plus a top-level `run_<timestamp>.json` orchestrator trace.

Not yet built: the frontend prototype, and a non-agentic keyword-matching baseline intended for A/B comparison. Three of five Ranking Agent tests are verified passing; the remaining two are robustness checks that were blocked by the Gemini free-tier daily quota.

Built solo on the backend over roughly five days, with a teammate on UI design, for the AI Seekho Antigravity Hackathon.

## Data and privacy

All provider data is synthetic and flagged `_synthetic: true`. Names are realistic and regional, and coordinates point at genuine working-class neighbourhoods — but no real person's identity is used. Informal workers are precisely the population least able to consent to having their data in someone's hackathon project.

## Running it

```bash
# TODO: fill in your actual commands
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
uvicorn main:app --host 0.0.0.0 --port 8000
```

The server binds to `0.0.0.0` so it can be reached from a phone on the same network for demo purposes.
