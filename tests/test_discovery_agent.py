"""
Discovery Agent tests — deterministic, no LLM calls, no rate limit delays.

Tests filtering, fallback logic, and trace file creation.
"""

import os
import pytest
from pathlib import Path

from backend.agents.discovery_agent import DiscoveryAgent


@pytest.fixture(scope="module")
def agent():
    """Shared DiscoveryAgent instance."""
    return DiscoveryAgent()


# ── Test 1: Happy path — AC Technicians in Lahore ───────────────────────────

@pytest.mark.asyncio
async def test_happy_path_lahore_ac(agent):
    """AC Technician in Lahore → should find candidates, no fallback."""
    intent = {
        "service_type": "AC Technician",
        "location_sector": "Misri Shah, Lahore",
        "home_city": "Lahore",
        "raw_input": "AC technician chahiye Lahore mein",
    }
    result = await agent.run(intent)

    assert result["total_found"] > 0
    assert result["fallback_used"] is False
    assert result["no_candidates_reason"] is None
    assert result["city_searched"] == "Lahore"

    # All returned candidates should be Lahore AC Technicians
    for c in result["candidates"]:
        assert c["home_city"] == "Lahore"
        assert c["category"] == "AC Technician"

    # Trace file created
    assert result.get("_trace_file") is not None
    trace_path = Path(os.getcwd()) / result["_trace_file"]
    assert trace_path.exists()


# ── Test 2: Fallback — Tutor in Islamabad (zero in-city) ────────────────────

@pytest.mark.asyncio
async def test_fallback_tutor_islamabad(agent):
    """Tutor in Islamabad → zero in-city → fallback nationwide."""
    intent = {
        "service_type": "Tutor",
        "location_sector": "G-7, Islamabad",
        "home_city": "Islamabad",
        "raw_input": "Tutor chahiye G-7 mein",
    }
    result = await agent.run(intent)

    assert result["fallback_used"] is True
    assert result["fallback_reason"] is not None
    assert "Islamabad" in result["fallback_reason"]
    assert result["total_found"] > 0  # nationwide tutors exist
    assert result["no_candidates_reason"] is None


# ── Test 3: No service_type → empty result ──────────────────────────────────

@pytest.mark.asyncio
async def test_no_service_type(agent):
    """Missing service_type → empty candidates with reason."""
    intent = {
        "service_type": None,
        "location_sector": "Lahore",
        "home_city": "Lahore",
        "raw_input": "kuch chahiye",
    }
    result = await agent.run(intent)

    assert result["total_found"] == 0
    assert result["candidates"] == []
    assert result["no_candidates_reason"] is not None


# ── Test 4: City-only sector ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_city_only_sector(agent):
    """City-only location_sector (e.g. 'Karachi') works correctly."""
    intent = {
        "service_type": "Plumber",
        "location_sector": "Karachi",
        "home_city": "Karachi",
        "raw_input": "Karachi mein plumber chahiye",
    }
    result = await agent.run(intent)

    assert result["city_searched"] == "Karachi"
    assert result["total_found"] > 0
    assert result["fallback_used"] is False
    for c in result["candidates"]:
        assert c["home_city"] == "Karachi"
        assert c["category"] == "Plumber"
