"""
Action Agent — Performs the booking action and generates follow-up tasks.

Responsibilities:
  - Given a selected provider and intent, perform the BOOKING SIMULATION.
  - Handle race conditions, no slots, zero candidates.
  - Atomic reservation of slots.
"""

import os
import json
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional, Tuple
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

from backend.config import MOCK_DATA_DIR, TRACE_DIR
from backend.services.trace_writer import write_action_trace

class ConfirmationMessage(BaseModel):
    text: str = Field(description="The confirmation or fallback message in the requested tone and language")
    language: str = Field(description="Language of the message (e.g. 'english', 'urdu', 'roman_urdu')")

class BookingResult(BaseModel):
    status: Literal["confirmed", "no_provider", "no_slots_available", "slot_taken", "needs_clarification"]
    booking_id: str | None = None
    provider_id: str | None = None
    provider_name: str | None = None
    scheduled_datetime: str | None = None
    confirmation_message: str | None = None
    confirmation_language: str | None = None
    time_negotiated: bool = False
    followups_scheduled: list[str] = Field(default_factory=list)
    receipt_path: str | None = None
    error_reason: str | None = None


CONFIRMATION_SYSTEM_PROMPT = """You are Daira-e-Hunar's Action Agent.
Your job is to write a short confirmation message for a booked service.

TONE MIRRORING:
- Formality: {formality} (can be formal, casual, or slang)
- Language: {language}
- Code-switching: {code_switched}

If time was negotiated (requested time didn't match available slots), mention the new time gracefully.
Keep it under 3 sentences. Be polite. Use the provider's name and the scheduled time.

Example for Roman Urdu casual slang:
"Bhai, tumhara AC Technician {provider} book ho gaya hai {time} ke liye. Koi masla ho to batana."
"""

NO_PROVIDER_SYSTEM_PROMPT = """You are Daira-e-Hunar's Action Agent.
Your job is to write a polite message explaining that no providers could be found for the requested service.

TONE MIRRORING:
- Formality: {formality}
- Language: {language}
- Code-switching: {code_switched}

Keep it to 1-2 sentences. Apologize gracefully.
"""


class ActionAgent:
    def __init__(self):
        # Allow injecting a client if needed, otherwise read from env
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = "gemini-2.5-flash"

    async def run(self, intent: dict, ranking: dict, selected_provider_id: str | None = None) -> dict:
        start_time = datetime.now()
        
        # Short circuits from orchestrator
        if intent.get("needs_clarification"):
            # If the orchestrator passes this down, handle it (though orchestrator might handle it itself)
            result = BookingResult(status="needs_clarification", error_reason="Intent needs clarification")
            latency = (datetime.now() - start_time).total_seconds() * 1000
            tpath = write_action_trace(intent, None, None, None, None, None, result.model_dump(), latency)
            res = result.model_dump()
            res["_trace_file"] = tpath
            return res

        if not ranking.get("top_3"):
            # Zero candidates -> generate no provider message
            msg, lang, prompt, raw = await self._generate_no_provider_message(intent)
            result = BookingResult(
                status="no_provider", 
                confirmation_message=msg,
                confirmation_language=lang,
                error_reason="No candidates found in discovery/ranking"
            )
            latency = (datetime.now() - start_time).total_seconds() * 1000
            tpath = write_action_trace(intent, None, None, None, prompt, raw, result.model_dump(), latency)
            res = result.model_dump()
            res["_trace_file"] = tpath
            return res

        if not selected_provider_id:
            selected_provider_id = ranking["top_3"][0]["provider_id"]

        providers = self._load_providers()
        provider = self._find_provider(providers, selected_provider_id)
        
        if not provider:
            result = BookingResult(status="no_provider", error_reason=f"Provider {selected_provider_id} not found in mock data")
            latency = (datetime.now() - start_time).total_seconds() * 1000
            tpath = write_action_trace(intent, None, None, None, None, None, result.model_dump(), latency)
            res = result.model_dump()
            res["_trace_file"] = tpath
            return res

        slot_chosen, time_negotiated = self._select_slot(provider, intent)
        if not slot_chosen:
            result = BookingResult(status="no_slots_available", error_reason="Provider has zero available slots")
            latency = (datetime.now() - start_time).total_seconds() * 1000
            tpath = write_action_trace(intent, provider, None, None, None, None, result.model_dump(), latency)
            res = result.model_dump()
            res["_trace_file"] = tpath
            return res

        race_check = self._race_check_and_reserve(selected_provider_id, slot_chosen)
        if not race_check:
            result = BookingResult(status="slot_taken", error_reason="Slot was reserved by another process")
            latency = (datetime.now() - start_time).total_seconds() * 1000
            tpath = write_action_trace(intent, provider, slot_chosen, False, None, None, result.model_dump(), latency)
            res = result.model_dump()
            res["_trace_file"] = tpath
            return res

        # Success path
        booking_id = f"B{uuid.uuid4().hex[:8].upper()}"
        
        booking_data = {
            "booking_id": booking_id,
            "provider_id": provider["id"],
            "provider_name": provider["name"],
            "scheduled_datetime": slot_chosen,
            "time_negotiated": time_negotiated,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        self._write_booking(booking_data)
        followup_ids = self._write_followups(booking_id, slot_chosen)
        
        msg, lang, prompt, raw = await self._generate_confirmation(intent, provider, slot_chosen, time_negotiated)
        
        receipt_path = self._write_receipt(booking_id, booking_data, msg, followup_ids)

        result = BookingResult(
            status="confirmed",
            booking_id=booking_id,
            provider_id=provider["id"],
            provider_name=provider["name"],
            scheduled_datetime=slot_chosen,
            confirmation_message=msg,
            confirmation_language=lang,
            time_negotiated=time_negotiated,
            followups_scheduled=followup_ids,
            receipt_path=receipt_path
        )
        
        latency = (datetime.now() - start_time).total_seconds() * 1000
        tpath = write_action_trace(intent, provider, slot_chosen, True, prompt, raw, result.model_dump(), latency)
        
        res = result.model_dump()
        res["_trace_file"] = tpath
        return res

    def _load_providers(self) -> list[dict]:
        path = os.path.join(MOCK_DATA_DIR, "providers.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _find_provider(self, providers: list[dict], provider_id: str) -> dict | None:
        for p in providers:
            if p["id"] == provider_id:
                return p
        return None

    def _select_slot(self, provider: dict, intent: dict) -> Tuple[str | None, bool]:
        slots = provider.get("available_slots", [])
        if not slots:
            return None, False

        req_time = (intent.get("requested_time") or "").lower()
        urgency = (intent.get("urgency") or "").lower()

        # Mock current time as roughly the start of the slot window for demo purposes, 
        # or just parse slots and find the first matching one.
        # Since slots are ISO strings, we can sort them.
        slots.sort()
        
        target_hours = None
        if "morning" in req_time:
            target_hours = range(6, 12)
        elif "afternoon" in req_time:
            target_hours = range(12, 17)
        elif "evening" in req_time:
            target_hours = range(17, 22)

        # For "today" or "this_week", we normally check against current date.
        # But mock data is fixed to May 20-28 2026. 
        # So we just match by hours if specified, otherwise grab the earliest.
        # We'll try to find a slot matching target_hours first.
        
        if target_hours:
            for s in slots:
                try:
                    dt = datetime.fromisoformat(s)
                    if dt.hour in target_hours:
                        return s, False
                except ValueError:
                    continue
        
        # If no slot matches the specific hours (or no hours specified), take the earliest.
        # We consider it negotiated if target_hours was specified and we didn't match it,
        # or if urgency="now" / "today" and the slot is tomorrow or later (hard to compute exactly without fixing a mock current date, so we'll just set it true if target_hours failed).
        time_negotiated = bool(target_hours)
        
        return slots[0], time_negotiated

    def _race_check_and_reserve(self, provider_id: str, chosen_slot: str) -> bool:
        path = os.path.join(MOCK_DATA_DIR, "providers.json")
        tmp_path = path + ".tmp"
        
        # Atomic read and write
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            found = False
            for p in data:
                if p["id"] == provider_id:
                    if chosen_slot in p.get("available_slots", []):
                        p["available_slots"].remove(chosen_slot)
                        found = True
                    break
            
            if not found:
                return False
                
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            os.replace(tmp_path, path)
            return True
            
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return False

    def _write_booking(self, booking_data: dict) -> None:
        path = os.path.join(MOCK_DATA_DIR, "bookings.json")
        data = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data.append(booking_data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _write_followups(self, booking_id: str, scheduled_datetime: str) -> list[str]:
        path = os.path.join(MOCK_DATA_DIR, "followups.json")
        data = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
        try:
            dt = datetime.fromisoformat(scheduled_datetime)
            remind_time = dt - timedelta(hours=1)
            rate_time = dt + timedelta(hours=2)
        except ValueError:
            # Fallback if unparseable
            remind_time = datetime.now()
            rate_time = datetime.now()
            
        f1 = f"F{uuid.uuid4().hex[:8].upper()}"
        f2 = f"F{uuid.uuid4().hex[:8].upper()}"
        
        data.append({
            "followup_id": f1,
            "booking_id": booking_id,
            "type": "reminder",
            "trigger_time": remind_time.isoformat()
        })
        data.append({
            "followup_id": f2,
            "booking_id": booking_id,
            "type": "rating_prompt",
            "trigger_time": rate_time.isoformat()
        })
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return [f1, f2]

    def _write_receipt(self, booking_id: str, booking_data: dict, text: str, followups: list[str]) -> str:
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"receipt_{booking_id}.txt"
        path = TRACE_DIR / filename
        
        content = f"BOOKING RECEIPT: {booking_id}\n"
        content += "=" * 40 + "\n"
        content += f"Provider: {booking_data['provider_name']} ({booking_data['provider_id']})\n"
        content += f"Time: {booking_data['scheduled_datetime']}\n"
        content += f"Negotiated: {booking_data['time_negotiated']}\n"
        content += "-" * 40 + "\n"
        content += f"Message sent to user:\n{text}\n"
        content += "-" * 40 + "\n"
        content += f"Followups scheduled: {', '.join(followups)}\n"
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"trace/{filename}"

    async def _generate_no_provider_message(self, intent: dict) -> Tuple[str, str, str, str]:
        if not self.client:
            return "Sorry, no providers found.", "english", "No LLM Client", "{}"

        formality = intent.get("formality_level", "casual")
        language = intent.get("detected_language", "english")
        code_switched = intent.get("code_switching", False)
        
        prompt = NO_PROVIDER_SYSTEM_PROMPT.format(
            formality=formality,
            language=language,
            code_switched=code_switched
        )
        
        return await self._call_llm_with_retry(prompt)

    async def _generate_confirmation(self, intent: dict, provider: dict, scheduled_datetime: str, time_negotiated: bool) -> Tuple[str, str, str, str]:
        if not self.client:
            return "Booking confirmed.", "english", "No LLM Client", "{}"

        formality = intent.get("formality_level", "casual")
        language = intent.get("detected_language", "english")
        code_switched = intent.get("code_switching", False)
        
        prompt = CONFIRMATION_SYSTEM_PROMPT.format(
            formality=formality,
            language=language,
            code_switched=code_switched,
            provider=provider["name"],
            time=scheduled_datetime
        )
        if time_negotiated:
            prompt += "\nNote: We had to negotiate the time because their preferred time was unavailable. Mention the new time politely."
            
        return await self._call_llm_with_retry(prompt)

    async def _call_llm_with_retry(self, prompt: str) -> Tuple[str, str, str, str]:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ConfirmationMessage,
                        temperature=0.3
                    )
                )
                
                raw = response.text
                try:
                    parsed = json.loads(raw)
                    return parsed.get("text", "Confirmed"), parsed.get("language", "english"), prompt, raw
                except json.JSONDecodeError:
                    return "Confirmed", "english", prompt, raw
            except Exception as e:
                if "429" in str(e) or "503" in str(e):
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5 * (attempt + 1))
                        continue
                return "Confirmed (error)", "english", prompt, str(e)
                
        return "Confirmed (timeout)", "english", prompt, "timeout"
