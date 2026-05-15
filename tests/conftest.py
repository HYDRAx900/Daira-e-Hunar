"""
Pytest configuration for ServiceWala tests.

Loads .env before any tests run and configures asyncio mode.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def pytest_configure(config):
    """Load environment variables before test collection."""
    # .env lives in backend/ — load it explicitly
    env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
    load_dotenv(env_path, override=True)

    # Force reload of config values since they were read at import time
    # by setting them in os.environ before any test imports config
    # (dotenv has already done this via override=True)
