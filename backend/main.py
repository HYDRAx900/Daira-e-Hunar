"""
Daira-e-Hunar API — FastAPI backend for the AI Service Orchestrator.

Exposes a single POST /request endpoint that chains three ADK agents:
Intent -> Discovery -> Ranking.

Run with:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
"""

from dotenv import load_dotenv

# Load .env BEFORE importing config so env vars are available
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from backend.config import HOST, PORT
from backend.agents.intent_agent import IntentAgent
from backend.agents.discovery_agent import DiscoveryAgent
from backend.agents.ranking_agent import RankingAgent

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Daira-e-Hunar API",
    description="Daira-e-Hunar — AI Service Orchestrator for Pakistan's Informal Economy",
    version="0.4.0",
)

# Allow all origins — needed for Flutter web during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Agent instances ──────────────────────────────────────────────────────────

intent_agent = IntentAgent()
discovery_agent = DiscoveryAgent()
ranking_agent = RankingAgent()


# ── Request / Response models ────────────────────────────────────────────────

class ServiceRequest(BaseModel):
    """User's natural-language service request."""
    query: str
    mode: str = "agentic"  # "agentic" or "baseline" (Phase 5)


class ServiceResponse(BaseModel):
    """Response containing the full agent pipeline results."""
    status: str
    message: str
    intent: Optional[dict] = None
    discovery: Optional[dict] = None
    ranking: Optional[dict] = None
    trace_files: Optional[dict] = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Simple health check for connectivity testing."""
    return {"status": "ok", "service": "Daira-e-Hunar API", "version": "0.4.0"}


@app.post("/request", response_model=ServiceResponse)
async def handle_request(request: ServiceRequest):
    """
    Main endpoint — accepts a natural-language service request and
    orchestrates the agent pipeline.

    Pipeline: Intent -> Discovery -> Ranking.
    If Discovery returns zero candidates, Ranking is skipped.
    """
    trace_files = {}

    try:
        # ── Stage 1: Intent Agent ────────────────────────────────────
        intent_result = await intent_agent.run(request.query)
        trace_files["intent"] = intent_result.pop("_trace_file", None)

        # ── Stage 2: Discovery Agent ─────────────────────────────────
        discovery_result = await discovery_agent.run(intent_result)
        trace_files["discovery"] = discovery_result.pop("_trace_file", None)

        # Strip full provider dicts from response (too large) — keep IDs
        candidates = discovery_result.get("candidates", [])
        discovery_summary = {
            "total_found": discovery_result["total_found"],
            "city_searched": discovery_result["city_searched"],
            "fallback_used": discovery_result["fallback_used"],
            "fallback_reason": discovery_result.get("fallback_reason"),
            "no_candidates_reason": discovery_result.get("no_candidates_reason"),
            "candidate_ids": [c["id"] for c in candidates],
        }

        # ── Stage 3: Ranking Agent (skip if no candidates) ───────────
        ranking_result = None
        if candidates:
            ranking_result = await ranking_agent.run(candidates, intent_result)
            trace_files["ranking"] = ranking_result.pop("_trace_file", None)
            message = "Pipeline complete: Intent -> Discovery -> Ranking."
        else:
            message = (
                "Pipeline partial: Intent -> Discovery (no candidates found). "
                "Ranking skipped."
            )

        return ServiceResponse(
            status="ok",
            message=message,
            intent=intent_result,
            discovery=discovery_summary,
            ranking=ranking_result,
            trace_files=trace_files,
        )
    except Exception as e:
        return ServiceResponse(
            status="error",
            message=f"Pipeline failed: {str(e)}",
            intent=None,
            discovery=None,
            ranking=None,
            trace_files=trace_files if trace_files else None,
        )


# ── Entry point (for running directly with `python -m backend.main`) ────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
