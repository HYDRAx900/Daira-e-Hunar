"""
Intent Agent test suite — 8 test cases covering:
  - English, Roman Urdu, and Urdu script inputs
  - Ambiguous/inferred inputs
  - Nonsense input
  - Missing location

Each test makes a real Gemini API call to validate prompt quality
and JSON-mode schema compliance. No mocking.
"""

import os
import time
import pytest
from pathlib import Path

from backend.agents.intent_agent import IntentAgent

# All required keys in the intent output
REQUIRED_KEYS = {
    "service_type",
    "location_sector",
    "requested_time",
    "urgency",
    "constraints",
    "raw_input",
    "detected_language",
    "confidence",
    "needs_clarification",
    "clarification_question",
    "formality_level",
    "literacy_register",
    "code_switching",
}


@pytest.fixture(scope="module")
def agent():
    """Shared IntentAgent instance for all tests in this module."""
    return IntentAgent()


@pytest.fixture(autouse=True)
def rate_limit_delay():
    """
    Pause between tests to respect Gemini free-tier rate limit
    (5 requests/minute for gemini-2.5-flash).
    """
    yield
    time.sleep(13)



def _assert_valid_structure(result: dict, original_input: str):
    """Common structural assertions for every test."""
    # All required keys present (minus _trace_file which is internal)
    result_keys = {k for k in result.keys() if not k.startswith("_")}
    assert REQUIRED_KEYS.issubset(result_keys), (
        f"Missing keys: {REQUIRED_KEYS - result_keys}"
    )

    # raw_input echoes the original
    assert result["raw_input"] == original_input

    # confidence is a float in [0, 1]
    assert 0.0 <= result["confidence"] <= 1.0

    # urgency is one of the valid values
    assert result["urgency"] in ("now", "today", "this_week", "flexible")

    # detected_language is valid
    assert result["detected_language"] in ("english", "urdu", "roman_urdu")

    # Trace file was created
    trace_path = result.get("_trace_file")
    assert trace_path is not None, "Trace file path should be set"
    full_path = Path(os.getcwd()) / trace_path
    assert full_path.exists(), f"Trace file not found: {full_path}"


# ── Test 1: Clear English input ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_english_clear(agent):
    """Full English request with service, location, and time."""
    text = "I need a tutor for O-level math in F-10 this weekend"
    result = await agent.run(text)

    _assert_valid_structure(result, text)
    assert result["service_type"] == "Tutor"
    assert result["location_sector"] == "F-10, Islamabad"
    assert result["urgency"] in ("this_week", "today")
    assert result["confidence"] >= 0.7
    assert result["detected_language"] == "english"
    assert result["formality_level"] == "formal"
    assert result["code_switching"] is False


# ── Test 2: Clear Roman Urdu input ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_roman_urdu_clear(agent):
    """Roman Urdu with all fields explicit."""
    text = "Mujhe kal subah G-13 mein AC technician chahiye"
    result = await agent.run(text)

    _assert_valid_structure(result, text)
    assert result["service_type"] == "AC Technician"
    assert result["location_sector"] == "G-13, Islamabad"
    assert result["detected_language"] == "roman_urdu"
    assert result["confidence"] >= 0.7


# ── Test 3: Roman Urdu urgent ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_roman_urdu_urgent(agent):
    """Roman Urdu with 'abhi' indicating urgency."""
    text = "G-11 mein plumber chahiye abhi"
    result = await agent.run(text)

    _assert_valid_structure(result, text)
    assert result["service_type"] == "Plumber"
    assert result["location_sector"] == "G-11, Islamabad"
    assert result["urgency"] == "now"


# ── Test 4: Urdu script ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_urdu_script(agent):
    """Urdu script input."""
    text = "بیوٹیشن چاہیے DHA میں"
    result = await agent.run(text)

    _assert_valid_structure(result, text)
    assert result["service_type"] == "Beautician"
    assert result["detected_language"] == "urdu"
    assert result["formality_level"] in ("casual", "formal")
    assert result["literacy_register"] in ("medium", "high")


# ── Test 5: Terse Roman Urdu ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_roman_urdu_terse(agent):
    """Very short Roman Urdu with implied urgency."""
    text = "electrician F-11 jaldi"
    result = await agent.run(text)

    _assert_valid_structure(result, text)
    assert result["service_type"] == "Electrician"
    assert result["location_sector"] == "F-11, Islamabad"
    assert result["urgency"] in ("now", "today")


# ── Test 6: Ambiguous input ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ambiguous_input(agent):
    """Ambiguous — 'tap fix' implies Plumber but isn't explicit."""
    text = "koi banda chahiye for tap fix"
    result = await agent.run(text)

    _assert_valid_structure(result, text)
    # Should infer Plumber from context
    assert result["service_type"] == "Plumber"
    # Confidence should be lower due to inference
    assert result["confidence"] < 0.9
    # Location and time are missing → needs clarification
    assert result["needs_clarification"] is True


# ── Test 7: Nonsense input ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_nonsense_input(agent):
    """Deliberate nonsense — agent should flag low confidence."""
    text = "xkcd flibble plumber"
    result = await agent.run(text)

    _assert_valid_structure(result, text)
    assert result["needs_clarification"] is True
    assert result["confidence"] < 0.5


# ── Test 8: No location ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_location(agent):
    """Valid service request but no location specified."""
    text = "I need an electrician urgently"
    result = await agent.run(text)

    _assert_valid_structure(result, text)
    assert result["service_type"] == "Electrician"
    assert result["location_sector"] is None
    assert result["urgency"] in ("now", "today")
    assert result["needs_clarification"] is True


# ── Test 9: Casual slang ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_formality_casual_slang(agent):
    """Casual/slang Roman Urdu request."""
    text = "AC bana de bhai G-13 mein kal subah"
    result = await agent.run(text)

    _assert_valid_structure(result, text)
    assert result["formality_level"] in ("slang", "casual")


# ── Test 10: Code-switching ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_code_switching(agent):
    """Input mixing English and Roman Urdu."""
    text = "Mujhe ek good plumber chahiye urgent F-10 mein"
    result = await agent.run(text)

    _assert_valid_structure(result, text)
    assert result["code_switching"] is True
