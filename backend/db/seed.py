# seed.py -- Load mock data into SQLite for first-run experience.
# Depends on: db/database.py, db/models.py, config.py
# Depended on by: main.py (on_startup if no runs exist)
#
# Creates a complete pipeline run with all 5 stages populated so that
# the Audit Mode shows a full trace and the Ledger has scored hypotheses.
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import MOCK_DATA_DIR
from backend.db.database import SessionLocal
from backend.db.models import Hypothesis, InboxItem, JournalEntry, Run, UserState
from backend.engine.conviction import score_conviction
from backend.schemas.scoring import ConvictionInput


MOCK_RUN_ID = "R-MOCK-20260323"
MOCK_RUN_TIMESTAMP = "2026-03-23T10:00:00"


def seed_if_empty():
    """Check if database is empty and seed with mock data if so."""
    db = SessionLocal()
    try:
        run_count = db.query(Run).count()
        if run_count > 0:
            return False  # Already has data
        return seed_mock_data(db)
    finally:
        db.close()


def seed_mock_data(db: Session) -> bool:
    """Load all mock data files and populate the database."""
    # Load mock files
    gen_output = _load_json("generation_output.json")
    elim_output = _load_json("elimination_output.json")
    activation_scores = _load_json("activation_scores.json")
    inbox_items = _load_json("inbox_items.json")
    journal_entries = _load_json("journal_entries.json")

    if not gen_output or not elim_output:
        return False

    # Create the mock run
    run = Run(
        id=MOCK_RUN_ID,
        timestamp=MOCK_RUN_TIMESTAMP,
        status="complete",
        generation_output=json.dumps(gen_output),
        elimination_output=json.dumps(elim_output),
        activation_scores=json.dumps(activation_scores),
    )
    db.add(run)
    db.flush()  # Flush run first so hypothesis FK references work

    # Build elimination lookup by index
    elim_map = {}
    for item in elim_output:
        idx = item.get("hypothesis_id", -1)
        elim_map[idx] = item

    # Create hypotheses by merging generation + elimination + conviction scoring
    for i, gen_item in enumerate(gen_output):
        elim_item = elim_map.get(i, {})

        h_id = f"H-2026-082-{(i + 1):02d}"
        source_theory = gen_item.get("theory_id", "")
        source_theories = gen_item.get("source_theories", [source_theory])
        status = elim_item.get("status", "SURVIVED")

        # Normalize falsifiers
        hard_f = _normalize_hard_falsifiers(gen_item.get("hard_falsifiers", []), elim_item)
        soft_f = _normalize_soft_falsifiers(gen_item.get("soft_falsifiers", []), elim_item)

        # Run conviction scoring for non-KILLED hypotheses
        conviction_val = 0.0
        conviction_math_json = None

        if status != "KILLED":
            conv_inputs = elim_item.get("conviction_inputs", gen_item.get("conviction_inputs", {}))
            triggered_sf = [{"severity": sf["severity"]} for sf in soft_f if sf.get("status") == "TRIGGERED"]

            # Count overlap (other hypotheses sharing same primary asset)
            primary_assets = gen_item.get("predicted_assets", [])
            primary_asset = primary_assets[0] if primary_assets else ""
            overlap = _count_overlap(primary_asset, gen_output, elim_output, i)

            ci = ConvictionInput(
                hypothesis_id=h_id,
                support_strength=conv_inputs.get("support_strength", 0.5),
                evidence_quality=conv_inputs.get("evidence_quality", 0.5),
                convergence=conv_inputs.get("convergence", 0.3),
                falsifier_clarity=conv_inputs.get("falsifier_clarity", 0.7),
                triggered_soft_falsifiers=triggered_sf,
                overlap_count=overlap,
                horizon_alignment=conv_inputs.get("horizon_alignment", 0.5),
                expression_efficiency=conv_inputs.get("expression_efficiency", 0.5),
            )
            result = score_conviction(ci)
            conviction_val = result.stage3.final
            conviction_math_json = json.dumps(result.model_dump())

        hypothesis = Hypothesis(
            id=h_id,
            run_id=MOCK_RUN_ID,
            short_name=gen_item.get("short_name", ""),
            full_statement=gen_item.get("full_statement", ""),
            source_theory=source_theory,
            source_theories=json.dumps(source_theories),
            status=status,
            conviction=conviction_val,
            conviction_math=conviction_math_json,
            hard_falsifiers=json.dumps(hard_f),
            soft_falsifiers=json.dumps(soft_f),
            predicted_assets=json.dumps(gen_item.get("predicted_assets", [])),
            asset_direction=json.dumps(gen_item.get("asset_direction", {})),
            timeframe=gen_item.get("timeframe", ""),
            elimination_notes=elim_item.get("elimination_notes", ""),
            generated_date="2026-03-23",
        )
        db.add(hypothesis)

    # Flush hypotheses so FK references work for journal/inbox
    db.flush()

    # Create inbox items
    for item in (inbox_items or []):
        inbox = InboxItem(
            id=item["id"],
            date=item["date"],
            type=item["type"],
            content=item["content"],
            source=item.get("source"),
            theories=json.dumps(item.get("theories", [])) if item.get("theories") else None,
            hypothesis_id=item.get("hypothesis_id"),
            status=item.get("status", "queued"),
            incorporated_run_id=MOCK_RUN_ID if item.get("status") == "incorporated" else None,
        )
        db.add(inbox)

    # Create journal entries
    for entry in (journal_entries or []):
        je = JournalEntry(
            id=entry["id"],
            hypothesis_id=entry["hypothesis_id"],
            date=entry["date"],
            action=entry["action"],
            size=entry.get("size"),
            conviction_at_entry=entry.get("conviction_at_entry"),
            reasoning=entry["reasoning"],
            status=entry.get("status", "OPEN"),
            outcome=entry.get("outcome"),
            closed_date=entry.get("closed_date"),
        )
        db.add(je)

    # Set user state
    db.add(UserState(key="last_reviewed_run_id", value=""))
    db.add(UserState(key="is_mock_data", value="true"))

    db.commit()
    return True


def _load_json(filename: str) -> list | dict | None:
    path = MOCK_DATA_DIR / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_hard_falsifiers(gen_falsifiers: list, elim_item: dict) -> list[dict]:
    """Merge generation hard falsifiers with elimination check results."""
    hf_check = elim_item.get("hard_falsifier_check", {})
    any_triggered = hf_check.get("any_triggered", False)

    result = []
    for hf in gen_falsifiers:
        if isinstance(hf, str):
            result.append({"condition": hf, "status": "FAILED" if any_triggered else "passed", "detail": ""})
        elif isinstance(hf, dict):
            result.append({
                "condition": hf.get("condition", ""),
                "status": "FAILED" if any_triggered else "passed",
                "detail": "",
                "metric": hf.get("metric", ""),
                "threshold": hf.get("threshold", ""),
            })
    return result


def _normalize_soft_falsifiers(gen_falsifiers: list, elim_item: dict) -> list[dict]:
    """Merge generation soft falsifiers with elimination check results."""
    sf_check = elim_item.get("soft_falsifier_check", {})
    triggered_names = set(n.lower() for n in sf_check.get("triggered", []))

    result = []
    for sf in gen_falsifiers:
        if isinstance(sf, dict):
            name = sf.get("name", sf.get("condition", "Unknown"))
            severity = sf.get("severity", "minor").lower()
            if severity not in ("minor", "medium", "major"):
                severity = "minor"
            is_triggered = name.lower() in triggered_names
            result.append({
                "name": name,
                "severity": severity,
                "status": "TRIGGERED" if is_triggered else "clear",
                "metric": str(sf.get("metric", "")),
                "threshold": str(sf.get("threshold", "")),
                "condition": sf.get("condition", ""),
            })
    return result


def _count_overlap(primary_asset: str, gen_output: list, elim_output: list, current_idx: int) -> int:
    """Count how many other surviving hypotheses share the same primary asset."""
    if not primary_asset:
        return 0

    elim_map = {item.get("hypothesis_id", -1): item for item in elim_output}
    count = 0
    for j, gen in enumerate(gen_output):
        if j == current_idx:
            continue
        elim = elim_map.get(j, {})
        if elim.get("status", "SURVIVED") == "KILLED":
            continue
        assets = gen.get("predicted_assets", [])
        if primary_asset in assets:
            count += 1
    return count
