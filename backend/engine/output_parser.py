# output_parser.py -- Parse LLM JSON output into hypothesis objects.
# Depends on: schemas/hypothesis.py, schemas/scoring.py
# Depended on by: api/pipeline.py
#
# DESIGN PRINCIPLE: Be maximally tolerant of LLM output variations.
# Never reject a hypothesis over a missing display field — default it.
# Only reject if the data is completely unparseable (not JSON, not an array).
from __future__ import annotations

import json
import re
from datetime import date
from typing import Any


class ParseError(Exception):
    """Raised when LLM output doesn't match expected schema."""

    def __init__(self, message: str, raw_input: str = "", field_errors: list[str] | None = None):
        self.message = message
        self.raw_input = raw_input[:500] if raw_input else ""
        self.field_errors = field_errors or []
        super().__init__(message)


# ---------------------------------------------------------------------------
# Field name aliases — every reasonable name the LLM might use
# ---------------------------------------------------------------------------
FIELD_ALIASES: dict[str, list[str]] = {
    "short_name": [
        "name", "title", "hypothesis_name", "hypothesis", "hypothesis_title",
        "summary", "label", "short_title",
    ],
    "theory_id": [
        "source_theory", "theory", "theory_module", "module", "module_id",
    ],
    "predicted_assets": [
        "assets", "tickers", "instruments", "etfs", "predicted_tickers",
        "target_assets", "trade_instruments", "exposure", "positions",
        "etf_tickers", "target_etfs", "relevant_assets", "affected_assets",
    ],
    "asset_direction": [
        "direction", "directions", "asset_directions", "trade_direction",
        "position_direction", "long_short", "side", "sides",
        "directional_view", "directional_views",
    ],
    "full_statement": [
        "statement", "mechanism", "description", "thesis", "rationale",
        "full_description", "hypothesis_statement", "explanation",
        "causal_chain", "narrative",
    ],
    "hard_falsifiers": [
        "hard_falsifier", "kill_conditions", "hard_kill", "falsifiers_hard",
        "hard_falsifier_conditions",
    ],
    "soft_falsifiers": [
        "soft_falsifier", "wound_conditions", "soft_wound", "falsifiers_soft",
        "soft_falsifier_conditions",
    ],
    "timeframe": [
        "time_frame", "horizon", "time_horizon", "duration", "holding_period",
        "expected_timeframe",
    ],
    "source_theories": [
        "theories", "theory_ids", "source_theory_ids", "contributing_theories",
    ],
    "conviction_inputs": [
        "conviction", "scoring_inputs", "conviction_scoring",
        "epistemic_inputs", "scores",
    ],
}


def _normalize_fields(item: dict) -> None:
    """Apply all field name aliases in-place."""
    for canonical, alternatives in FIELD_ALIASES.items():
        if item.get(canonical):
            continue
        for alt in alternatives:
            if item.get(alt):
                item[canonical] = item.pop(alt)
                break


# ---------------------------------------------------------------------------
# Generation output parsing
# ---------------------------------------------------------------------------

def parse_generation_output(
    raw_json: str,
    run_id: str,
) -> list[dict[str, Any]]:
    """Parse generation pass JSON output into hypothesis dicts.

    Maximally tolerant: normalizes field names, derives missing fields,
    and only skips a hypothesis if it has literally no identifiable name.
    """
    data = _extract_json_array(raw_json)
    if not data:
        raise ParseError(
            "Expected a JSON array of hypothesis objects. Got empty or non-array input.",
            raw_input=raw_json,
        )

    # Format detection: reject elimination output fed to generation import
    if data and isinstance(data[0], dict):
        first = data[0]
        has_elim_keys = any(k in first for k in ("status", "hard_falsifier_check", "elimination_notes"))
        has_gen_keys = any(k in first for k in ("predicted_assets", "asset_direction", "mechanism", "prediction"))
        if has_elim_keys and not has_gen_keys:
            raise ParseError(
                "This looks like elimination output, not generation output. "
                "Check that you are importing into the correct pipeline step.",
                raw_input=raw_json,
            )

    hypotheses = []
    field_errors = []

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            field_errors.append(f"Hypothesis {i+1}: Expected object, got {type(item).__name__}")
            continue

        # Normalize all field names
        _normalize_fields(item)

        # Must have SOME name — this is the one hard requirement
        name = item.get("short_name", "")
        if not name:
            # Last resort: generate a name from theory_id
            theory = item.get("theory_id", "")
            if theory:
                name = f"Hypothesis from {theory}"
                item["short_name"] = name
            else:
                field_errors.append(
                    f"Hypothesis {i+1}: No identifiable name (tried: short_name, name, title, hypothesis). "
                    f"Keys present: {', '.join(sorted(item.keys()))}"
                )
                continue

        # Generate hypothesis ID
        run_ts = run_id.replace("R-", "") if run_id.startswith("R-") else run_id
        seq = len(hypotheses) + 1
        h_id = f"H-{run_ts}-{seq:02d}"

        # Derive theory fields with sensible defaults
        source_theory = item.get("theory_id", "unknown")
        source_theories = item.get("source_theories", [source_theory])
        if isinstance(source_theories, str):
            source_theories = [source_theories]
        if source_theory and source_theory not in source_theories:
            source_theories = [source_theory] + source_theories

        # Derive asset fields — try every possible source
        predicted_assets = _extract_assets(item)
        asset_direction = _extract_directions(item, predicted_assets)

        hypothesis = {
            "id": h_id,
            "run_id": run_id,
            "short_name": name,
            "full_statement": item.get("full_statement", item.get("prediction", "")),
            "source_theory": source_theory,
            "source_theories": json.dumps(source_theories),
            "status": "SURVIVED",
            "conviction": None,
            "conviction_math": None,
            "hard_falsifiers": json.dumps(_normalize_hard_falsifiers(item.get("hard_falsifiers", []))),
            "soft_falsifiers": json.dumps(_normalize_soft_falsifiers(item.get("soft_falsifiers", []))),
            "predicted_assets": json.dumps(predicted_assets),
            "asset_direction": json.dumps(asset_direction),
            "timeframe": item.get("timeframe", ""),
            "elimination_notes": "",
            "generated_date": date.today().isoformat(),
        }

        # Stash conviction inputs for later scoring
        conv = item.get("conviction_inputs", {})
        if isinstance(conv, dict):
            hypothesis["_conviction_inputs"] = conv
        else:
            hypothesis["_conviction_inputs"] = {}

        hypotheses.append(hypothesis)

    if not hypotheses:
        raise ParseError(
            f"Could not parse any hypotheses from {len(data)} items.",
            raw_input=raw_json,
            field_errors=field_errors,
        )

    return hypotheses


def _extract_assets(item: dict) -> list[str]:
    """Extract predicted assets from any plausible field."""
    # Direct field
    assets = item.get("predicted_assets", [])
    if isinstance(assets, list) and assets:
        return assets

    # From asset_direction keys
    directions = item.get("asset_direction", {})
    if isinstance(directions, dict) and directions:
        return list(directions.keys())

    # Search nested structures — Claude sometimes puts assets inside prediction
    for key in ["prediction", "trade", "position", "exposure"]:
        nested = item.get(key, {})
        if isinstance(nested, dict):
            for sub_key in ["assets", "tickers", "instruments", "etfs", "predicted_assets"]:
                val = nested.get(sub_key, [])
                if isinstance(val, list) and val:
                    return val
            for sub_key in ["direction", "directions", "asset_direction"]:
                val = nested.get(sub_key, {})
                if isinstance(val, dict) and val:
                    return list(val.keys())

    return []


def _extract_directions(item: dict, assets: list[str]) -> dict[str, str]:
    """Extract asset directions from any plausible field."""
    directions = item.get("asset_direction", {})
    if isinstance(directions, dict) and directions:
        return directions

    # Search nested
    for key in ["prediction", "trade", "position", "exposure"]:
        nested = item.get(key, {})
        if isinstance(nested, dict):
            for sub_key in ["direction", "directions", "asset_direction"]:
                val = nested.get(sub_key, {})
                if isinstance(val, dict) and val:
                    return val

    # Default: mark all assets as LONG
    if assets:
        return {a: "LONG" for a in assets}

    return {}


# ---------------------------------------------------------------------------
# Elimination output parsing
# ---------------------------------------------------------------------------

def parse_elimination_output(
    raw_json: str,
    existing_hypotheses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Parse elimination pass JSON output and merge with existing hypotheses."""
    data = _extract_json_array(raw_json)
    if not data:
        raise ParseError(
            "Expected a JSON array of elimination results. Got empty or non-array input.",
            raw_input=raw_json,
        )

    # Format detection: reject generation output fed to elimination import
    if data and isinstance(data[0], dict):
        first = data[0]
        has_gen_keys = any(k in first for k in ("predicted_assets", "asset_direction", "mechanism"))
        has_elim_keys = any(k in first for k in ("status", "hard_falsifier_check", "elimination_notes"))
        if has_gen_keys and not has_elim_keys:
            raise ParseError(
                "This looks like generation output, not elimination output. "
                "Check that you are importing into the correct pipeline step.",
                raw_input=raw_json,
            )

    # Build lookup by various keys
    existing_by_id = {}
    existing_by_index = {}
    existing_by_name = {}
    for i, h in enumerate(existing_hypotheses):
        existing_by_id[h.get("id", "")] = h
        existing_by_index[str(i)] = h
        existing_by_name[h.get("short_name", "").lower().strip()] = h

    updated = []
    for i, item in enumerate(data):
        _normalize_fields(item)

        matched = None

        # Try hypothesis_id / id
        h_id = item.get("hypothesis_id", item.get("id", ""))
        if h_id and h_id in existing_by_id:
            matched = existing_by_id[h_id]

        # Try by short_name
        if not matched:
            name = item.get("short_name", "").lower().strip()
            if name and name in existing_by_name:
                matched = existing_by_name[name]

        # Try by index
        if not matched and i < len(existing_hypotheses):
            matched = existing_hypotheses[i]

        if not matched:
            continue

        # Update status
        status = item.get("status", "SURVIVED").upper()
        if status not in ("SURVIVED", "WOUNDED", "KILLED"):
            status = "SURVIVED"

        matched["status"] = status
        matched["elimination_notes"] = item.get("elimination_notes", item.get("notes", item.get("reasoning", "")))

        # Update soft falsifier states — robust matching with fallback
        sf_updates = item.get("soft_falsifiers", item.get("soft_falsifier_check", {}))
        existing_sf = json.loads(matched.get("soft_falsifiers", "[]"))

        if isinstance(sf_updates, dict):
            triggered_names = [n.lower().strip() for n in sf_updates.get("triggered", [])]
            triggered_count = sf_updates.get("triggered_count", len(triggered_names))

            if triggered_names or triggered_count > 0:
                matched_count = 0
                # Try matching by name, condition, or substring
                for sf in existing_sf:
                    sf_name = sf.get("name", "").lower().strip()
                    sf_cond = sf.get("condition", "").lower().strip()
                    for tn in triggered_names:
                        if (tn == sf_name or tn == sf_cond
                                or tn in sf_name or tn in sf_cond
                                or sf_name in tn or sf_cond in tn):
                            sf["status"] = "TRIGGERED"
                            matched_count += 1
                            break

                # Fallback: if triggered_count > matched, mark remaining by severity (worst first)
                if matched_count < triggered_count:
                    remaining = triggered_count - matched_count
                    severity_order = {"major": 0, "medium": 1, "minor": 2}
                    unmatched = [sf for sf in existing_sf if sf.get("status") != "TRIGGERED"]
                    unmatched.sort(key=lambda x: severity_order.get(x.get("severity", "minor"), 2))
                    for sf in unmatched[:remaining]:
                        sf["status"] = "TRIGGERED"

        elif isinstance(sf_updates, list):
            for sf_item in sf_updates:
                if isinstance(sf_item, dict) and sf_item.get("status", "").upper() == "TRIGGERED":
                    name = sf_item.get("name", sf_item.get("id", "")).lower().strip()
                    for sf in existing_sf:
                        sf_name = sf.get("name", "").lower().strip()
                        sf_cond = sf.get("condition", "").lower().strip()
                        if (name == sf_name or name == sf_cond
                                or name in sf_name or name in sf_cond
                                or sf_name in name or sf_cond in name):
                            sf["status"] = "TRIGGERED"
                            break

        matched["soft_falsifiers"] = json.dumps(existing_sf)

        # Store conviction inputs
        matched["_conviction_inputs"] = item.get("conviction_inputs", {})

        updated.append(matched)

    # Include unmatched hypotheses as-is
    updated_ids = {h.get("id") for h in updated}
    for h in existing_hypotheses:
        if h.get("id") not in updated_ids:
            updated.append(h)

    return updated


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------

def _normalize_hard_falsifiers(items: list) -> list[dict]:
    """Normalize hard falsifier items to consistent schema."""
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if isinstance(item, str):
            result.append({"condition": item, "status": "passed", "detail": "", "metric": "", "threshold": ""})
        elif isinstance(item, dict):
            result.append({
                "condition": item.get("condition", item.get("description", str(item))),
                "status": "passed",
                "detail": "",
                "metric": str(item.get("metric", "")),
                "threshold": str(item.get("threshold", "")),
            })
    return result


def _normalize_soft_falsifiers(items: list) -> list[dict]:
    """Normalize soft falsifier items to consistent schema."""
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if isinstance(item, str):
            result.append({
                "name": item, "severity": "minor", "status": "clear",
                "metric": "", "threshold": "", "condition": item,
            })
        elif isinstance(item, dict):
            severity = str(item.get("severity", "minor")).lower()
            if severity not in ("minor", "medium", "major"):
                severity = "minor"
            name = item.get("name", item.get("condition", item.get("description", "Unknown")))
            result.append({
                "name": name,
                "severity": severity,
                "status": "clear",
                "metric": str(item.get("metric", "")),
                "threshold": str(item.get("threshold", "")),
                "condition": item.get("condition", name),
            })
    return result
