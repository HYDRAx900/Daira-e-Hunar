"""
Centralized configuration for the Daira-e-Hunar backend.
Reads from environment variables (loaded via .env file).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend/ directory — makes config self-contained
# regardless of entry point (uvicorn, pytest, direct script)
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH, override=False)


# --- Paths ---
# Project root is one level up from backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOCK_DATA_DIR = PROJECT_ROOT / "mock_data"
TRACE_DIR = PROJECT_ROOT / "trace"

# --- API Keys & Model ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")

# --- Server ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
