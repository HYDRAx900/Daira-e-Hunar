"""
Trace writer — writes structured, human-readable JSON trace files
for every agent invocation.

Trace files are the primary graded deliverable for judges.
Each file captures the full prompt→response→parse pipeline.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.config import TRACE_DIR


def write_intent_trace(
    user_input: str,
    prompt_sent: str,
    raw_llm_response: str,
    parsed_output: dict,
    model_name: str,
    latency_ms: float,
) -> str:
    """
    Write a trace file for an Intent Agent invocation.

    Args:
        user_input:       The raw user text.
        prompt_sent:      Full prompt string sent to the LLM.
        raw_llm_response: Raw text response from the LLM.
        parsed_output:    The structured dict parsed from the LLM response.
        model_name:       Model identifier (e.g. "gemini-2.5-flash").
        latency_ms:       Round-trip latency in milliseconds.

    Returns:
        Relative path to the trace file (e.g. "trace/intent_20260515T120530Z.json").
    """
    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    ts_str = timestamp.strftime("%Y%m%dT%H%M%SZ")
    filename = f"intent_{ts_str}.json"

    # ── Build human-readable summary line ────────────────────────────────
    summary = _build_summary(parsed_output)

    trace_data = {
        "trace_type": "intent_agent",
        "timestamp": timestamp.isoformat(),
        "model": model_name,
        "latency_ms": round(latency_ms, 1),
        "input": {
            "user_text": user_input,
        },
        "prompt_sent_to_llm": prompt_sent,
        "raw_llm_response": raw_llm_response,
        "parsed_output": parsed_output,
        "summary": summary,
    }

    trace_path = TRACE_DIR / filename
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, indent=2, ensure_ascii=False)

    # Return relative path from project root
    return f"trace/{filename}"


def _build_summary(parsed: dict) -> str:
    """
    Generate a one-line human-readable summary of the intent parse result.

    Examples:
        "Parsed roman_urdu request -> AC Technician in G-13, tomorrow morning, confidence 0.95"
        "Needs clarification: Could you specify which sector you need the electrician in?"
    """
    if parsed.get("needs_clarification"):
        question = parsed.get("clarification_question", "Ambiguous input")
        lang = parsed.get("detected_language", "unknown")
        stype = parsed.get("service_type", "unknown service")
        conf = parsed.get("confidence", 0.0)
        return (
            f"[CLARIFICATION NEEDED] {lang} input -> {stype}, "
            f"confidence {conf:.2f}. Question: {question}"
        )

    lang = parsed.get("detected_language", "unknown")
    stype = parsed.get("service_type", "unknown")
    sector = parsed.get("location_sector", "unspecified location")
    time = parsed.get("requested_time", "flexible timing")
    conf = parsed.get("confidence", 0.0)

    return (
        f"Parsed {lang} request -> {stype} in {sector}, "
        f"{time}, confidence {conf:.2f}"
    )
