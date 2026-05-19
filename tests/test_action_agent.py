"""
Tests for the Action Agent.
Deterministic tests using patched mock data and mocked LLM calls.
"""

import os
import json
import pytest
import shutil
from unittest.mock import patch, AsyncMock
from backend.agents.action_agent import ActionAgent

@pytest.fixture
def tmp_mock_dir(tmp_path):
    """Create a temporary mock data directory to avoid mutating real files."""
    mock_dir = tmp_path / "mock_data"
    mock_dir.mkdir()
    
    # Copy providers
    src_providers = os.path.join("mock_data", "providers.json")
    dst_providers = mock_dir / "providers.json"
    shutil.copy(src_providers, dst_providers)
    
    # Create empty bookings and followups
    (mock_dir / "bookings.json").write_text("[]")
    (mock_dir / "followups.json").write_text("[]")
    
    with patch("backend.agents.action_agent.MOCK_DATA_DIR", str(mock_dir)):
        yield mock_dir

@pytest.fixture
def mock_intent():
    return {
        "service_type": "AC Technician",
        "location_sector": "Islamabad",
        "requested_time": "tomorrow morning",
        "urgency": "this_week",
        "detected_language": "roman_urdu",
        "formality_level": "casual",
        "code_switching": False
    }

@pytest.fixture
def mock_ranking():
    return {
        "top_3": [
            {
                "provider_id": "P0003",
                "score": 0.95,
                "reasoning": "Dost Muhammad is a great AC tech."
            }
        ],
        "rejected": []
    }

@pytest.fixture
def action_agent():
    return ActionAgent()

@pytest.fixture
def mock_llm_confirmation():
    with patch("backend.agents.action_agent.ActionAgent._call_llm_with_retry", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = ("Test confirmation message", "roman_urdu", "prompt", "raw_response")
        yield mock_llm

@pytest.mark.asyncio
async def test_happy_path(tmp_mock_dir, action_agent, mock_intent, mock_ranking, mock_llm_confirmation):
    # Initial state
    with open(tmp_mock_dir / "providers.json", "r", encoding="utf-8") as f:
        initial_providers = json.load(f)
    initial_p0003 = next(p for p in initial_providers if p["id"] == "P0003")
    initial_slot_count = len(initial_p0003["available_slots"])

    result = await action_agent.run(mock_intent, mock_ranking, "P0003")
    
    assert result["status"] == "confirmed"
    assert result["booking_id"].startswith("B")
    assert result["provider_id"] == "P0003"
    assert len(result["followups_scheduled"]) == 2
    assert result["receipt_path"].startswith("trace/receipt_")

    # Verify mutations
    with open(tmp_mock_dir / "bookings.json", "r", encoding="utf-8") as f:
        bookings = json.load(f)
    assert len(bookings) == 1
    assert bookings[0]["booking_id"] == result["booking_id"]

    with open(tmp_mock_dir / "providers.json", "r", encoding="utf-8") as f:
        final_providers = json.load(f)
    final_p0003 = next(p for p in final_providers if p["id"] == "P0003")
    assert len(final_p0003["available_slots"]) == initial_slot_count - 1

@pytest.mark.asyncio
async def test_slot_taken_race_condition(tmp_mock_dir, action_agent, mock_intent, mock_ranking, mock_llm_confirmation):
    # Get provider and slot
    with open(tmp_mock_dir / "providers.json", "r", encoding="utf-8") as f:
        providers = json.load(f)
    p0003 = next(p for p in providers if p["id"] == "P0003")
    
    slot_chosen, time_neg = action_agent._select_slot(p0003, mock_intent)
    assert slot_chosen is not None
    
    # Mutate file directly to simulate race condition
    p0003["available_slots"].remove(slot_chosen)
    with open(tmp_mock_dir / "providers.json", "w", encoding="utf-8") as f:
        json.dump(providers, f)
        
    # Assert _race_check_and_reserve fails
    assert not action_agent._race_check_and_reserve("P0003", slot_chosen)

@pytest.mark.asyncio
async def test_no_slots_available(tmp_mock_dir, action_agent, mock_intent, mock_ranking, mock_llm_confirmation):
    # Mutate to zero slots
    with open(tmp_mock_dir / "providers.json", "r", encoding="utf-8") as f:
        providers = json.load(f)
    p0003 = next(p for p in providers if p["id"] == "P0003")
    p0003["available_slots"] = []
    with open(tmp_mock_dir / "providers.json", "w", encoding="utf-8") as f:
        json.dump(providers, f)
        
    result = await action_agent.run(mock_intent, mock_ranking, "P0003")
    assert result["status"] == "no_slots_available"

@pytest.mark.asyncio
async def test_time_negotiation(tmp_mock_dir, action_agent, mock_intent, mock_ranking, mock_llm_confirmation):
    mock_intent["urgency"] = "today"
    mock_intent["requested_time"] = "morning" 
    
    # Mutate P0003 slots so none are in the morning (06-11)
    with open(tmp_mock_dir / "providers.json", "r", encoding="utf-8") as f:
        providers = json.load(f)
    p0003 = next(p for p in providers if p["id"] == "P0003")
    p0003["available_slots"] = ["2026-05-21T15:00:00+05:00"] # 3 PM
    with open(tmp_mock_dir / "providers.json", "w", encoding="utf-8") as f:
        json.dump(providers, f)
        
    result = await action_agent.run(mock_intent, mock_ranking, "P0003")
    assert result["status"] == "confirmed"
    assert result["time_negotiated"] is True

@pytest.mark.asyncio
async def test_atomicity(tmp_mock_dir, action_agent, mock_intent, mock_ranking, mock_llm_confirmation):
    result = await action_agent.run(mock_intent, mock_ranking, "P0003")
    assert result["status"] == "confirmed"
    
    # File must be valid JSON
    with open(tmp_mock_dir / "providers.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) == 100
