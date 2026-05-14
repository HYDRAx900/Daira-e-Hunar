"""
Discovery Agent — Phase 2 will implement this.

Responsibilities:
  - Given a parsed intent, query mock_data/providers.json.
  - Filter by service_type AND sector (or adjacent sectors via geo_service).
  - Handle edge cases: zero candidates → widen search or report gracefully.
"""


class DiscoveryAgent:
    """
    Discovers matching service providers from the mock data.

    Phase 0: stub — returns an empty candidate list.
    Phase 2: will filter providers.json using geo_service for adjacency.
    """

    async def run(self, intent: dict) -> dict:
        """
        Find candidate providers matching the parsed intent.

        Args:
            intent: Structured intent dict from IntentAgent.

        Returns:
            Dict with 'candidates' list and metadata.
        """
        return {
            "candidates": [],
            "total_found": 0,
            "sector_searched": intent.get("location_sector"),
            "fallback_used": False,
            "no_candidates_reason": "Discovery Agent not yet implemented (Phase 2).",
        }
