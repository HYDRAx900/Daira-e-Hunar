"""
Orchestrator for Daira-e-Hunar Agentic Loop.
Handles the top-level observe -> reason -> decide -> act sequence.
"""

import time
from datetime import datetime, timezone

from backend.agents.intent_agent import IntentAgent
from backend.agents.discovery_agent import DiscoveryAgent
from backend.agents.ranking_agent import RankingAgent
from backend.agents.action_agent import ActionAgent
from backend.services.trace_writer import write_run_trace

class Orchestrator:
    def __init__(self):
        self.intent_agent = IntentAgent()
        self.discovery_agent = DiscoveryAgent()
        self.ranking_agent = RankingAgent()
        self.action_agent = ActionAgent()

    async def run_request(self, user_query: str, mode: str = "agentic") -> dict:
        if mode == "baseline":
            raise NotImplementedError("Baseline mode is Phase 5")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"run_{timestamp}"
        
        workplan = {
            "run_id": run_id,
            "user_query": user_query,
            "mode": mode,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "stages": [],
            "final_status": "unknown",
            "final_provider_id": None
        }

        def add_stage(agent_name, trace, success, latency):
            workplan["stages"].append({
                "agent": agent_name,
                "trace_file": trace,
                "success": success,
                "latency_ms": latency
            })

        # 1. Intent
        start_time = time.time()
        intent_result = await self.intent_agent.run(user_query)
        latency_ms = (time.time() - start_time) * 1000
        intent_trace = intent_result.pop("_trace_file", None)
        success = not intent_result.get("needs_clarification", False)
        add_stage("intent", intent_trace, success, latency_ms)
        
        if not success:
            # Short-circuit on needs_clarification
            # Orchestrator invokes Action even on short-circuit paths
            start_time = time.time()
            action_result = await self.action_agent.run(intent_result, {})
            latency_ms = (time.time() - start_time) * 1000
            action_trace = action_result.pop("_trace_file", None)
            add_stage("action", action_trace, True, latency_ms)
            
            workplan["final_status"] = "needs_clarification"
            run_trace = write_run_trace(workplan)
            
            return {
                "status": "needs_clarification",
                "message": "Needs clarification.",
                "intent": intent_result,
                "booking": action_result,
                "trace_files": {"intent": intent_trace, "action": action_trace},
                "run_trace": run_trace
            }

        # 2. Discovery
        start_time = time.time()
        discovery_result = await self.discovery_agent.run(intent_result)
        latency_ms = (time.time() - start_time) * 1000
        discovery_trace = discovery_result.pop("_trace_file", None)
        candidates = discovery_result.get("candidates", [])
        success = len(candidates) > 0
        add_stage("discovery", discovery_trace, success, latency_ms)

        discovery_summary = {
            "total_found": discovery_result.get("total_found"),
            "city_searched": discovery_result.get("city_searched"),
            "fallback_used": discovery_result.get("fallback_used"),
            "fallback_reason": discovery_result.get("fallback_reason"),
            "no_candidates_reason": discovery_result.get("no_candidates_reason"),
            "candidate_ids": [c["id"] for c in candidates],
        }

        if not success:
            start_time = time.time()
            action_result = await self.action_agent.run(intent_result, {})
            latency_ms = (time.time() - start_time) * 1000
            action_trace = action_result.pop("_trace_file", None)
            add_stage("action", action_trace, True, latency_ms)
            
            workplan["final_status"] = "no_provider"
            run_trace = write_run_trace(workplan)
            
            return {
                "status": "no_provider",
                "message": "No providers found.",
                "intent": intent_result,
                "discovery": discovery_summary,
                "booking": action_result,
                "trace_files": {"intent": intent_trace, "discovery": discovery_trace, "action": action_trace},
                "run_trace": run_trace
            }

        # 3. Ranking
        start_time = time.time()
        ranking_result = await self.ranking_agent.run(candidates, intent_result)
        latency_ms = (time.time() - start_time) * 1000
        ranking_trace = ranking_result.pop("_trace_file", None)
        top_3 = ranking_result.get("top_3", [])
        success = len(top_3) > 0
        add_stage("ranking", ranking_trace, success, latency_ms)

        if not success:
            start_time = time.time()
            action_result = await self.action_agent.run(intent_result, ranking_result)
            latency_ms = (time.time() - start_time) * 1000
            action_trace = action_result.pop("_trace_file", None)
            add_stage("action", action_trace, True, latency_ms)
            
            workplan["final_status"] = "no_provider"
            run_trace = write_run_trace(workplan)
            
            return {
                "status": "no_provider",
                "message": "No providers ranked.",
                "intent": intent_result,
                "discovery": discovery_summary,
                "ranking": ranking_result,
                "booking": action_result,
                "trace_files": {"intent": intent_trace, "discovery": discovery_trace, "ranking": ranking_trace, "action": action_trace},
                "run_trace": run_trace
            }

        # 4. Action
        start_time = time.time()
        selected_provider_id = top_3[0]["provider_id"]
        action_result = await self.action_agent.run(intent_result, ranking_result, selected_provider_id)
        latency_ms = (time.time() - start_time) * 1000
        action_trace = action_result.pop("_trace_file", None)
        success = action_result.get("status") == "confirmed"
        add_stage("action", action_trace, success, latency_ms)

        workplan["final_status"] = action_result.get("status")
        workplan["final_provider_id"] = action_result.get("provider_id")
        run_trace = write_run_trace(workplan)

        return {
            "status": "ok",
            "message": "Pipeline complete.",
            "intent": intent_result,
            "discovery": discovery_summary,
            "ranking": ranking_result,
            "booking": action_result,
            "trace_files": {
                "intent": intent_trace,
                "discovery": discovery_trace,
                "ranking": ranking_trace,
                "action": action_trace
            },
            "run_trace": run_trace
        }
