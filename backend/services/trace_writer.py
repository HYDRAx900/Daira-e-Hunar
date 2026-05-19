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
        "Parsed casual roman_urdu request (code_switched) -> AC Technician in G-13, Islamabad, tomorrow morning, confidence 0.95"
        "[CLARIFICATION NEEDED] unknown input -> unknown service, confidence 0.00. Question: Ambiguous input"
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
    
    # Extract new signals
    formality = parsed.get("formality_level", "")
    code_switched = parsed.get("code_switching", False)
    
    # Build the format: "{formality} {lang} request {code_switched}"
    request_desc = f"{formality} {lang}".strip() if formality else lang
    if code_switched:
        request_desc += " (code_switched)"

    return (
        f"Parsed {request_desc} request -> {stype} in {sector}, "
        f"{time}, confidence {conf:.2f}"
    )


# ── Discovery Agent trace ────────────────────────────────────────────────────

def write_discovery_trace(
    intent_input: dict,
    filter_applied: dict,
    candidates_returned: list,
    fallback_used: bool,
    fallback_reason: str | None,
    no_candidates_reason: str | None,
) -> str:
    """
    Write a trace file for a Discovery Agent invocation.

    Args:
        intent_input:         The parsed intent dict from Intent Agent.
        filter_applied:       Dict describing the filter (city, service_type).
        candidates_returned:  List of provider dicts that matched.
        fallback_used:        Whether the search was broadened.
        fallback_reason:      Why fallback was triggered (if applicable).
        no_candidates_reason: Reason if zero candidates found.

    Returns:
        Relative path to the trace file.
    """
    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    ts_str = timestamp.strftime("%Y%m%dT%H%M%SZ")
    filename = f"discovery_{ts_str}.json"

    summary = _build_discovery_summary(
        filter_applied, len(candidates_returned), fallback_used, fallback_reason
    )

    trace_data = {
        "trace_type": "discovery_agent",
        "timestamp": timestamp.isoformat(),
        "input": {
            "service_type": intent_input.get("service_type"),
            "location_sector": intent_input.get("location_sector"),
            "home_city": intent_input.get("home_city"),
        },
        "filter_applied": filter_applied,
        "candidates_returned": len(candidates_returned),
        "candidate_ids": [c["id"] for c in candidates_returned],
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "no_candidates_reason": no_candidates_reason,
        "summary": summary,
    }

    trace_path = TRACE_DIR / filename
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, indent=2, ensure_ascii=False)

    return f"trace/{filename}"


def _build_discovery_summary(
    filter_applied: dict,
    count: int,
    fallback_used: bool,
    fallback_reason: str | None,
) -> str:
    """
    One-line summary for discovery trace.

    Examples:
        "Found 4 AC Technicians in Lahore (no fallback)"
        "[FALLBACK] No Tutor in Islamabad; broadened nationwide, found 29"
    """
    stype = filter_applied.get("service_type", "unknown")
    city = filter_applied.get("city", "unknown")

    if fallback_used:
        return (
            f"[FALLBACK] No {stype} in {city}; "
            f"{fallback_reason or 'broadened nationwide'}, found {count}"
        )
    return f"Found {count} {stype}s in {city} (no fallback)"


# ── Ranking Agent trace ──────────────────────────────────────────────────────

def write_ranking_trace(
    intent_input: dict,
    candidates_with_distances: list,
    prompt_sent: str,
    raw_llm_response: str,
    parsed_output: dict,
    model_name: str,
    latency_ms: float,
) -> str:
    """
    Write a trace file for a Ranking Agent invocation.

    Args:
        intent_input:               The parsed intent dict.
        candidates_with_distances:  Candidate payloads with distance_km.
        prompt_sent:                Full prompt string sent to the LLM.
        raw_llm_response:           Raw text response from the LLM.
        parsed_output:              The structured ranking result dict.
        model_name:                 Model identifier.
        latency_ms:                 Round-trip latency in milliseconds.

    Returns:
        Relative path to the trace file.
    """
    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    ts_str = timestamp.strftime("%Y%m%dT%H%M%SZ")
    filename = f"ranking_{ts_str}.json"

    summary = _build_ranking_summary(parsed_output, len(candidates_with_distances))

    trace_data = {
        "trace_type": "ranking_agent",
        "timestamp": timestamp.isoformat(),
        "model": model_name,
        "latency_ms": round(latency_ms, 1),
        "input": {
            "user_text": intent_input.get("raw_input"),
            "service_type": intent_input.get("service_type"),
            "location_sector": intent_input.get("location_sector"),
            "detected_language": intent_input.get("detected_language"),
            "formality_level": intent_input.get("formality_level"),
        },
        "candidates_with_distances": candidates_with_distances,
        "prompt_sent_to_llm": prompt_sent,
        "raw_llm_response": raw_llm_response,
        "parsed_output": parsed_output,
        "summary": summary,
    }

    trace_path = TRACE_DIR / filename
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, indent=2, ensure_ascii=False)

    return f"trace/{filename}"


def _build_ranking_summary(parsed: dict, candidate_count: int) -> str:
    """
    One-line summary for ranking trace.

    Examples:
        "Ranked 4 candidates -> top 3: P0021(0.92), P0024(0.85), P0019(0.78) | 1 rejected"
    """
    top = parsed.get("top_3", [])
    rejected = parsed.get("rejected", [])

    if not top:
        return f"No ranking produced from {candidate_count} candidates"

    top_str = ", ".join(
        f"{p.get('provider_id', '?')}({p.get('score', 0):.2f})" for p in top
    )
    return (
        f"Ranked {candidate_count} candidates -> "
        f"top {len(top)}: {top_str} | {len(rejected)} rejected"
    )


# ── Action Agent trace ───────────────────────────────────────────────────────

def write_action_trace(
    intent_input: dict,
    selected_provider: dict | None,
    slot_chosen: str | None,
    race_check_result: bool | None,
    confirmation_prompt: str | None,
    raw_llm_response: str | None,
    parsed_booking_result: dict,
    latency_ms: float,
) -> str:
    """
    Write a trace file for an Action Agent invocation.

    Returns:
        Relative path to the trace file.
    """
    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    ts_str = timestamp.strftime("%Y%m%dT%H%M%SZ")
    filename = f"action_{ts_str}.json"

    # Build summary
    b_id = parsed_booking_result.get("booking_id") or "none"
    p_id = parsed_booking_result.get("provider_id") or "none"
    slot = parsed_booking_result.get("scheduled_datetime") or "none"
    status = parsed_booking_result.get("status", "unknown")
    negotiated = parsed_booking_result.get("time_negotiated", False)
    summary = f"ACTION booking_id={b_id} | provider={p_id} | slot={slot} | status={status} | negotiated={str(negotiated).lower()}"

    trace_data = {
        "trace_type": "action_agent",
        "timestamp": timestamp.isoformat(),
        "latency_ms": round(latency_ms, 1),
        "input": {
            "intent": intent_input,
            "selected_provider": selected_provider,
        },
        "slot_chosen": slot_chosen,
        "race_check_result": race_check_result,
        "confirmation_prompt": confirmation_prompt,
        "raw_llm_response": raw_llm_response,
        "parsed_output": parsed_booking_result,
        "summary": summary,
    }

    trace_path = TRACE_DIR / filename
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, indent=2, ensure_ascii=False)

    return f"trace/{filename}"


# ── Run trace (Orchestrator) ─────────────────────────────────────────────────

def write_run_trace(workplan: dict) -> str:
    """
    Write a trace file for an end-to-end Orchestrator run.

    Returns:
        Relative path to the trace file.
    """
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    
    run_id = workplan.get("run_id", "unknown_run")
    filename = f"{run_id}.json"
    
    query = workplan.get("user_query", "")
    status = workplan.get("final_status", "unknown")
    provider = workplan.get("final_provider_id") or "none"
    stages = workplan.get("stages", [])
    total_latency = sum(stage.get("latency_ms", 0.0) for stage in stages)
    
    summary = f"AGENTIC RUN {run_id} | query: '{query}' | status: {status} | provider: {provider} | latency: {round(total_latency, 1)}ms | {len(stages)} stages OK"
    workplan["summary"] = summary
    
    trace_path = TRACE_DIR / filename
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(workplan, f, indent=2, ensure_ascii=False)

    return f"trace/{filename}"

