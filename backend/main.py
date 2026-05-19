"""
Daira-e-Hunar API — FastAPI backend for the AI Service Orchestrator.

Exposes a single POST /request endpoint that chains four ADK agents:
Intent -> Discovery -> Ranking -> Action.

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
from backend.orchestrator import Orchestrator

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Daira-e-Hunar API",
    description="Daira-e-Hunar — AI Service Orchestrator for Pakistan's Informal Economy",
    version="0.5.0",
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

orchestrator = Orchestrator()


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
    booking: Optional[dict] = None
    trace_files: Optional[dict] = None
    run_trace: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Simple health check for connectivity testing."""
    return {"status": "ok", "service": "Daira-e-Hunar API", "version": "0.5.0"}


@app.post("/request", response_model=ServiceResponse)
async def handle_request(request: ServiceRequest):
    """
    Main endpoint — accepts a natural-language service request and
    orchestrates the agent pipeline.
    """
    try:
        result = await orchestrator.run_request(request.query, request.mode)
        return ServiceResponse(
            status=result.get("status", "error"),
            message=result.get("message", "Pipeline complete."),
            intent=result.get("intent"),
            discovery=result.get("discovery"),
            ranking=result.get("ranking"),
            booking=result.get("booking"),
            trace_files=result.get("trace_files"),
            run_trace=result.get("run_trace"),
        )
    except Exception as e:
        return ServiceResponse(
            status="error",
            message=f"Pipeline failed: {str(e)}"
        )


# ── Entry point (for running directly with `python -m backend.main`) ────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
