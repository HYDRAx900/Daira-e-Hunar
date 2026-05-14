"""
Intent Agent — Phase 1 will implement this.

Responsibilities:
  - Accept free-form text in English, Urdu, or Roman Urdu.
  - Use Gemini (via ADK) to parse the request into a structured intent JSON.
  - Write a trace file for every invocation.
"""


class IntentAgent:
    """
    Parses natural-language service requests into structured intents.

    Phase 0: stub — returns a placeholder dict.
    Phase 1: will use google.adk LlmAgent with Gemini 2.5 Flash.
    """

    async def run(self, text: str) -> dict:
        """
        Parse a user's natural-language request.

        Args:
            text: Raw user input (English, Urdu, or Roman Urdu).

        Returns:
            Structured intent dict with service_type, location, time, etc.
        """
        return {
            "service_type": None,
            "location_sector": None,
            "requested_time": None,
            "urgency": "flexible",
            "constraints": {},
            "raw_input": text,
            "detected_language": None,
            "confidence": 0.0,
            "needs_clarification": True,
            "clarification_question": "Intent Agent not yet implemented (Phase 1).",
        }
