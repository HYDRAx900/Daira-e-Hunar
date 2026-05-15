"""
ServiceWala API — FastAPI backend for the AI Service Orchestrator.

Exposes a single POST /request endpoint that will chain four ADK agents
(Intent → Discovery → Ranking → Action) in later phases.

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

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ServiceWala API",
    description="AI Service Orchestrator for Pakistan's Informal Economy",
    version="0.2.0",
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


# ── Request / Response models ────────────────────────────────────────────────

class ServiceRequest(BaseModel):
    """User's natural-language service request."""
    query: str
    mode: str = "agentic"  # "agentic" or "baseline" (Phase 5)


class ServiceResponse(BaseModel):
    """Response containing parsed intent and trace file path."""
    status: str
    message: str
    intent: Optional[dict] = None
    trace_file: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Simple health check for connectivity testing."""
    return {"status": "ok", "service": "ServiceWala API", "version": "0.2.0"}


@app.post("/request", response_model=ServiceResponse)
async def handle_request(request: ServiceRequest):
    """
    Main endpoint — accepts a natural-language service request and
    orchestrates the agent pipeline.

    Phase 1: Intent Agent only (parses NL → structured intent).
    Phases 2–3 will wire up Discovery → Ranking → Action.
    """
    try:
        result = await intent_agent.run(request.query)

        # Extract trace_file from result (added by IntentAgent, not part of LLM schema)
        trace_file = result.pop("_trace_file", None)

        return ServiceResponse(
            status="ok",
            message="Intent parsed successfully.",
            intent=result,
            trace_file=trace_file,
        )
    except Exception as e:
        return ServiceResponse(
            status="error",
            message=f"Intent Agent failed: {str(e)}",
            intent=None,
            trace_file=None,
        )


# ── Entry point (for running directly with `python -m backend.main`) ────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
