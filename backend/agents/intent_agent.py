"""
Intent Agent — Parses natural-language service requests into structured intents.

Uses Gemini 2.5 Flash via the google-genai SDK with JSON-mode output
and a Pydantic response schema for reliable structured extraction.

Supports English, Urdu (script), and Roman Urdu inputs.
Every invocation writes a trace file to trace/ for judge review.
"""

import json
import time
from typing import Literal, Optional

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from backend.config import GOOGLE_API_KEY, MODEL_NAME
from backend.services.trace_writer import write_intent_trace


# ── Pydantic schema for structured LLM output ───────────────────────────────

class IntentConstraints(BaseModel):
    """Optional constraints the user specified."""
    gender_preference: Optional[str] = Field(
        None, description="Preferred gender of the service provider, if mentioned"
    )
    budget_max_pkr: Optional[int] = Field(
        None, description="Maximum budget in PKR, if mentioned"
    )


class IntentResult(BaseModel):
    """Structured intent parsed from a user's service request."""
    service_type: Optional[str] = Field(
        None,
        description=(
            "The type of service requested. Must be one of: "
            "'AC Technician', 'Plumber', 'Electrician', 'Tutor', 'Beautician'. "
            "Set to null if you cannot determine the service type."
        ),
    )
    location_sector: Optional[str] = Field(
        None,
        description=(
            "The sector/area in Islamabad or Rawalpindi. Known sectors: "
            "G-13, G-11, F-10, F-11, I-8, I-10, Blue Area, DHA Phase 2 Rawalpindi. "
            "Set to null if the user did not specify a location."
        ),
    )
    requested_time: Optional[str] = Field(
        None,
        description=(
            "When the user wants the service. Use ISO 8601 datetime if specific, "
            "or a descriptive string like 'tomorrow morning', 'this weekend'. "
            "Set to null if not mentioned."
        ),
    )
    urgency: Literal["now", "today", "this_week", "flexible"] = Field(
        "flexible",
        description=(
            "How urgently the service is needed. 'now' = immediately, "
            "'today' = within today, 'this_week' = within the week, "
            "'flexible' = no time pressure or not specified."
        ),
    )
    constraints: IntentConstraints = Field(
        default_factory=IntentConstraints,
        description="Additional constraints like gender preference or budget.",
    )
    raw_input: str = Field(
        description="The original user input text, echoed back verbatim."
    )
    detected_language: Literal["english", "urdu", "roman_urdu"] = Field(
        description=(
            "The language of the user's input. "
            "'english' for English, 'urdu' for Urdu script, "
            "'roman_urdu' for Urdu written in Latin characters."
        ),
    )
    confidence: float = Field(
        description=(
            "Your confidence in the overall parse, from 0.0 to 1.0. "
            "Be CONSERVATIVE: return confidence < 0.7 whenever ANY field "
            "is inferred rather than explicitly stated by the user. "
            "Return confidence < 0.5 if the input is nonsensical or "
            "you cannot determine the service type."
        ),
    )
    needs_clarification: bool = Field(
        description=(
            "Set to true if service_type, location_sector, OR requested_time "
            "is missing or ambiguous in the user's input. The system should "
            "ask a follow-up question before proceeding."
        ),
    )
    clarification_question: Optional[str] = Field(
        None,
        description=(
            "A follow-up question to ask the user, in the same language they "
            "used. Only set when needs_clarification is true. Ask about the "
            "most important missing field first."
        ),
    )


# ── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an intent-parsing agent for ServiceWala, a service marketplace operating in Islamabad and Rawalpindi, Pakistan.

Your job: take a user's free-form text — which may be in English, Urdu (script), or Roman Urdu (Urdu written in Latin characters) — and extract a structured service request.

## Valid service types
- AC Technician
- Plumber
- Electrician
- Tutor
- Beautician

## Known sectors/areas
- G-13, G-11, F-10, F-11, I-8, I-10 (Islamabad sectors)
- Blue Area (Islamabad commercial district)
- DHA Phase 2 Rawalpindi

## Confidence scoring rules (IMPORTANT — be conservative)
- Return confidence >= 0.8 ONLY when service_type, location, AND time are ALL explicitly stated.
- Return confidence 0.5–0.7 when you had to INFER any field (e.g., "tap fix" → Plumber is an inference).
- Return confidence < 0.5 for nonsensical, unrelated, or extremely vague inputs.

## Clarification rules
- Set needs_clarification = true when service_type, location_sector, OR requested_time is missing or ambiguous.
- When needs_clarification is true, generate a helpful clarification_question in the SAME LANGUAGE the user used.
- Ask about the most critical missing field first (usually service_type > location > time).

## Urgency mapping
- Words like "abhi", "now", "immediately", "foran" → "now"
- Words like "aaj", "today" → "today"
- Words like "is hafte", "this week", "weekend" → "this_week"
- No time pressure or not mentioned → "flexible"
- "jaldi" (quickly) → "now" or "today" depending on context
- "kal" (tomorrow) → "today" or "this_week" depending on context

## Few-shot examples

INPUT: "Mujhe kal subah G-13 mein AC technician chahiye"
OUTPUT: service_type="AC Technician", location_sector="G-13", requested_time="tomorrow morning", urgency="this_week", detected_language="roman_urdu", confidence=0.92, needs_clarification=false

INPUT: "G-11 mein plumber chahiye abhi"
OUTPUT: service_type="Plumber", location_sector="G-11", requested_time=null, urgency="now", detected_language="roman_urdu", confidence=0.85, needs_clarification=true (requested_time missing), clarification_question="Kya aap abhi foran plumber chahte hain ya koi specific time hai?"

INPUT: "I need a tutor for O-level math in F-10 this weekend"
OUTPUT: service_type="Tutor", location_sector="F-10", requested_time="this weekend", urgency="this_week", detected_language="english", confidence=0.90, needs_clarification=false

INPUT: "بیوٹیشن چاہیے DHA میں"
OUTPUT: service_type="Beautician", location_sector="DHA Phase 2 Rawalpindi", requested_time=null, urgency="flexible", detected_language="urdu", confidence=0.75, needs_clarification=true (requested_time missing), clarification_question="آپ کو بیوٹیشن کب چاہیے؟"

INPUT: "electrician F-11 jaldi"
OUTPUT: service_type="Electrician", location_sector="F-11", requested_time=null, urgency="now", detected_language="roman_urdu", confidence=0.80, needs_clarification=true (requested_time missing), clarification_question="Kab chahiye? Abhi ya aaj kisi waqt?"

Always echo the original user input verbatim in the raw_input field."""


# ── Agent class ──────────────────────────────────────────────────────────────

class IntentAgent:
    """
    Parses natural-language service requests into structured intents.

    Uses Gemini 2.5 Flash with JSON-mode output and Pydantic response schema.
    Every invocation writes a trace file to trace/ for judge review.
    """

    def __init__(self):
        if not GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is not set. Check your .env file."
            )
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
        self.model_name = MODEL_NAME

    def _build_prompt(self, text: str) -> str:
        """Build the full prompt string sent to the LLM."""
        return f"{SYSTEM_PROMPT}\n\n---\n\nUser input: {text}"

    async def run(self, text: str) -> dict:
        """
        Parse a user's natural-language request.

        Args:
            text: Raw user input (English, Urdu, or Roman Urdu).

        Returns:
            Structured intent dict with service_type, location, time, etc.
            Also returns a 'trace_file' key with the path to the trace.
        """
        prompt = self._build_prompt(text)

        start_time = time.time()

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=IntentResult,
                temperature=0.2,  # low temp for consistent parsing
            ),
        )

        latency_ms = (time.time() - start_time) * 1000
        raw_response_text = response.text

        # Parse the JSON response
        try:
            parsed = json.loads(raw_response_text)
        except json.JSONDecodeError:
            parsed = {
                "service_type": None,
                "location_sector": None,
                "requested_time": None,
                "urgency": "flexible",
                "constraints": {},
                "raw_input": text,
                "detected_language": "english",
                "confidence": 0.0,
                "needs_clarification": True,
                "clarification_question": "Sorry, I could not understand your request. Could you please rephrase?",
            }

        # Ensure raw_input is always the original text
        parsed["raw_input"] = text

        # Write trace file
        trace_file = write_intent_trace(
            user_input=text,
            prompt_sent=prompt,
            raw_llm_response=raw_response_text,
            parsed_output=parsed,
            model_name=self.model_name,
            latency_ms=latency_ms,
        )

        # Attach trace path to the result (not part of the LLM schema,
        # but useful for the API response)
        result = dict(parsed)
        result["_trace_file"] = trace_file

        return result
