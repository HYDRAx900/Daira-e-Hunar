"""
Tests for the Orchestrator.
Deterministic tests using mocked agents.
"""

import pytest
from unittest.mock import patch, AsyncMock
from backend.orchestrator import Orchestrator

@pytest.fixture
def mock_orchestrator():
    orchestrator = Orchestrator()
    orchestrator.intent_agent.run = AsyncMock()
    orchestrator.discovery_agent.run = AsyncMock()
    orchestrator.ranking_agent.run = AsyncMock()
    orchestrator.action_agent.run = AsyncMock()
    return orchestrator

@pytest.mark.asyncio
async def test_full_happy_path(mock_orchestrator):
    # Setup mocks
    mock_orchestrator.intent_agent.run.return_value = {
        "service_type": "AC Technician",
        "location_sector": "Islamabad",
        "needs_clarification": False,
        "_trace_file": "trace/intent.json"
    }
    
    mock_orchestrator.discovery_agent.run.return_value = {
        "candidates": [{"id": "P0003"}],
        "total_found": 1,
        "_trace_file": "trace/discovery.json"
    }
    
    mock_orchestrator.ranking_agent.run.return_value = {
        "top_3": [{"provider_id": "P0003"}],
        "rejected": [],
        "_trace_file": "trace/ranking.json"
    }
    
    mock_orchestrator.action_agent.run.return_value = {
        "status": "confirmed",
        "booking_id": "B123",
        "provider_id": "P0003",
        "_trace_file": "trace/action.json"
    }
    
    result = await mock_orchestrator.run_request("I need an AC technician")
    
    assert result["status"] == "ok"
    assert result["booking"]["status"] == "confirmed"
    assert "intent" in result["trace_files"]
    assert "discovery" in result["trace_files"]
    assert "ranking" in result["trace_files"]
    assert "action" in result["trace_files"]
    
    # Run trace
    assert result["run_trace"].startswith("trace/run_")
    
    # Assert all agents were called
    mock_orchestrator.intent_agent.run.assert_called_once()
    mock_orchestrator.discovery_agent.run.assert_called_once()
    mock_orchestrator.ranking_agent.run.assert_called_once()
    mock_orchestrator.action_agent.run.assert_called_once()

@pytest.mark.asyncio
async def test_needs_clarification_short_circuit(mock_orchestrator):
    mock_orchestrator.intent_agent.run.return_value = {
        "needs_clarification": True,
        "_trace_file": "trace/intent.json"
    }
    mock_orchestrator.action_agent.run.return_value = {
        "status": "needs_clarification",
        "_trace_file": "trace/action.json"
    }
    
    result = await mock_orchestrator.run_request("unknown input")
    
    assert result["status"] == "needs_clarification"
    
    # Discovery and Ranking should NOT be called
    mock_orchestrator.discovery_agent.run.assert_not_called()
    mock_orchestrator.ranking_agent.run.assert_not_called()
    
    # Action should be called to generate the message
    mock_orchestrator.action_agent.run.assert_called_once()

@pytest.mark.asyncio
async def test_zero_discovery_candidates(mock_orchestrator):
    mock_orchestrator.intent_agent.run.return_value = {
        "needs_clarification": False,
        "detected_language": "urdu",
        "_trace_file": "trace/intent.json"
    }
    mock_orchestrator.discovery_agent.run.return_value = {
        "candidates": [],
        "total_found": 0,
        "_trace_file": "trace/discovery.json"
    }
    mock_orchestrator.action_agent.run.return_value = {
        "status": "no_provider",
        "confirmation_language": "urdu",
        "_trace_file": "trace/action.json"
    }
    
    result = await mock_orchestrator.run_request("I need a beautician in Quetta")
    
    assert result["status"] == "no_provider"
    
    # Ranking should NOT be called
    mock_orchestrator.ranking_agent.run.assert_not_called()
    
    # Action should be called to generate the fallback message
    mock_orchestrator.action_agent.run.assert_called_once()
    
    assert result["booking"]["status"] == "no_provider"
    assert result["booking"]["confirmation_language"] == "urdu"

@pytest.mark.asyncio
async def test_baseline_mode_raises(mock_orchestrator):
    with pytest.raises(NotImplementedError):
        await mock_orchestrator.run_request("I need an AC technician", mode="baseline")
