# pipeline.py -- Pipeline status, prompt generation, and import endpoints.
# Depends on: db/database.py, db/models.py, engine/prompt_builder.py, engine/output_parser.py,
#             engine/theory_parser.py, engine/activation.py, engine/conviction.py
# Depended on by: main.py (router registration)
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Hypothesis as HypothesisModel
from backend.db.models import InboxItem, Run
from backend.engine import activation, conviction, theory_parser
from backend.engine.output_parser import ParseError, parse_elimination_output, parse_generation_output
from backend.engine.prompt_builder import build_elimination_prompt, build_generation_prompt
from backend.schemas.briefing import BriefingPacket
from backend.schemas.scoring import ConvictionInput

router = APIRouter(tags=["pipeline"])


def _load_briefing() -> dict[str, Any]:
    """Load the latest briefing packet from mock_data or data directory."""
    from backend.config import DATA_DIR, MOCK_DATA_DIR

    # Try real briefing first, fall back to mock
    for path in [DATA_DIR / "briefing_packet.json", MOCK_DATA_DIR / "briefing_packet.json"]:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _get_current_pipeline_state(db: Session) -> dict:
    """Determine the current state of each pipeline step."""
    latest_run = db.query(Run).order_by(desc(Run.timestamp)).first()

    briefing_data = _load_briefing()
    briefing_fresh = bool(briefing_data)
    briefing_timestamp = briefing_data.get("timestamp", "") if briefing_data else ""

    if not latest_run:
        # No runs at all
        return {
            "current_step": 1 if briefing_fresh else 0,
            "run_id": "",
            "briefing_timestamp": briefing_timestamp,
            "steps": [
                {"step": 1, "label": "Data Briefing", "type": "automated", "state": "complete" if briefing_fresh else "ready"},
                {"step": 2, "label": "Activation Scoring", "type": "automated", "state": "waiting"},
                {"step": 3, "label": "Generation Pass", "type": "human-in-loop", "state": "waiting"},
                {"step": 4, "label": "Elimination Pass", "type": "human-in-loop", "state": "waiting"},
                {"step": 5, "label": "Conviction Scoring", "type": "automated", "state": "waiting"},
            ],
        }

    if latest_run.status == "complete":
        # Last run is complete — show all steps as complete, ready for new run
        return {
            "current_step": 5,
            "run_id": latest_run.id,
            "briefing_timestamp": briefing_timestamp,
            "steps": [
                {"step": 1, "label": "Data Briefing", "type": "automated", "state": "complete"},
                {"step": 2, "label": "Activation Scoring", "type": "automated", "state": "complete"},
                {"step": 3, "label": "Generation Pass", "type": "human-in-loop", "state": "complete"},
                {"step": 4, "label": "Elimination Pass", "type": "human-in-loop", "state": "complete"},
                {"step": 5, "label": "Conviction Scoring", "type": "automated", "state": "complete"},
            ],
        }

    # Active run exists
    has_activation = bool(latest_run.activation_scores)
    has_generation = bool(latest_run.generation_output)
    has_elimination = bool(latest_run.elimination_output)

    steps = [
        {"step": 1, "label": "Data Briefing", "type": "automated", "state": "complete"},
        {"step": 2, "label": "Activation Scoring", "type": "automated", "state": "complete" if has_activation else "ready"},
        {"step": 3, "label": "Generation Pass", "type": "human-in-loop",
         "state": "complete" if has_generation else ("ready" if has_activation else "waiting")},
        {"step": 4, "label": "Elimination Pass", "type": "human-in-loop",
         "state": "complete" if has_elimination else ("ready" if has_generation else "waiting")},
        {"step": 5, "label": "Conviction Scoring", "type": "automated",
         "state": "complete" if latest_run.status == "complete" else ("ready" if has_elimination else "waiting")},
    ]

    current = 5
    for s in steps:
        if s["state"] in ("ready", "waiting"):
            current = s["step"]
            break

    return {
        "current_step": current,
        "run_id": latest_run.id,
        "briefing_timestamp": briefing_timestamp,
        "steps": steps,
    }


# --- Run endpoints ---

@router.get("/runs")
def list_runs(db: Session = Depends(get_db)):
    runs = db.query(Run).order_by(desc(Run.timestamp)).all()
    results = []
    for r in runs:
        hyp_count = db.query(HypothesisModel).filter(HypothesisModel.run_id == r.id).count()
        survived = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == r.id, HypothesisModel.status == "SURVIVED"
        ).count()
        wounded = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == r.id, HypothesisModel.status == "WOUNDED"
        ).count()
        killed = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == r.id, HypothesisModel.status == "KILLED"
        ).count()
        results.append({
            "id": r.id,
            "timestamp": r.timestamp,
            "status": r.status,
            "hypotheses_generated": hyp_count,
            "hypotheses_survived": survived,
            "hypotheses_wounded": wounded,
            "hypotheses_killed": killed,
        })
    return results


@router.get("/runs/latest")
def get_latest_run(db: Session = Depends(get_db)):
    run = db.query(Run).order_by(desc(Run.timestamp)).first()
    if not run:
        raise HTTPException(status_code=404, detail="No runs found")
    return {"id": run.id, "timestamp": run.timestamp, "status": run.status}


@router.get("/runs/{run_id}")
def get_run_detail(run_id: str, db: Session = Depends(get_db)):
    """Full run detail for audit mode -- includes all stage outputs."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    hyps = db.query(HypothesisModel).filter(HypothesisModel.run_id == run_id).all()
    activation_scores = json.loads(run.activation_scores) if run.activation_scores else {}
    generation_output = json.loads(run.generation_output) if run.generation_output else []
    elimination_output = json.loads(run.elimination_output) if run.elimination_output else []

    from backend.api.hypotheses import _model_to_dict
    hypothesis_dicts = [_model_to_dict(h, db) for h in hyps]

    return {
        "id": run.id,
        "timestamp": run.timestamp,
        "status": run.status,
        "activation_scores": activation_scores,
        "generation_output": generation_output,
        "elimination_output": elimination_output,
        "hypotheses": hypothesis_dicts,
    }


# --- Pipeline status ---

@router.get("/pipeline/status")
def get_pipeline_status(db: Session = Depends(get_db)):
    return _get_current_pipeline_state(db)


# --- Prompt generation ---

@router.get("/pipeline/prompt/generation")
def get_generation_prompt(db: Session = Depends(get_db)):
    """Build and return the generation prompt text for copy-paste."""
    # Load theories and briefing
    theories = theory_parser.load_all_theories()
    briefing_data = _load_briefing()
    if not briefing_data:
        raise HTTPException(status_code=400, detail="No briefing packet available. Run the data agent first.")

    briefing = BriefingPacket(**briefing_data)

    # Run activation scoring
    activation_results = activation.score_all_theories(theories, briefing)

    # Get queued inbox items
    inbox_rows = db.query(InboxItem).filter(InboxItem.status == "queued").all()
    inbox_items = [
        {"date": item.date, "content": item.content, "source": item.source or "",
         "theories": json.loads(item.theories) if item.theories else []}
        for item in inbox_rows
    ]

    # Ensure a run exists for this pipeline execution
    run = _get_or_create_active_run(db, activation_results)

    prompt = build_generation_prompt(
        theories=theories,
        activation_results=activation_results,
        briefing=briefing_data,
        inbox_items=inbox_items,
    )

    return {"prompt": prompt, "run_id": run.id}


@router.get("/pipeline/prompt/elimination")
def get_elimination_prompt(db: Session = Depends(get_db)):
    """Build and return the elimination prompt text (requires generation output)."""
    latest_run = db.query(Run).order_by(desc(Run.timestamp)).first()
    if not latest_run or not latest_run.generation_output:
        raise HTTPException(
            status_code=400,
            detail="Generation output must be imported before generating the elimination prompt.",
        )

    theories = theory_parser.load_all_theories()
    briefing_data = _load_briefing()
    briefing = BriefingPacket(**briefing_data)
    activation_results = activation.score_all_theories(theories, briefing)

    # Get generated hypotheses from the current run
    hyps = db.query(HypothesisModel).filter(HypothesisModel.run_id == latest_run.id).all()
    hypothesis_dicts = [
        {
            "id": h.id,
            "theory_id": h.source_theory,
            "source_theories": json.loads(h.source_theories) if h.source_theories else [h.source_theory],
            "short_name": h.short_name,
            "full_statement": h.full_statement,
            "predicted_assets": json.loads(h.predicted_assets) if h.predicted_assets else [],
            "asset_direction": json.loads(h.asset_direction) if h.asset_direction else {},
            "hard_falsifiers": json.loads(h.hard_falsifiers) if h.hard_falsifiers else [],
            "soft_falsifiers": json.loads(h.soft_falsifiers) if h.soft_falsifiers else [],
            "timeframe": h.timeframe,
        }
        for h in hyps
    ]

    prompt = build_elimination_prompt(
        hypotheses=hypothesis_dicts,
        theories=theories,
        activation_results=activation_results,
        briefing=briefing_data,
    )

    return {"prompt": prompt, "run_id": latest_run.id}


# --- Import endpoints ---

@router.post("/pipeline/import/generation")
def import_generation(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Import generation output JSON. Creates hypotheses in the database."""
    raw_json = payload.get("json_text", "")
    if not raw_json:
        raise HTTPException(status_code=400, detail="Missing 'json_text' field in request body")

    # Get or create active run
    run = _get_or_create_active_run(db)

    # Clear any existing hypotheses for this run (allows re-import)
    db.query(HypothesisModel).filter(HypothesisModel.run_id == run.id).delete()
    run.generation_output = None
    db.flush()

    try:
        hypotheses = parse_generation_output(raw_json, run.id)
    except ParseError as e:
        raise HTTPException(
            status_code=422,
            detail={"message": e.message, "field_errors": e.field_errors, "raw_preview": e.raw_input},
        )

    # Store in database
    created = []
    for h_data in hypotheses:
        conv_inputs = h_data.pop("_conviction_inputs", {})
        h = HypothesisModel(**h_data)
        db.add(h)
        created.append({**h_data, "_conviction_inputs": conv_inputs})

    # Update run with raw generation output
    run.generation_output = raw_json
    db.commit()

    return {"run_id": run.id, "hypotheses_created": len(created), "hypotheses": created}


@router.post("/pipeline/import/elimination")
def import_elimination(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Import elimination output JSON. Updates hypotheses and triggers conviction scoring."""
    raw_json = payload.get("json_text", "")
    if not raw_json:
        raise HTTPException(status_code=400, detail="Missing 'json_text' field in request body")

    latest_run = db.query(Run).order_by(desc(Run.timestamp)).first()
    if not latest_run:
        raise HTTPException(status_code=400, detail="No active run. Import generation output first.")

    # Get existing hypotheses for this run
    existing_hyps = db.query(HypothesisModel).filter(HypothesisModel.run_id == latest_run.id).all()
    existing_dicts = [
        {
            "id": h.id,
            "short_name": h.short_name,
            "source_theory": h.source_theory,
            "status": h.status,
            "soft_falsifiers": h.soft_falsifiers or "[]",
        }
        for h in existing_hyps
    ]

    try:
        updated = parse_elimination_output(raw_json, existing_dicts)
    except ParseError as e:
        raise HTTPException(
            status_code=422,
            detail={"message": e.message, "field_errors": e.field_errors, "raw_preview": e.raw_input},
        )

    # Update hypotheses in database and run conviction scoring
    scored_results = []
    # Count overlaps for overlap penalty
    asset_counts: dict[str, int] = {}
    for h_data in updated:
        if h_data.get("status") != "KILLED":
            assets = json.loads(h_data.get("predicted_assets", "[]")) if isinstance(h_data.get("predicted_assets"), str) else h_data.get("predicted_assets", [])
            for asset in assets:
                asset_counts[asset] = asset_counts.get(asset, 0) + 1

    for h_data in updated:
        h = db.query(HypothesisModel).filter(HypothesisModel.id == h_data["id"]).first()
        if not h:
            continue

        h.status = h_data["status"]
        h.elimination_notes = h_data.get("elimination_notes", "")
        h.soft_falsifiers = h_data.get("soft_falsifiers", h.soft_falsifiers)

        # Run conviction scoring for non-KILLED hypotheses
        if h.status != "KILLED":
            conv_inputs = h_data.get("_conviction_inputs", {})
            soft_f = json.loads(h.soft_falsifiers) if h.soft_falsifiers else []
            triggered_sf = [{"severity": sf["severity"]} for sf in soft_f if sf.get("status") == "TRIGGERED"]

            # Compute overlap for primary asset
            assets = json.loads(h.predicted_assets) if h.predicted_assets else []
            primary_asset = assets[0] if assets else ""
            overlap = max(0, asset_counts.get(primary_asset, 1) - 1)

            ci = ConvictionInput(
                hypothesis_id=h.id,
                support_strength=conv_inputs.get("support_strength", 0.5),
                evidence_quality=conv_inputs.get("evidence_quality", 0.5),
                convergence=conv_inputs.get("convergence", 0.3),
                falsifier_clarity=conv_inputs.get("falsifier_clarity", 0.7),
                triggered_soft_falsifiers=triggered_sf,
                overlap_count=overlap,
                horizon_alignment=conv_inputs.get("horizon_alignment", 0.5),
                expression_efficiency=conv_inputs.get("expression_efficiency", 0.5),
            )

            result = conviction.score_conviction(ci)
            h.conviction = result.stage3.final
            h.conviction_math = json.dumps(result.model_dump())
        else:
            h.conviction = 0.0
            h.conviction_math = None

        scored_results.append({"id": h.id, "status": h.status, "conviction": h.conviction})

    # Update run
    latest_run.elimination_output = raw_json
    latest_run.status = "complete"

    # Mark queued inbox items as incorporated
    db.query(InboxItem).filter(InboxItem.status == "queued").update(
        {"status": "incorporated", "incorporated_run_id": latest_run.id}
    )

    db.commit()

    return {
        "run_id": latest_run.id,
        "hypotheses_updated": len(scored_results),
        "results": scored_results,
    }


# --- Snapshot endpoint for static publishing ---

@router.get("/snapshot")
def get_snapshot(db: Session = Depends(get_db)):
    """Export the current state as a single JSON blob for static publishing.

    This powers the GitHub Pages read-only view. It bundles:
    - All hypotheses from the latest completed run
    - The latest briefing packet
    - Activation scores
    - Theory metadata
    - Run metadata
    """
    from backend.api.hypotheses import _model_to_dict

    # Latest completed run
    latest_run = db.query(Run).filter(Run.status == "complete").order_by(desc(Run.timestamp)).first()

    run_data = None
    hypotheses = []
    activation_scores = []

    if latest_run:
        run_data = {
            "id": latest_run.id,
            "timestamp": latest_run.timestamp,
            "status": latest_run.status,
        }
        hyps = db.query(HypothesisModel).filter(HypothesisModel.run_id == latest_run.id).all()
        hypotheses = [_model_to_dict(h, db) for h in hyps]
        activation_scores = json.loads(latest_run.activation_scores) if latest_run.activation_scores else []

    # Briefing
    briefing_data = _load_briefing()

    # Theories (just names and IDs, not full markdown)
    theories = theory_parser.load_all_theories()
    theory_summaries = [
        {"theory_id": t.theory_id, "name": t.name, "domain": t.domain, "is_two_phase": t.is_two_phase}
        for t in theories
    ]

    return {
        "snapshot_timestamp": datetime.now().isoformat(),
        "run": run_data,
        "hypotheses": hypotheses,
        "activation_scores": activation_scores,
        "briefing": briefing_data,
        "theories": theory_summaries,
    }


@router.post("/publish")
def publish_to_ghpages(db: Session = Depends(get_db)):
    """Trigger the GitHub Pages publish script.

    Requires the backend to be running and git to be configured.
    This runs scripts/publish_ghpages.sh as a subprocess.
    """
    import subprocess
    from backend.config import BASE_DIR

    script = BASE_DIR / "scripts" / "publish_ghpages.sh"
    if not script.exists():
        raise HTTPException(status_code=404, detail="Publish script not found")

    try:
        result = subprocess.run(
            [str(script)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(BASE_DIR),
        )
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Publish failed:\n{result.stderr[-500:] if result.stderr else result.stdout[-500:]}",
            )
        return {"status": "ok", "output": result.stdout[-1000:]}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Publish timed out after 120 seconds")


def _get_or_create_active_run(db: Session, activation_results=None) -> Run:
    """Get the current active (partial) run, or create a new one."""
    latest = db.query(Run).order_by(desc(Run.timestamp)).first()
    if latest and latest.status != "complete":
        return latest

    run_id = f"R-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    activation_json = None
    if activation_results:
        activation_json = json.dumps([ar.model_dump() for ar in activation_results])

    run = Run(
        id=run_id,
        timestamp=datetime.now().isoformat(),
        status="partial",
        activation_scores=activation_json,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
