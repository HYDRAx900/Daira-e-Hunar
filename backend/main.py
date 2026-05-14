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

from backend.config import HOST, PORT

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ServiceWala API",
    description="AI Service Orchestrator for Pakistan's Informal Economy",
    version="0.1.0",
)

# Allow all origins — needed for Flutter web during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ────────────────────────────────────────────────

class ServiceRequest(BaseModel):
    """User's natural-language service request."""
    query: str
    mode: str = "agentic"  # "agentic" or "baseline" (Phase 5)


class ServiceResponse(BaseModel):
    """Placeholder response — will be enriched in Phases 1–3."""
    status: str
    message: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Simple health check for connectivity testing."""
    return {"status": "ok", "service": "ServiceWala API", "version": "0.1.0"}


@app.post("/request", response_model=ServiceResponse)
async def handle_request(request: ServiceRequest):
    """
    Main endpoint — accepts a natural-language service request and
    orchestrates the four-agent pipeline.

    Phase 0: returns a stub response.
    Phases 1–3 will wire up Intent → Discovery → Ranking → Action.
    """
    return ServiceResponse(
        status="not_implemented",
        message=(
            f"Received query: '{request.query}' in mode '{request.mode}'. "
            "Agent pipeline not yet wired — see Phase 1."
        ),
    )


# ── Entry point (for running directly with `python -m backend.main`) ────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
