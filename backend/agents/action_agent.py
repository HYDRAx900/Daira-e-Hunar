"""
Action Agent — Phase 3 will implement this.

Responsibilities:
  - Given a selected provider and intent, perform the BOOKING SIMULATION:
    1. Reserve a slot from the provider's available_slots.
    2. Append a booking entry to mock_data/bookings.json.
    3. Generate a confirmation message in the user's language.
    4. Schedule follow-up (reminder + post-job rating prompt).
    5. Write a booking receipt to trace/.
  - Handle edge cases: no slots, race conditions, zero candidates.
"""


class ActionAgent:
    """
    Performs the booking action and generates follow-up tasks.

    Phase 0: stub — returns a placeholder booking result.
    Phase 3: will write to bookings.json, generate multilingual
    confirmations, and schedule follow-ups.
    """

    async def run(self, provider: dict, intent: dict) -> dict:
        """
        Book a service provider and generate confirmation.

        Args:
            provider: Selected provider dict (top-1 from RankingAgent
                      or user override).
            intent: Structured intent dict from IntentAgent.

        Returns:
            Dict with booking details, confirmation message, and
            follow-up schedule.
        """
        return {
            "booking_id": None,
            "status": "not_implemented",
            "confirmation_message": "Action Agent not yet implemented (Phase 3).",
            "follow_ups": [],
        }
