"""
Discovery Agent — deterministic provider filtering.

Given a parsed intent, filters mock_data/providers.json by home_city and
service_type. No LLM call — the agentic reasoning happens in Ranking.

Handles edge cases:
  - Zero candidates in the target city → broadens to nationwide (fallback).
  - Still zero (e.g. service_type is None) → returns empty with reason.

Every invocation writes a trace file to trace/ for judge review.
"""

import json
from pathlib import Path

from backend.config import MOCK_DATA_DIR
from backend.services.trace_writer import write_discovery_trace
from backend.services.geo_service import CITY_CENTROIDS


# ── Helper: extract target city from location_sector ─────────────────────────

def _extract_city(location_sector: str | None, home_city: str | None) -> str | None:
    """
    Determine the target city from the intent fields.

    Logic:
      - "Lyari, Karachi" → "Karachi" (split on comma, take city part)
      - "Lahore" → "Lahore" (city-only sector, check CITY_CENTROIDS)
      - None → fall back to home_city
    """
    if location_sector:
        # "Neighborhood, City" format
        if ", " in location_sector:
            city_part = location_sector.split(", ")[-1].strip()
            if city_part in CITY_CENTROIDS:
                return city_part

        # City-only format (e.g. "Lahore")
        if location_sector in CITY_CENTROIDS:
            return location_sector

    # Fall back to home_city
    if home_city and home_city in CITY_CENTROIDS:
        return home_city

    return None


# ── Agent class ──────────────────────────────────────────────────────────────

class DiscoveryAgent:
    """
    Discovers matching service providers from the mock data.

    Deterministic filtering by home_city + service_type.
    Falls back to nationwide search when zero in-city candidates.
    """

    def __init__(self):
        self._providers = self._load_providers()

    def _load_providers(self) -> list[dict]:
        """Load providers.json once at init."""
        providers_path = MOCK_DATA_DIR / "providers.json"
        with open(providers_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def run(self, intent: dict) -> dict:
        """
        Find candidate providers matching the parsed intent.

        Args:
            intent: Structured intent dict from IntentAgent.

        Returns:
            Dict with 'candidates' list and metadata.
        """
        service_type = intent.get("service_type")
        location_sector = intent.get("location_sector")
        home_city = intent.get("home_city")

        target_city = _extract_city(location_sector, home_city)

        # Guard: no service_type → can't filter
        if not service_type:
            result = {
                "candidates": [],
                "total_found": 0,
                "city_searched": target_city,
                "fallback_used": False,
                "fallback_reason": None,
                "no_candidates_reason": (
                    "Cannot discover providers: service_type is not specified."
                ),
            }
            self._write_trace(intent, target_city, service_type, result)
            return result

        # ── Primary filter: city + category ──────────────────────────────
        candidates = [
            p for p in self._providers
            if p["home_city"] == target_city and p["category"] == service_type
        ]

        fallback_used = False
        fallback_reason = None
        no_candidates_reason = None

        if not candidates and target_city:
            # ── Fallback: broaden to nationwide ──────────────────────────
            candidates = [
                p for p in self._providers
                if p["category"] == service_type
            ]
            fallback_used = True
            fallback_reason = (
                f"No {service_type} found in {target_city}; "
                f"broadened to nationwide"
            )

        if not candidates:
            no_candidates_reason = (
                f"No providers found for category '{service_type}' "
                f"in any city."
            )

        result = {
            "candidates": candidates,
            "total_found": len(candidates),
            "city_searched": target_city,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "no_candidates_reason": no_candidates_reason,
        }

        self._write_trace(intent, target_city, service_type, result)
        return result

    def _write_trace(
        self,
        intent: dict,
        target_city: str | None,
        service_type: str | None,
        result: dict,
    ) -> str:
        """Write a discovery trace and attach the path to the result."""
        filter_applied = {
            "city": target_city,
            "service_type": service_type,
        }

        trace_file = write_discovery_trace(
            intent_input=intent,
            filter_applied=filter_applied,
            candidates_returned=result["candidates"],
            fallback_used=result["fallback_used"],
            fallback_reason=result["fallback_reason"],
            no_candidates_reason=result["no_candidates_reason"],
        )

        result["_trace_file"] = trace_file
        return trace_file
