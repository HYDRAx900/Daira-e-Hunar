"""
Centralized configuration for the ServiceWala backend.
Reads from environment variables (loaded via .env file).
"""

import os
from pathlib import Path

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
