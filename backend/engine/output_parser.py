# output_parser.py -- Parse LLM JSON output into hypothesis objects.
# Depends on: schemas/hypothesis.py, schemas/scoring.py
# Depended on by: api/pipeline.py
#
# Handles both generation output (creates new hypotheses) and
# elimination output (updates existing hypotheses with status + notes).
# Validates schema with clear error messages for malformed input.
from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime
from typing import Any


class ParseError(Exception):
    """Raised when LLM output doesn't match expected schema."""

    def __init__(self, message: str, raw_input: str = "", field_errors: list[str] | None = None):
        self.message = message
        self.raw_input = raw_input[:500] if raw_input else ""
        self.field_errors = field_errors or []
        super().__init__(message)


def parse_generation_output(
    raw_json: str,
    run_id: str,
) -> list[dict[str, Any]]:
    """Parse generation pass JSON output into hypothesis dicts.

    Returns a list of hypothesis dicts ready for DB insertion.
    Raises ParseError with specific field-level messages on failure.
    """
    data = _extract_json_array(raw_json)
    if not data:
        raise ParseError(
            "Expected a JSON array of hypothesis objects. Got empty or non-array input.",
            raw_input=raw_json,
        )

    hypotheses = []
    field_errors = []

    for i, item in enumerate(data):
        errors = _validate_generation_item(item, i)
        if errors:
            field_errors.extend(errors)
            continue

        # Generate hypothesis ID: H-YYYY-DDD-NN
        today = date.today()
        day_of_year = today.timetuple().tm_yday
        seq = len(hypotheses) + 1
        h_id = f"H-{today.year}-{day_of_year:03d}-{seq:02d}"

        source_theory = item.get("theory_id", "")
        source_theories = item.get("source_theories", [source_theory])
        if source_theory and source_theory not in source_theories:
            source_theories = [source_theory] + source_theories

        hypothesis = {
            "id": h_id,
            "run_id": run_id,
            "short_name": item["short_name"],
            "full_statement": item.get("full_statement", item.get("mechanism", "")),
            "source_theory": source_theory,
            "source_theories": json.dumps(source_theories),
            "status": "SURVIVED",  # all start as survived; elimination updates this
            "conviction": None,  # set by conviction scoring
            "conviction_math": None,
            "hard_falsifiers": json.dumps(_normalize_hard_falsifiers(item.get("hard_falsifiers", []))),
            "soft_falsifiers": json.dumps(_normalize_soft_falsifiers(item.get("soft_falsifiers", []))),
            "predicted_assets": json.dumps(item.get("predicted_assets", [])),
            "asset_direction": json.dumps(item.get("asset_direction", {})),
            "timeframe": item.get("timeframe", ""),
            "elimination_notes": "",
            "generated_date": today.isoformat(),
        }

        # Stash conviction inputs for later scoring
        hypothesis["_conviction_inputs"] = item.get("conviction_inputs", {})

        hypotheses.append(hypothesis)

    if field_errors and not hypotheses:
        raise ParseError(
            f"All {len(data)} hypotheses had validation errors.",
            raw_input=raw_json,
            field_errors=field_errors,
        )

    return hypotheses


def parse_elimination_output(
    raw_json: str,
    existing_hypotheses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Parse elimination pass JSON output and merge with existing hypotheses.

    Updates status, elimination_notes, soft falsifier states, and conviction inputs.
    Returns updated hypothesis dicts.
    """
    data = _extract_json_array(raw_json)
    if not data:
        raise ParseError(
            "Expected a JSON array of elimination results. Got empty or non-array input.",
            raw_input=raw_json,
        )

    # Build lookup by various keys the LLM might use
    existing_by_id = {}
    existing_by_index = {}
    existing_by_name = {}
    for i, h in enumerate(existing_hypotheses):
        existing_by_id[h.get("id", "")] = h
        existing_by_index[str(i)] = h
        existing_by_name[h.get("short_name", "").lower().strip()] = h

    updated = []
    for i, item in enumerate(data):
        # Match to existing hypothesis
        matched = None

        # Try hypothesis_id first
        h_id = item.get("hypothesis_id", "")
        if h_id and h_id in existing_by_id:
            matched = existing_by_id[h_id]
        elif str(h_id) in existing_by_index:
            matched = existing_by_index[str(h_id)]

        # Try by index
        if not matched and str(i) in existing_by_index:
            matched = existing_by_index[str(i)]

        # Try by short_name
        if not matched:
            name = item.get("short_name", "").lower().strip()
            if name and name in existing_by_name:
                matched = existing_by_name[name]

        if not matched:
            # If we can't match, use index-based matching as last resort
            if i < len(existing_hypotheses):
                matched = existing_hypotheses[i]
            else:
                continue

        # Update the hypothesis
        status = item.get("status", "SURVIVED").upper()
        if status not in ("SURVIVED", "WOUNDED", "KILLED"):
            status = "SURVIVED"

        matched["status"] = status
        matched["elimination_notes"] = item.get("elimination_notes", "")

        # Update soft falsifier states from elimination output
        sf_check = item.get("soft_falsifier_check", {})
        triggered_names = set(n.lower() for n in sf_check.get("triggered", []))
        if triggered_names:
            existing_sf = json.loads(matched.get("soft_falsifiers", "[]"))
            for sf in existing_sf:
                if sf.get("name", "").lower() in triggered_names:
                    sf["status"] = "TRIGGERED"
            matched["soft_falsifiers"] = json.dumps(existing_sf)

        # Store conviction inputs from elimination
        matched["_conviction_inputs"] = item.get("conviction_inputs", {})

        updated.append(matched)

    # Include any hypotheses not in elimination output (shouldn't happen, but be safe)
    updated_ids = {h.get("id") for h in updated}
    for h in existing_hypotheses:
        if h.get("id") not in updated_ids:
            updated.append(h)

    return updated


def _extract_json_array(raw: str) -> list[dict] | None:
    """Extract a JSON array from potentially noisy LLM output.

    Handles: raw JSON, JSON in code blocks, JSON with surrounding text.
    """
    raw = raw.strip()

    # Try direct parse first
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Try extracting from code blocks
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if code_block:
        try:
            result = json.loads(code_block.group(1).strip())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Try finding the outermost array brackets
    start = raw.find("[")
    end = raw.rfind("]")
    if start >= 0 and end > start:
        try:
            result = json.loads(raw[start : end + 1])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    return None


def _validate_generation_item(item: dict, index: int) -> list[str]:
    """Validate a single generation output item. Returns list of error messages."""
    errors = []
    prefix = f"Hypothesis {index + 1}"

    if not isinstance(item, dict):
        return [f"{prefix}: Expected object, got {type(item).__name__}"]

    required = ["short_name", "theory_id"]
    for field in required:
        if not item.get(field):
            errors.append(f"{prefix}: Missing required field '{field}'")

    if not item.get("predicted_assets") and not item.get("asset_direction"):
        errors.append(f"{prefix}: Must specify predicted_assets or asset_direction")

    return errors


def _normalize_hard_falsifiers(items: list) -> list[dict]:
    """Normalize hard falsifier items to consistent schema."""
    result = []
    for item in items:
        if isinstance(item, str):
            result.append({"condition": item, "status": "passed", "detail": ""})
        elif isinstance(item, dict):
            result.append({
                "condition": item.get("condition", str(item)),
                "status": "passed",
                "detail": "",
                "metric": item.get("metric", ""),
                "threshold": item.get("threshold", ""),
            })
    return result


def _normalize_soft_falsifiers(items: list) -> list[dict]:
    """Normalize soft falsifier items to consistent schema."""
    result = []
    for item in items:
        if isinstance(item, dict):
            severity = item.get("severity", "minor").lower()
            if severity not in ("minor", "medium", "major"):
                severity = "minor"
            result.append({
                "name": item.get("name", item.get("condition", "Unknown")),
                "severity": severity,
                "status": "clear",
                "metric": str(item.get("metric", "")),
                "threshold": str(item.get("threshold", "")),
                "condition": item.get("condition", ""),
            })
    return result
