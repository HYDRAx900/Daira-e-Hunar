"""
Ranking Agent — LLM-driven provider ranking with tone-mirrored reasoning.

THIS IS THE CENTERPIECE of the Daira-e-Hunar demo. The Ranking Agent uses
Gemini 2.5 Flash to produce natural-language justification for each ranked
provider, mirroring the user's language, formality, and register.

No hard-coded weighted ranking formula. The LLM is the ranker.
Every invocation writes a trace file to trace/ for judge review.
"""

import json
import time
from typing import Optional

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from backend.config import GOOGLE_API_KEY, MODEL_NAME
from backend.services.trace_writer import write_ranking_trace
from backend.services.geo_service import get_distance_km, resolve_user_location


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class RankedProvider(BaseModel):
    """A provider that made the top ranking."""
    provider_id: str = Field(
        description="The provider's ID (e.g. 'P0021')."
    )
    score: float = Field(
        description=(
            "Overall suitability score from 0.0 to 1.0. "
            "Consider distance, rating, availability, bio relevance, "
            "language compatibility, and price."
        ),
    )
    reasoning: str = Field(
        description=(
            "2-4 sentence explanation of why this provider is recommended. "
            "MUST be written in the SAME language and formality level the "
            "user used. Name specific facts: distance, rating, slot "
            "availability, bio detail, price range. No generic platitudes."
        ),
    )


class RejectedProvider(BaseModel):
    """A provider that was filtered out of the top ranking."""
    provider_id: str = Field(
        description="The provider's ID."
    )
    reason: str = Field(
        description=(
            "Short reason for rejection (1 sentence). "
            "E.g. 'Too far (45 km)', 'No available slots', 'Low rating (2.1/5)'."
        ),
    )


class RankingResult(BaseModel):
    """The full ranking output from the LLM."""
    top_3: list[RankedProvider] = Field(
        description=(
            "Up to 3 top-ranked providers, ordered by suitability. "
            "Return fewer if fewer candidates exist — do NOT pad with "
            "duplicates or fabricate providers. Minimum 1, maximum 3."
        ),
    )
    rejected: list[RejectedProvider] = Field(
        description="Providers not included in top_3, with rejection reasons.",
    )


# ── System prompt ────────────────────────────────────────────────────────────

RANKING_SYSTEM_PROMPT = """You are the Ranking Agent for Daira-e-Hunar, a service marketplace for Pakistan's informal economy. Your job: given a user's service request and a list of candidate providers, rank the providers and explain WHY each one is recommended or rejected.

## Your output
Return up to 3 ranked providers in the `top_3` list, ordered by suitability (best first). If fewer than 3 candidates exist, return fewer — do NOT pad with duplicates or fabricate providers. Put all remaining candidates in the `rejected` list with a short reason.

## PILLAR 1: TONE MIRRORING (CRITICAL)
Write ALL reasoning text in the SAME language and formality level the user used:
- If detected_language="roman_urdu" and formality_level="slang" → write reasoning in casual Roman Urdu with slang (use "yaar", "bhai", "behtareen", "acha" etc.)
- If detected_language="roman_urdu" and formality_level="casual" → write reasoning in normal Roman Urdu
- If detected_language="roman_urdu" and formality_level="formal" → write reasoning in polite Roman Urdu (use "aap", "behtar")
- If detected_language="urdu" and formality_level="formal" → write reasoning in formal Urdu script
- If detected_language="urdu" and formality_level="casual" → write reasoning in conversational Urdu script
- If detected_language="english" → write reasoning in English
- If code_switching=true → mirror the English/Urdu mix in your reasoning

Examples:
- Slang Roman Urdu: "Yaar ye banda sab se qareeb hai, sirf 2 km door. Rating bhi 4.5 hai aur 12 saal ka tajurba hai. AC split ka kaam karta hai, kal subah ke liye slot bhi khali hai."
- Formal Urdu script: "یہ فراہم کنندہ آپ کے علاقے سے صرف ۲ کلومیٹر کے فاصلے پر ہیں۔ ان کی درجہ بندی ۴.۵ ہے اور ۱۲ سال کا تجربہ رکھتے ہیں۔ کل صبح کے لیے وقت دستیاب ہے۔"
- English: "This provider is only 2 km away with a 4.5 rating and 12 years of experience. They specialize in split AC installation and have a slot available tomorrow morning."

## PILLAR 2: READ THE BIO
The `bio` field carries human signal that ratings don't. Reference specific bio details when they inform the ranking:
- A provider whose bio mentions specialization in the requested service type is a strength.
- A provider whose bio implies a DIFFERENT specialty than their listed category is a RED FLAG. For example, a "Tutor" whose bio is about "stitching bridal lehengas" should be deprioritized and the mismatch should be flagged in the reasoning.
- Bio details about reliability, family tradition, or specific expertise are worth mentioning.

## PILLAR 3: LANGUAGE & REGIONAL COMPATIBILITY
When a provider's `languages_spoken` overlaps with the user's likely language (inferred from detected_language), or when the provider is from the same locality as the user's requested area, you may note this as a practical communication or local-knowledge advantage.
- NEVER frame this as ethnicity matching. Talk about language and locality, not ethnicity.
- If the user explicitly stated a language preference (e.g. "Pashto bolne wala chahiye"), honor it as a HARD preference and surface it prominently in the reasoning. Deprioritize providers who don't speak the requested language.

## PILLAR 4: CONSISTENCY REASONING
If `requested_time` and `urgency` appear inconsistent:
- "kal subah" (tomorrow morning) + urgency="this_week" → the specific signal "kal subah" is more precise; use tomorrow morning as the actual constraint.
- Mention the reconciliation briefly in the reasoning (e.g. "User ne 'kal subah' kaha, is liye kal ka slot check kiya").

## PILLAR 5: GROUNDED REASONING
Each reasoning paragraph MUST be 2-4 sentences. Name SPECIFIC facts:
- Distance in km (use the distance_km field provided)
- Rating and rating_count
- Number of available slots and specific slot times when relevant
- Bio details that matter
- Price range
- Verified status
No generic platitudes. No performative empathy. Concrete and grounded.

## Scoring guidelines
- Distance: closer is better, but not the only factor
- Rating: weight higher ratings, but also consider rating_count (a 4.8 with 5 reviews is less reliable than a 4.3 with 150 reviews)
- Availability: providers with slots matching the user's requested_time score higher
- Bio relevance: bio matching the service type is a plus; bio mismatching is a penalty
- Verified: slight bonus for verified providers
- Price: reasonable price ranges preferred; very cheap + low rating = red flag
- Language: matching the user's language is a practical advantage

## Input format
You will receive:
- The user's original request and parsed intent fields
- A list of candidate providers with their details and pre-computed distance_km

Rank them and explain your reasoning."""


# ── Agent class ──────────────────────────────────────────────────────────────

class RankingAgent:
    """
    LLM-driven ranking of candidate providers.

    Uses Gemini 2.5 Flash with JSON-mode output and Pydantic response schema.
    Pre-computes distances via geo_service before sending to the LLM.
    Every invocation writes a trace file to trace/ for judge review.
    """

    def __init__(self):
        if not GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is not set. Check your .env file."
            )
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
        self.model_name = MODEL_NAME

    def _build_candidate_payload(
        self,
        candidates: list[dict],
        user_location: tuple[float, float] | None,
    ) -> list[dict]:
        """
        Build the candidate payload for the LLM prompt.

        Pre-computes distance_km for each candidate using geo_service.
        Includes next 2-3 available slot timestamps for grounded reasoning.
        """
        payloads = []
        for c in candidates:
            distance = None
            if user_location:
                provider_loc = (c["lat"], c["lng"])
                distance = round(get_distance_km(user_location, provider_loc), 1)

            # Include next 2-3 slot timestamps for grounded reasoning
            slots = c.get("available_slots", [])
            next_slots = slots[:3] if slots else []

            payloads.append({
                "provider_id": c["id"],
                "name": c["name"],
                "category": c["category"],
                "sector": c["sector"],
                "rating": c["rating"],
                "rating_count": c["rating_count"],
                "price_range": c["price_range"],
                "available_slot_count": len(slots),
                "next_available_slots": next_slots,
                "verified": c["verified"],
                "languages_spoken": c["languages_spoken"],
                "bio": c["bio"],
                "years_experience": c["years_experience"],
                "cultural_background": c.get("cultural_background"),
                "distance_km": distance,
            })
        return payloads

    def _build_prompt(
        self,
        intent: dict,
        candidate_payloads: list[dict],
    ) -> str:
        """Build the full prompt string sent to the LLM."""
        intent_summary = {
            "raw_input": intent.get("raw_input"),
            "service_type": intent.get("service_type"),
            "location_sector": intent.get("location_sector"),
            "requested_time": intent.get("requested_time"),
            "urgency": intent.get("urgency"),
            "detected_language": intent.get("detected_language"),
            "formality_level": intent.get("formality_level"),
            "literacy_register": intent.get("literacy_register"),
            "code_switching": intent.get("code_switching"),
            "constraints": intent.get("constraints"),
        }

        return (
            f"{RANKING_SYSTEM_PROMPT}\n\n"
            f"---\n\n"
            f"## User Intent\n"
            f"```json\n{json.dumps(intent_summary, indent=2, ensure_ascii=False)}\n```\n\n"
            f"## Candidate Providers\n"
            f"```json\n{json.dumps(candidate_payloads, indent=2, ensure_ascii=False)}\n```"
        )

    async def run(self, candidates: list[dict], intent: dict) -> dict:
        """
        Rank candidate providers using LLM reasoning.

        Args:
            candidates: List of provider dicts from DiscoveryAgent.
            intent: Structured intent dict from IntentAgent.

        Returns:
            Dict with 'top_3' ranked list and 'rejected' list,
            each with natural-language reasoning.
        """
        # ── Pre-compute distances ────────────────────────────────────────
        user_location = resolve_user_location(
            intent.get("location_sector"),
            intent.get("home_city"),
        )
        candidate_payloads = self._build_candidate_payload(
            candidates, user_location
        )

        prompt = self._build_prompt(intent, candidate_payloads)

        start_time = time.time()

        # ── LLM call with retry on 429/503 ───────────────────────────────
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RankingResult,
                        temperature=0.3,
                    ),
                )
                break
            except Exception as e:
                error_str = str(e)
                if ("429" in error_str or "503" in error_str) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    time.sleep(wait_time)
                    continue
                raise

        latency_ms = (time.time() - start_time) * 1000
        raw_response_text = response.text

        # ── Parse the JSON response ──────────────────────────────────────
        try:
            parsed = json.loads(raw_response_text)
        except json.JSONDecodeError:
            parsed = {
                "top_3": [],
                "rejected": [],
            }

        # ── Write trace file ─────────────────────────────────────────────
        trace_file = write_ranking_trace(
            intent_input=intent,
            candidates_with_distances=candidate_payloads,
            prompt_sent=prompt,
            raw_llm_response=raw_response_text,
            parsed_output=parsed,
            model_name=self.model_name,
            latency_ms=latency_ms,
        )

        result = dict(parsed)
        result["_trace_file"] = trace_file

        return result
