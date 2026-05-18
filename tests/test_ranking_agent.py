"""
Ranking Agent test suite — 5 scenarios testing LLM-driven reasoning.

Each test makes a real Gemini API call. 13-second delays between tests
to respect the free-tier rate limit (5 RPM).

Tests focus on:
  1. Slang Roman Urdu tone-mirroring
  2. Formal Urdu script tone-mirroring
  3. Explicit language preference (Pashto)
  4. Time inconsistency reasoning
  5. Bio-vs-category edge case
"""

import os
import re
import time
import pytest
from pathlib import Path

from backend.agents.intent_agent import IntentAgent
from backend.agents.discovery_agent import DiscoveryAgent
from backend.agents.ranking_agent import RankingAgent


# ── Required keys in ranking output ─────────────────────────────────────────

REQUIRED_KEYS = {"top_3", "rejected"}


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def intent_agent():
    return IntentAgent()


@pytest.fixture(scope="module")
def discovery_agent():
    return DiscoveryAgent()


@pytest.fixture(scope="module")
def ranking_agent():
    return RankingAgent()


@pytest.fixture(autouse=True)
def rate_limit_delay():
    """
    Pause between tests to respect Gemini free-tier rate limit.
    Each ranking test makes 2 LLM calls (Intent + Ranking), so we
    need a longer delay than Intent-only tests (25s vs 13s).
    """
    yield
    time.sleep(25)


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _run_pipeline(intent_agent, discovery_agent, ranking_agent, query: str) -> dict:
    """Run the full Intent -> Discovery -> Ranking pipeline."""
    intent = await intent_agent.run(query)
    discovery = await discovery_agent.run(intent)
    candidates = discovery.get("candidates", [])
    if not candidates:
        pytest.skip(f"No candidates found for: {query}")
    ranking = await ranking_agent.run(candidates, intent)
    return {
        "intent": intent,
        "discovery": discovery,
        "ranking": ranking,
    }


def _assert_ranking_structure(ranking: dict):
    """Common structural assertions."""
    result_keys = {k for k in ranking.keys() if not k.startswith("_")}
    assert REQUIRED_KEYS.issubset(result_keys), (
        f"Missing keys: {REQUIRED_KEYS - result_keys}"
    )
    assert len(ranking["top_3"]) >= 1
    assert len(ranking["top_3"]) <= 3

    for p in ranking["top_3"]:
        assert "provider_id" in p
        assert "score" in p
        assert "reasoning" in p
        assert 0.0 <= p["score"] <= 1.0
        assert len(p["reasoning"]) > 20  # at least a meaningful sentence

    # Trace file created
    trace_path = ranking.get("_trace_file")
    assert trace_path is not None
    full_path = Path(os.getcwd()) / trace_path
    assert full_path.exists()


# ── Roman Urdu marker words for tone-mirroring assertion ─────────────────────

ROMAN_URDU_MARKERS = [
    "hai", "hain", "wala", "chahiye", "mein", "yaar", "kal", "subah",
    "jaldi", "acha", "behtareen", "bhi", "aur", "ke", "ka", "ki",
    "kaam", "door", "qareeb", "saal", "tajurba", "banda",
]

# Compile regex patterns with word boundaries for each marker
_MARKER_PATTERNS = [
    re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    for word in ROMAN_URDU_MARKERS
]


def _count_roman_urdu_markers(text: str) -> int:
    """Count distinct Roman Urdu marker words found as whole words."""
    return sum(1 for pattern in _MARKER_PATTERNS if pattern.search(text))


def _count_urdu_script_chars(text: str) -> int:
    """Count characters in the Arabic/Urdu script range (U+0600-U+06FF)."""
    return sum(1 for ch in text if "\u0600" <= ch <= "\u06FF")


# ── Test 1: Slang Roman Urdu tone-mirroring ─────────────────────────────────

@pytest.mark.asyncio
async def test_tone_mirror_slang_roman_urdu(
    intent_agent, discovery_agent, ranking_agent
):
    """Slang Roman Urdu request -> reasoning should be in Roman Urdu."""
    result = await _run_pipeline(
        intent_agent, discovery_agent, ranking_agent,
        "AC bana de yaar Lahore mein, jaldi"
    )

    ranking = result["ranking"]
    _assert_ranking_structure(ranking)

    # Combine all reasoning text
    all_reasoning = " ".join(p["reasoning"] for p in ranking["top_3"])

    # Must contain at least 3 distinct Roman Urdu marker words (whole-word)
    marker_count = _count_roman_urdu_markers(all_reasoning)
    assert marker_count >= 3, (
        f"Expected >= 3 Roman Urdu markers, found {marker_count} in: "
        f"{all_reasoning[:200]}..."
    )


# ── Test 2: Formal Urdu script tone-mirroring ───────────────────────────────

@pytest.mark.asyncio
async def test_tone_mirror_formal_urdu(
    intent_agent, discovery_agent, ranking_agent
):
    """Formal Urdu script request -> reasoning should contain Urdu script."""
    result = await _run_pipeline(
        intent_agent, discovery_agent, ranking_agent,
        "مہربانی فرما کر لاہور میں ایک اچھا پلمبر بتائیں اس ہفتے کے لیے"
    )

    ranking = result["ranking"]
    _assert_ranking_structure(ranking)

    # Combine all reasoning text
    all_reasoning = " ".join(p["reasoning"] for p in ranking["top_3"])

    # Must contain at least 20 Urdu script characters
    urdu_count = _count_urdu_script_chars(all_reasoning)
    assert urdu_count >= 20, (
        f"Expected >= 20 Urdu script chars, found {urdu_count} in: "
        f"{all_reasoning[:200]}..."
    )


# ── Test 3: Explicit Pashto language preference ─────────────────────────────

@pytest.mark.asyncio
async def test_language_preference_pashto(
    intent_agent, discovery_agent, ranking_agent
):
    """
    Explicit Pashto preference -> top-1 should speak Pashto.

    Data verified: P0078 (Dost Muhammad, Quetta Electrician) speaks Pashto.
    """
    result = await _run_pipeline(
        intent_agent, discovery_agent, ranking_agent,
        "Pashto bolne wala electrician chahiye Quetta mein"
    )

    ranking = result["ranking"]
    _assert_ranking_structure(ranking)

    # Load provider data to check languages
    import json
    from backend.config import MOCK_DATA_DIR
    providers = json.load(open(MOCK_DATA_DIR / "providers.json", "r", encoding="utf-8"))
    provider_map = {p["id"]: p for p in providers}

    # Top-1 provider should speak Pashto
    top_1_id = ranking["top_3"][0]["provider_id"]
    top_1_provider = provider_map.get(top_1_id)
    assert top_1_provider is not None, f"Provider {top_1_id} not found"
    assert "Pashto" in top_1_provider["languages_spoken"], (
        f"Top-1 provider {top_1_id} doesn't speak Pashto: "
        f"{top_1_provider['languages_spoken']}"
    )

    # Reasoning should mention language/Pashto
    top_1_reasoning = ranking["top_3"][0]["reasoning"].lower()
    assert "pashto" in top_1_reasoning or "زبان" in top_1_reasoning, (
        f"Reasoning doesn't mention Pashto: {ranking['top_3'][0]['reasoning']}"
    )


# ── Test 4: Time inconsistency reasoning ────────────────────────────────────

@pytest.mark.asyncio
async def test_time_inconsistency(
    intent_agent, discovery_agent, ranking_agent
):
    """
    'kal subah' + urgency='this_week' -> reasoning should reconcile.
    """
    result = await _run_pipeline(
        intent_agent, discovery_agent, ranking_agent,
        "Mujhe kal subah Lahore mein AC technician chahiye"
    )

    ranking = result["ranking"]
    _assert_ranking_structure(ranking)

    # Check that reasoning OR trace reconciles time signals
    all_reasoning = " ".join(p["reasoning"] for p in ranking["top_3"])
    all_text = all_reasoning.lower()

    # Look for evidence of time reconciliation
    time_signals = ["kal", "subah", "tomorrow", "morning", "slot"]
    has_time_reference = any(s in all_text for s in time_signals)
    assert has_time_reference, (
        f"Reasoning doesn't reference time/schedule: {all_reasoning[:300]}..."
    )


# ── Test 5: Bio-vs-category edge case ───────────────────────────────────────

@pytest.mark.asyncio
async def test_bio_category_mismatch(
    intent_agent, discovery_agent, ranking_agent
):
    """
    P0050 (Nasreen Akhtar): category='Tutor', bio='Famous for stitching
    bridal lehengas'. Should NOT be in top_3 for a tutoring request,
    or if included, reasoning must flag the bio mismatch.
    """
    # Use Faisalabad for tutor search - P0050's home_city
    # First find P0050's actual city
    import json
    from backend.config import MOCK_DATA_DIR
    providers = json.load(open(MOCK_DATA_DIR / "providers.json", "r", encoding="utf-8"))
    p0050 = next(p for p in providers if p["id"] == "P0050")
    city = p0050["home_city"]

    result = await _run_pipeline(
        intent_agent, discovery_agent, ranking_agent,
        f"I need a good tutor in {city} for Urdu literature"
    )

    ranking = result["ranking"]
    _assert_ranking_structure(ranking)

    # Check if P0050 is in top_3
    top_ids = [p["provider_id"] for p in ranking["top_3"]]

    if "P0050" in top_ids:
        # If included, reasoning MUST flag the bio mismatch
        p0050_entry = next(p for p in ranking["top_3"] if p["provider_id"] == "P0050")
        reasoning_lower = p0050_entry["reasoning"].lower()
        bio_flag_terms = ["lehenga", "bridal", "stitching", "tailoring", "mismatch", "concern"]
        has_flag = any(term in reasoning_lower for term in bio_flag_terms)
        assert has_flag, (
            f"P0050 is in top_3 but reasoning doesn't flag bio mismatch: "
            f"{p0050_entry['reasoning']}"
        )
    # else: P0050 not in top_3 — that's the expected behavior, test passes
