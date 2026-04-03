# pipeline.py -- Pipeline status, prompt generation, and import endpoints.
# Depends on: db/database.py, db/models.py, engine/prompt_builder.py, engine/output_parser.py,
#             engine/theory_parser.py, engine/activation.py, engine/conviction.py
# Depended on by: main.py (router registration)
from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Hypothesis as HypothesisModel
from backend.db.models import HypothesisThread, InboxItem, Run, RunPriceSnapshot, SectorFalsifierAudit
from backend.engine import activation, conviction, regime, theory_parser
from backend.engine.output_parser import ParseError, parse_elimination_output, parse_generation_output, parse_sector_falsifier_audits
from backend.engine.prompt_builder import build_elimination_prompt, build_generation_prompt
from backend.engine.sector_appendices import select_sector_appendices
from backend.schemas.briefing import BriefingPacket
from backend.schemas.scoring import ConvictionInput

router = APIRouter(tags=["pipeline"])


def _activation_status_dict(activation_results) -> dict[str, str]:
    """Convert list[ActivationResult] to {theory_id: tier_value} for regime flag computation."""
    status = {}
    for ar in activation_results:
        # ActivationResult has effective_tier (two-phase) or tier (single-phase)
        ar_dict = ar.model_dump() if hasattr(ar, "model_dump") else ar
        tier = ar_dict.get("effective_tier") or ar_dict.get("tier")
        if tier:
            status[ar_dict["theory_id"]] = tier if isinstance(tier, str) else tier.value
    return status


def _load_briefing() -> dict[str, Any]:
    """Load the latest briefing packet from mock_data or data directory."""
    from backend.config import DATA_DIR, MOCK_DATA_DIR

    # Try real briefing first, fall back to mock
    for path in [DATA_DIR / "briefing_packet.json", MOCK_DATA_DIR / "briefing_packet.json"]:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _assess_data_quality(briefing: dict) -> dict:
    """Assess briefing packet completeness. Returns a quality report for the frontend.

    Sections: growth, inflation, rates, liquidity, credit, sentiment (FRED-sourced)
              computed (derived), markets (Yahoo Finance).
    """
    if not briefing:
        return {"status": "missing", "message": "No briefing data. Run REFRESH DATA first.", "sections": {}}

    FRED_SECTIONS = ["growth", "inflation", "rates", "liquidity", "credit", "sentiment"]
    sections = {}
    total_filled = 0
    total_fields = 0

    for section_name in FRED_SECTIONS:
        section = briefing.get(section_name, {})
        filled = sum(1 for v in section.values() if v is not None) if isinstance(section, dict) else 0
        count = len(section) if isinstance(section, dict) else 0
        sections[section_name] = {"filled": filled, "total": count}
        total_filled += filled
        total_fields += count

    # Markets (Yahoo Finance)
    markets = briefing.get("markets", {})
    markets_count = len(markets) if isinstance(markets, dict) else 0
    sections["markets"] = {"filled": markets_count, "total": markets_count}

    # Computed
    computed = briefing.get("computed", {})
    comp_filled = sum(1 for v in computed.values() if v is not None) if isinstance(computed, dict) else 0
    comp_total = len(computed) if isinstance(computed, dict) else 0
    sections["computed"] = {"filled": comp_filled, "total": comp_total}

    # Overall assessment
    fred_empty = total_fields == 0 or total_filled == 0
    if fred_empty and markets_count == 0:
        status = "missing"
        message = "No briefing data. Run REFRESH DATA first."
    elif fred_empty:
        status = "degraded"
        message = (
            f"FRED macro data is empty (growth, rates, inflation, liquidity, credit all missing). "
            f"Markets: {markets_count} tickers loaded. "
            f"Most theories will score Inactive without FRED data. "
            f"Check your FRED_API_KEY in .env and re-run REFRESH DATA."
        )
    elif total_filled < total_fields * 0.5:
        status = "partial"
        message = (
            f"FRED data partially loaded: {total_filled}/{total_fields} fields filled. "
            f"Some theories may score lower than expected due to missing indicators."
        )
    else:
        status = "ok"
        message = f"Data loaded: {total_filled}/{total_fields} FRED fields, {markets_count} market tickers, {comp_filled}/{comp_total} computed."

    return {"status": status, "message": message, "sections": sections}


def _get_current_pipeline_state(db: Session) -> dict:
    """Determine the current state of each pipeline step."""
    latest_run = db.query(Run).order_by(desc(Run.timestamp)).first()

    briefing_data = _load_briefing()
    briefing_fresh = bool(briefing_data)
    briefing_timestamp = briefing_data.get("timestamp", "") if briefing_data else ""
    data_quality = _assess_data_quality(briefing_data)

    if not latest_run:
        # No runs at all
        return {
            "current_step": 1 if briefing_fresh else 0,
            "run_id": "",
            "briefing_timestamp": briefing_timestamp,
            "data_quality": data_quality,
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
            "data_quality": data_quality,
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
        "data_quality": data_quality,
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


@router.get("/runs/archive")
def get_run_archive(db: Session = Depends(get_db)):
    """All runs with summary stats for the archive panel."""
    runs = db.query(Run).order_by(desc(Run.timestamp)).all()
    results = []
    # Aggregate outcome counts across all hypotheses
    outcome_counts = {"pending": 0, "correct": 0, "incorrect": 0, "partial": 0, "expired": 0}

    for r in runs:
        hyps = db.query(HypothesisModel).filter(HypothesisModel.run_id == r.id).all()
        total = len(hyps)
        survived = sum(1 for h in hyps if h.status == "SURVIVED")
        wounded = sum(1 for h in hyps if h.status == "WOUNDED")
        killed = sum(1 for h in hyps if h.status == "KILLED")

        # Count active theories from activation_scores
        active_theories = 0
        total_theories = 0
        if r.activation_scores:
            acts = json.loads(r.activation_scores)
            if isinstance(acts, list):
                total_theories = len(acts)
                for a in acts:
                    tier = (a.get("effective_tier") or a.get("tier") or "").upper()
                    if tier == "ACTIVE":
                        active_theories += 1

        # Per-run outcome counts
        for h in hyps:
            if h.outcome_status:
                key = h.outcome_status.lower()
                if key in outcome_counts:
                    outcome_counts[key] += 1
            else:
                outcome_counts["pending"] += 1

        results.append({
            "id": r.id,
            "timestamp": r.timestamp,
            "status": r.status,
            "active_theories": active_theories,
            "total_theories": total_theories,
            "hypotheses_generated": total,
            "hypotheses_survived": survived + wounded,
            "hypotheses_killed": killed,
            "price_snapshot_date": r.price_snapshot_date,
        })

    return {"runs": results, "outcome_counts": outcome_counts}


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

    regime_flags = json.loads(run.regime_flags_active) if run.regime_flags_active else []

    return {
        "id": run.id,
        "timestamp": run.timestamp,
        "status": run.status,
        "activation_scores": activation_scores,
        "regime_flags_active": regime_flags,
        "generation_output": generation_output,
        "elimination_output": elimination_output,
        "hypotheses": hypothesis_dicts,
    }


@router.get("/runs/{run_id}/prices")
def get_run_prices(run_id: str, db: Session = Depends(get_db)):
    """Get price snapshots for a run."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    snapshots = db.query(RunPriceSnapshot).filter(RunPriceSnapshot.run_id == run_id).all()
    return {
        "run_id": run_id,
        "price_snapshot_date": run.price_snapshot_date,
        "prices": {s.ticker: {"price": s.price, "date": s.date, "source": s.source} for s in snapshots},
    }


@router.get("/runs/{run_id}/walkforward")
def get_run_walkforward(run_id: str, db: Session = Depends(get_db)):
    """Walk-forward data: entry prices + current prices + direction-aware deltas."""
    from backend.api.trades import _fetch_current_price

    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Get price snapshots (entry prices)
    snapshots = db.query(RunPriceSnapshot).filter(RunPriceSnapshot.run_id == run_id).all()
    entry_prices = {s.ticker: s.price for s in snapshots}

    # Get hypotheses for this run (non-KILLED survivors for walk-forward display)
    hyps = db.query(HypothesisModel).filter(HypothesisModel.run_id == run_id).all()

    # Collect tickers we need current prices for
    tickers_needed: set[str] = set()
    rows = []
    for h in hyps:
        assets = json.loads(h.predicted_assets) if h.predicted_assets else []
        directions = json.loads(h.asset_direction) if h.asset_direction else {}
        primary = assets[0] if assets else None
        if primary:
            tickers_needed.add(primary)
            rows.append({
                "hypothesis_id": h.id,
                "short_name": h.short_name,
                "ticker": primary,
                "direction": directions.get(primary, "LONG"),
                "status": h.status,
                "conviction": h.conviction,
                "outcome_status": h.outcome_status,
            })

    # Fetch current prices
    current_prices: dict[str, float | None] = {}
    for ticker in tickers_needed:
        current_prices[ticker] = _fetch_current_price(ticker)

    # Compute direction-aware deltas
    from backend.realization import compute_expression_return

    for row in rows:
        ticker = row["ticker"]
        entry = entry_prices.get(ticker)
        current = current_prices.get(ticker)
        row["entry_price"] = entry
        row["current_price"] = current
        if entry and current and entry > 0:
            raw_delta = (current - entry) / entry
            # Direction-aware: positive = hypothesis winning
            if row["direction"] == "SHORT":
                raw_delta = -raw_delta
            row["delta_pct"] = round(raw_delta * 100, 2)
        else:
            row["delta_pct"] = None

    # Compute aggregate expression_return per hypothesis (mean of all leg deltas)
    hyp_map = {h.id: h for h in hyps}
    for row in rows:
        h = hyp_map.get(row["hypothesis_id"])
        if h:
            h_assets = json.loads(h.predicted_assets) if h.predicted_assets else []
            h_dirs = json.loads(h.asset_direction) if h.asset_direction else {}
            h_current = {t: current_prices[t] for t in h_assets if t in current_prices}
            expr_ret = compute_expression_return(h_assets, h_dirs, entry_prices, h_current)
            row["expression_return"] = round(expr_ret, 6) if expr_ret is not None else None
        else:
            row["expression_return"] = None

    # Outcome summary for this run
    outcome_counts = {"pending": 0, "correct": 0, "incorrect": 0, "partial": 0, "expired": 0}
    for h in hyps:
        if h.outcome_status:
            key = h.outcome_status.lower()
            if key in outcome_counts:
                outcome_counts[key] += 1
        else:
            outcome_counts["pending"] += 1

    return {
        "run_id": run_id,
        "run_date": run.timestamp,
        "price_snapshot_date": run.price_snapshot_date,
        "rows": rows,
        "outcome_counts": outcome_counts,
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

    # Pass 1.5: Compute regime flags from activation results
    active_flags = regime.compute_regime_flags(_activation_status_dict(activation_results))

    # Ensure a run exists for this pipeline execution
    run = _get_or_create_active_run(db, activation_results)

    # Store active regime flag IDs on the run
    flag_ids = [f["flag_id"] for f in active_flags]
    run.regime_flags_active = json.dumps(flag_ids)
    db.commit()

    # Query prior surviving hypotheses with realization data for continuation context
    prior_hyps = (
        db.query(HypothesisModel)
        .filter(
            HypothesisModel.run_id != run.id,
            HypothesisModel.status.in_(["SURVIVED", "WOUNDED"]),
        )
        .all()
    )
    prior_hypotheses = []
    for h in prior_hyps:
        # Only include hypotheses that have at least some realization data
        has_realization = (
            h.expression_return is not None
            or h.predicted_magnitude_lower is not None
        )
        if has_realization:
            prior_hypotheses.append({
                "id": h.id,
                "short_name": h.short_name,
                "predicted_assets": json.loads(h.predicted_assets) if h.predicted_assets else [],
                "asset_direction": json.loads(h.asset_direction) if h.asset_direction else {},
                "predicted_magnitude_lower": h.predicted_magnitude_lower,
                "predicted_magnitude_upper": h.predicted_magnitude_upper,
                "timeframe_end_date": h.timeframe_end_date,
                "expression_return": h.expression_return,
                "realization_vs_lower": h.realization_vs_lower,
                "realization_vs_upper": h.realization_vs_upper,
                "time_elapsed_pct": h.time_elapsed_pct,
                "status": h.status,
                "continuation_generation": h.continuation_generation or 1,
                "continuation_of": h.continuation_of,
            })

    prompt = build_generation_prompt(
        theories=theories,
        activation_results=activation_results,
        briefing=briefing_data,
        inbox_items=inbox_items,
        active_regime_flags=active_flags,
        prior_hypotheses=prior_hypotheses if prior_hypotheses else None,
    )

    return {"prompt": prompt, "run_id": run.id, "regime_flags_active": flag_ids}


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
            "resolution_channel": h.resolution_channel or "",
        }
        for h in hyps
    ]

    # Check if any hypothesis has a channel tag
    has_channel_tags = any(h.resolution_channel for h in hyps)

    # Select sector appendices based on hypothesis tickers (v4)
    selected_appendices = select_sector_appendices(hypothesis_dicts)
    sector_ids = [a["sector_id"] for a in selected_appendices]

    # Persist selected sector_ids on the run
    latest_run.sector_appendices_loaded = json.dumps(sector_ids) if sector_ids else None
    db.commit()

    prompt = build_elimination_prompt(
        hypotheses=hypothesis_dicts,
        theories=theories,
        activation_results=activation_results,
        briefing=briefing_data,
        has_channel_tags=has_channel_tags,
        sector_appendices=selected_appendices,
    )

    return {"prompt": prompt, "run_id": latest_run.id, "sector_appendices_loaded": sector_ids}


# --- Import endpoints ---

@router.post("/pipeline/import/generation")
def import_generation(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Import generation output JSON. Creates hypotheses and manages thread lifecycle.

    Handles five lifecycle actions:
    - NEW: Create thread + instance, capture entry prices and payoff band
    - CONFIRM: Link instance to existing thread, increment counters, inherit falsifier counters
    - UPDATE: Link instance to existing thread, reset confirmation_count, update timeframe if revised
    - RENEW: RETIRE old thread, create new thread with renewed_from link, new instance
    - RETIRE: Set thread status=RETIRED (no new instance)
    """
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

    # Load current price snapshot for entry prices on NEW/RENEW threads
    price_snapshot = _get_current_prices_for_threads(db, run)

    # Process lifecycle actions and store in database
    created = []
    retired_threads = []
    thread_actions_log = []

    for h_data in hypotheses:
        # Pop internal/transient fields before DB insert
        conv_inputs = h_data.pop("_conviction_inputs", {})
        thread_id_ref = h_data.pop("_thread_id_ref", None)
        retire_only = h_data.pop("_retire_only", False)
        revised_timeframe = h_data.pop("_revised_timeframe_end_date", None)
        revised_short_name = h_data.pop("_revised_short_name", None)
        revised_full_statement = h_data.pop("_revised_full_statement", None)

        action = h_data.get("lifecycle_action", "NEW")

        # --- RETIRE: no instance, just update thread status ---
        if retire_only or action == "RETIRE":
            if thread_id_ref:
                thread = db.query(HypothesisThread).filter(
                    HypothesisThread.thread_id == thread_id_ref
                ).first()
                if thread:
                    thread.status = "RETIRED"
                    retired_threads.append(thread_id_ref)
                    thread_actions_log.append({
                        "action": "RETIRE",
                        "thread_id": thread_id_ref,
                    })
            continue

        # --- CONFIRM: existing thread, new instance, increment counters ---
        if action == "CONFIRM" and thread_id_ref:
            thread = db.query(HypothesisThread).filter(
                HypothesisThread.thread_id == thread_id_ref
            ).first()
            if thread:
                h_data = _apply_thread_to_instance(h_data, thread, db)
                thread.confirmation_count += 1
                thread.total_instances += 1
                h_data["thread_id"] = thread.thread_id
                h = HypothesisModel(**h_data)
                db.add(h)
                created.append({**h_data, "_conviction_inputs": conv_inputs})
                thread_actions_log.append({
                    "action": "CONFIRM",
                    "thread_id": thread.thread_id,
                    "instance_id": h_data["id"],
                })
                continue

        # --- UPDATE: existing thread, new instance, reset confirmation_count ---
        if action == "UPDATE" and thread_id_ref:
            thread = db.query(HypothesisThread).filter(
                HypothesisThread.thread_id == thread_id_ref
            ).first()
            if thread:
                h_data = _apply_thread_to_instance(h_data, thread, db)
                thread.confirmation_count = 0
                thread.total_instances += 1
                # Apply revised fields if provided
                if revised_timeframe:
                    thread.timeframe_end_date = revised_timeframe
                if revised_short_name:
                    h_data["short_name"] = revised_short_name
                if revised_full_statement:
                    h_data["full_statement"] = revised_full_statement
                h_data["thread_id"] = thread.thread_id
                h = HypothesisModel(**h_data)
                db.add(h)
                created.append({**h_data, "_conviction_inputs": conv_inputs})
                thread_actions_log.append({
                    "action": "UPDATE",
                    "thread_id": thread.thread_id,
                    "instance_id": h_data["id"],
                })
                continue

        # --- RENEW: retire old thread, create new thread + instance ---
        if action == "RENEW" and thread_id_ref:
            old_thread = db.query(HypothesisThread).filter(
                HypothesisThread.thread_id == thread_id_ref
            ).first()
            if old_thread:
                old_thread.status = "RETIRED"
                retired_threads.append(thread_id_ref)

            # Create the instance first (thread needs originating_instance_id)
            h = HypothesisModel(**h_data)
            db.add(h)
            db.flush()  # Ensure h.id is available for FK

            # Create new thread with renewed_from link
            new_thread = _create_thread_for_instance(h_data, run, price_snapshot, renewed_from=thread_id_ref)
            db.add(new_thread)
            db.flush()  # Thread must exist before hypothesis can reference it
            h.thread_id = new_thread.thread_id
            h_data["thread_id"] = new_thread.thread_id
            created.append({**h_data, "_conviction_inputs": conv_inputs})
            thread_actions_log.append({
                "action": "RENEW",
                "old_thread_id": thread_id_ref,
                "new_thread_id": new_thread.thread_id,
                "instance_id": h_data["id"],
            })
            continue

        # --- NEW (default): create thread + instance ---
        h = HypothesisModel(**h_data)
        db.add(h)
        db.flush()  # Ensure h.id is available for FK

        new_thread = _create_thread_for_instance(h_data, run, price_snapshot)
        db.add(new_thread)
        db.flush()  # Thread must exist before hypothesis can reference it
        h.thread_id = new_thread.thread_id
        h_data["thread_id"] = new_thread.thread_id
        created.append({**h_data, "_conviction_inputs": conv_inputs})
        thread_actions_log.append({
            "action": "NEW",
            "thread_id": new_thread.thread_id,
            "instance_id": h_data["id"],
        })

    # Update run with raw generation output
    run.generation_output = raw_json
    db.commit()

    return {
        "run_id": run.id,
        "hypotheses_created": len(created),
        "hypotheses": created,
        "thread_actions": thread_actions_log,
        "retired_threads": retired_threads,
    }


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
            "predicted_assets": h.predicted_assets or "[]",
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

    # Load activation scores and briefing for mechanical conviction computation
    activation_data = json.loads(latest_run.activation_scores) if latest_run.activation_scores else []
    briefing_raw = _load_briefing()

    # Load active regime flags for conviction scoring (D_r discount)
    active_regime_flags = []
    if latest_run.regime_flags_active:
        flag_ids = json.loads(latest_run.regime_flags_active)
        if flag_ids:
            # Reconstruct full flag objects from config
            from backend.engine.regime_config import REGIME_FLAGS
            for flag in REGIME_FLAGS["flags"]:
                if flag["flag_id"] in flag_ids:
                    active_regime_flags.append({
                        "flag_id": flag["flag_id"],
                        "affects": flag["affects"],
                        "channel_context": flag["channel_context"],
                        "channel_alignment": flag["channel_alignment"],
                    })

    # Parse elimination JSON for per-hypothesis elimination results
    data = _extract_json_for_lookup(raw_json)

    # Parse sector falsifier audit entries from evaluator output (v4)
    sector_audit_entries = parse_sector_falsifier_audits(raw=raw_json, elimination_items=data)
    # Build per-hypothesis lookup: hypothesis_id -> list of audit entries
    sector_audit_by_hypothesis: dict[str, list[dict]] = {}
    for entry in sector_audit_entries:
        hid = entry.get("hypothesis_id", "")
        if hid:
            sector_audit_by_hypothesis.setdefault(hid, []).append(entry)

    # Persist sector audit records to dedicated table (v4)
    for entry in sector_audit_entries:
        audit_row = SectorFalsifierAudit(
            id=f"SA-{uuid.uuid4().hex[:12]}",
            hypothesis_id=entry.get("hypothesis_id", ""),
            sector_id=entry.get("sector_id", ""),
            falsifier_id=entry.get("falsifier_id", ""),
            metric_value_found=entry.get("metric_value_found", ""),
            triggered=entry.get("triggered", "NO"),
            relevant=entry.get("relevant", "N/A"),
            reasoning=entry.get("reasoning", ""),
            severity_applied=entry.get("severity_applied", "NONE"),
            run_id=latest_run.id,
        )
        db.add(audit_row)

    # Update hypotheses in database and run conviction scoring
    scored_results = []

    # Build per-asset, per-theory overlap index from non-KILLED hypotheses
    # Key: asset ticker -> list of (hypothesis_id, source_theory)
    asset_hypothesis_map: dict[str, list[tuple[str, str]]] = {}
    for h_data in updated:
        if h_data.get("status") == "KILLED":
            continue
        pa = h_data.get("predicted_assets", "[]")
        assets = json.loads(pa) if isinstance(pa, str) else (pa or [])
        theory = h_data.get("source_theory", "")
        hid = h_data.get("id", "")
        for asset in assets:
            asset_hypothesis_map.setdefault(asset, []).append((hid, theory))

    for h_data in updated:
        h = db.query(HypothesisModel).filter(HypothesisModel.id == h_data["id"]).first()
        if not h:
            continue

        h.status = h_data["status"]
        h.elimination_notes = h_data.get("elimination_notes", "")
        h.soft_falsifiers = h_data.get("soft_falsifiers", h.soft_falsifiers)

        # Handle channel correction from evaluator
        elim_for_channel = None
        for er in data:
            er_id = er.get("hypothesis_id", er.get("id", ""))
            if er_id == h.id:
                elim_for_channel = er
                break
        if elim_for_channel:
            cv = elim_for_channel.get("channel_verification", {})
            corrected = cv.get("correct_channel", "")
            assigned = cv.get("assigned_channel", "")
            if corrected and corrected != assigned:
                h.resolution_channel_original = h.resolution_channel or assigned
                h.resolution_channel = corrected

        # Run conviction scoring for non-KILLED hypotheses
        if h.status != "KILLED":
            llm_inputs = h_data.get("_conviction_inputs", {})
            soft_f = json.loads(h.soft_falsifiers) if h.soft_falsifiers else []
            triggered_sf = [{"severity": sf["severity"]} for sf in soft_f if sf.get("status") == "TRIGGERED"]
            untestable_sf = [{"severity": sf["severity"]} for sf in soft_f if sf.get("status") == "UNTESTABLE"]

            # Compute theory-aware overlap for primary asset
            assets = json.loads(h.predicted_assets) if h.predicted_assets else []
            primary_asset = assets[0] if assets else ""
            same_theory = 0
            diff_theory = 0
            if primary_asset:
                for other_id, other_theory in asset_hypothesis_map.get(primary_asset, []):
                    if other_id == h.id:
                        continue
                    if other_theory == h.source_theory:
                        same_theory += 1
                    else:
                        diff_theory += 1

            # Find the elimination result for this hypothesis (for falsifier_clarity)
            elim_result = None
            for er in data:
                er_id = er.get("hypothesis_id", er.get("id", ""))
                if er_id == h.id:
                    elim_result = er
                    break

            # Compute mechanical Stage 1 inputs (replaces LLM-assigned values)
            h_dict = {
                "source_theory": h.source_theory,
                "source_theories": h.source_theories or json.dumps([h.source_theory]),
                "asset_direction": h.asset_direction or "{}",
                "hard_falsifiers": h.hard_falsifiers or "[]",
                "soft_falsifiers": h.soft_falsifiers or "[]",
            }
            mech = conviction.compute_mechanical_conviction_inputs(
                hypothesis=h_dict,
                activation_results=activation_data,
                briefing=briefing_raw,
                elimination_result=elim_result,
            )

            # Mechanical Stage 3 gates: horizon alignment + expression efficiency
            mech_horizon = conviction.compute_horizon_alignment(h.timeframe or "")
            pred_assets_raw = h.predicted_assets or "[]"
            try:
                pred_assets = json.loads(pred_assets_raw) if isinstance(pred_assets_raw, str) else (pred_assets_raw or [])
            except (json.JSONDecodeError, TypeError):
                pred_assets = []
            mech_expression = conviction.compute_expression_efficiency(pred_assets)

            ci = ConvictionInput(
                hypothesis_id=h.id,
                support_strength=mech.support_strength,
                evidence_quality=mech.evidence_quality,
                convergence=mech.convergence,
                falsifier_clarity=mech.falsifier_clarity,
                triggered_soft_falsifiers=triggered_sf,
                untestable_soft_falsifiers=untestable_sf,
                same_theory_overlap=same_theory,
                diff_theory_overlap=diff_theory,
                resolution_channel=h.resolution_channel or "",
                active_regime_flags=active_regime_flags,
                sector_falsifier_audit=sector_audit_by_hypothesis.get(h.id, []),
                horizon_alignment=mech_horizon,
                expression_efficiency=mech_expression,
            )

            result = conviction.score_conviction(ci)
            h.conviction = result.stage3.final

            # Store full math with mechanical + LLM inputs for audit comparison
            math_dump = result.model_dump()
            math_dump["llm_conviction_inputs"] = llm_inputs
            math_dump["llm_horizon_alignment"] = llm_inputs.get("horizon_alignment", None)
            math_dump["llm_expression_efficiency"] = llm_inputs.get("expression_efficiency", None)
            math_dump["mechanical_conviction_inputs"] = mech.model_dump()
            math_dump["mechanical_horizon_alignment"] = mech_horizon
            math_dump["mechanical_expression_efficiency"] = mech_expression
            h.conviction_math = json.dumps(math_dump)

            # Conviction floor: mechanical kill for scores below 5
            if result.stage3.floor_killed:
                h.status = "KILLED"
                h.elimination_notes = (
                    (h.elimination_notes or "") + f"\n[MECHANICAL] {result.stage3.kill_reason}"
                ).strip()

            # Record which sector appendices were applied to this hypothesis (v4)
            h_sector_ids = list({e["sector_id"] for e in sector_audit_by_hypothesis.get(h.id, [])})
            if h_sector_ids:
                h.sector_appendices_applied = json.dumps(sorted(h_sector_ids))
        else:
            h.conviction = 0.0
            h.conviction_math = None

        scored_results.append({"id": h.id, "status": h.status, "conviction": h.conviction})

    # Capture price snapshots for all predicted tickers across all hypotheses
    _capture_price_snapshots(db, latest_run, updated)

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
    regime_flags_active = []

    if latest_run:
        run_data = {
            "id": latest_run.id,
            "timestamp": latest_run.timestamp,
            "status": latest_run.status,
            "sector_appendices_loaded": json.loads(latest_run.sector_appendices_loaded) if latest_run.sector_appendices_loaded else [],
        }
        # Include ALL hypotheses (across all runs), matching the local ledger view
        hyps = db.query(HypothesisModel).all()
        hypotheses = [_model_to_dict(h, db, for_snapshot=True) for h in hyps]
        activation_scores = json.loads(latest_run.activation_scores) if latest_run.activation_scores else []
        regime_flags_active = json.loads(latest_run.regime_flags_active) if latest_run.regime_flags_active else []

    # Briefing
    briefing_data = _load_briefing()

    # Theories — reuse the same assembly logic as /api/theories
    # to guarantee identical data shape on the static site.
    from backend.api.theories import build_theory_summaries
    theory_summaries = build_theory_summaries(briefing_data=briefing_data)

    # Newsletters
    from backend.db.models import Newsletter, Trade
    newsletters_raw = db.query(Newsletter).order_by(desc(Newsletter.date)).all()
    newsletters = []
    for nl in newsletters_raw:
        recs = json.loads(nl.trade_recommendations) if nl.trade_recommendations else []
        newsletters.append({
            "id": nl.id,
            "date": nl.date,
            "run_id": nl.run_id,
            "content": nl.content,
            "trade_recommendations": recs,
            "trade_count": len(recs),
            "created_at": nl.created_at,
        })

    # Trades
    trades_raw = db.query(Trade).order_by(desc(Trade.entry_date)).all()
    trades = []
    for t in trades_raw:
        trades.append({
            "id": t.id,
            "hypothesis_id": t.hypothesis_id,
            "run_id": t.run_id,
            "newsletter_id": t.newsletter_id,
            "ticker": t.ticker,
            "direction": t.direction,
            "entry_date": t.entry_date,
            "entry_price": t.entry_price,
            "shares": t.shares,
            "conviction_at_entry": t.conviction_at_entry,
            "exit_date": t.exit_date,
            "exit_price": t.exit_price,
            "exit_reason": t.exit_reason,
            "status": t.status,
            "hypothesis_short_name": t.hypothesis_short_name,
            "hypothesis_theory": t.hypothesis_theory,
            "hypothesis_status_at_entry": t.hypothesis_status_at_entry,
        })

    return {
        "snapshot_timestamp": datetime.now().isoformat(),
        "run": run_data,
        "hypotheses": hypotheses,
        "activation_scores": activation_scores,
        "regime_flags_active": regime_flags_active,
        "briefing": briefing_data,
        "theories": theory_summaries,
        "newsletters": newsletters,
        "trades": trades,
    }


@router.post("/publish")
def publish_to_ghpages(db: Session = Depends(get_db)):
    """Trigger the GitHub Pages publish script.

    Requires the backend to be running and git to be configured.
    This runs scripts/publish_ghpages.sh as a subprocess.
    Output is logged to logs/publish.log for post-mortem investigation.
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
        combined = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Publish failed (exit {result.returncode}):\n{combined[-2000:]}",
            )
        return {"status": "ok", "output": combined[-2000:]}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Publish timed out after 120 seconds")


@router.get("/publish/log")
def get_publish_log():
    """Return the last publish log for debugging failed publishes."""
    from backend.config import BASE_DIR

    log_file = BASE_DIR / "logs" / "publish.log"
    if not log_file.exists():
        return {"log": "(no publish log found)"}
    text = log_file.read_text()
    # Return last 5000 chars to keep response reasonable
    return {"log": text[-5000:]}


def _extract_json_for_lookup(raw_json: str) -> list[dict]:
    """Parse elimination raw JSON into a list for per-hypothesis lookup."""
    try:
        parsed = json.loads(raw_json)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    # Try extracting array from noisy output
    import re
    start = raw_json.find("[")
    end = raw_json.rfind("]")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(raw_json[start:end + 1])
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    return []


def _capture_price_snapshots(db: Session, run: Run, hypotheses: list[dict]):
    """Capture current prices for all tickers across all hypotheses in this run."""
    from backend.api.trades import _fetch_current_price

    # Collect all unique tickers
    all_tickers: set[str] = set()
    for h_data in hypotheses:
        pa = h_data.get("predicted_assets", "[]")
        assets = json.loads(pa) if isinstance(pa, str) else (pa or [])
        all_tickers.update(assets)

    if not all_tickers:
        return

    today = date.today().isoformat()

    # Clear any existing snapshots for this run (allows re-import)
    db.query(RunPriceSnapshot).filter(RunPriceSnapshot.run_id == run.id).delete()

    for ticker in sorted(all_tickers):
        price = _fetch_current_price(ticker)
        if price is not None:
            db.add(RunPriceSnapshot(
                run_id=run.id,
                ticker=ticker,
                price=price,
                date=today,
                source="yahoo_finance",
            ))

    run.price_snapshot_date = today


# ---------------------------------------------------------------------------
# Thread lifecycle helpers (v7)
# ---------------------------------------------------------------------------

def _create_thread_for_instance(
    h_data: dict,
    run: Run,
    price_snapshot: dict[str, float],
    renewed_from: str | None = None,
) -> HypothesisThread:
    """Create a new HypothesisThread for a NEW or RENEW action.

    Entry prices are captured from the current run's price snapshot.
    Payoff band and timeframe come from the hypothesis data.
    """
    run_ts = run.id.replace("R-", "") if run.id.startswith("R-") else run.id

    # Derive sequence number from hypothesis ID
    h_id = h_data.get("id", "")
    seq = h_id.split("-")[-1] if h_id else "01"
    thread_id = f"T-{run_ts}-{seq}"

    # Build entry prices for the tickers in this hypothesis
    predicted_assets = json.loads(h_data.get("predicted_assets", "[]"))
    entry_prices = {}
    for ticker in predicted_assets:
        if ticker in price_snapshot:
            entry_prices[ticker] = price_snapshot[ticker]

    return HypothesisThread(
        thread_id=thread_id,
        status="ACTIVE",
        originating_instance_id=h_data["id"],
        originating_run_id=run.id,
        entry_prices=json.dumps(entry_prices) if entry_prices else None,
        payoff_band_lower=h_data.get("predicted_magnitude_lower"),
        payoff_band_upper=h_data.get("predicted_magnitude_upper"),
        timeframe_end_date=h_data.get("timeframe_end_date"),
        renewed_from=renewed_from,
        source_theory=h_data.get("source_theory", "unknown"),
        created_date=date.today().isoformat(),
        confirmation_count=0,
        total_instances=1,
    )


def _apply_thread_to_instance(
    h_data: dict,
    thread: HypothesisThread,
    db: Session,
) -> dict:
    """Apply thread context to a CONFIRM or UPDATE instance.

    For CONFIRM/UPDATE, the instance inherits the originating thread's
    realization anchor (entry prices, payoff band). If the LLM provided
    only a thread reference without full hypothesis fields, we carry
    forward fields from the prior instance in the thread.
    """
    # Find the most recent prior instance in this thread
    prior = (
        db.query(HypothesisModel)
        .filter(HypothesisModel.thread_id == thread.thread_id)
        .order_by(HypothesisModel.generated_date.desc())
        .first()
    )

    if prior:
        # Carry forward core fields if missing on the new instance
        _inherit_field(h_data, prior, "source_theory")
        _inherit_field(h_data, prior, "source_theories")
        _inherit_field(h_data, prior, "full_statement")
        _inherit_field(h_data, prior, "predicted_assets")
        _inherit_field(h_data, prior, "asset_direction")
        _inherit_field(h_data, prior, "timeframe")
        _inherit_field(h_data, prior, "resolution_channel")
        _inherit_field(h_data, prior, "hard_falsifiers")
        _inherit_field(h_data, prior, "predicted_magnitude_lower")
        _inherit_field(h_data, prior, "predicted_magnitude_upper")
        _inherit_field(h_data, prior, "timeframe_end_date")

        # Inherit soft falsifiers with accumulated untestable_consecutive counters
        if not h_data.get("soft_falsifiers") or h_data["soft_falsifiers"] == "[]":
            h_data["soft_falsifiers"] = prior.soft_falsifiers or "[]"
        else:
            _inherit_falsifier_counters(h_data, prior)

        # Fix placeholder short_name from parser (e.g. "[CONFIRM] T-xxx-01")
        if h_data.get("short_name", "").startswith("[CONFIRM]") or h_data.get("short_name", "").startswith("[UPDATE]"):
            h_data["short_name"] = prior.short_name

    return h_data


def _inherit_field(h_data: dict, prior: HypothesisModel, field: str) -> None:
    """Copy a field from the prior instance if the new instance has no value."""
    current = h_data.get(field)
    # Treat empty string, None, "unknown", and "[]" as missing
    if not current or current in ("unknown", "[]", "{}"):
        prior_val = getattr(prior, field, None)
        if prior_val is not None:
            h_data[field] = prior_val


def _inherit_falsifier_counters(h_data: dict, prior: HypothesisModel) -> None:
    """Carry forward untestable_consecutive counters from the prior instance.

    For each soft falsifier on the new instance that matches a prior falsifier
    by name, inherit the untestable_consecutive counter. This preserves the
    accumulation that feeds into ESCALATED_UNTESTABLE detection.
    """
    try:
        new_sf = json.loads(h_data.get("soft_falsifiers", "[]"))
        prior_sf = json.loads(prior.soft_falsifiers or "[]")
    except (json.JSONDecodeError, TypeError):
        return

    # Build lookup by falsifier name
    prior_by_name = {}
    for sf in prior_sf:
        name = sf.get("name", "").lower().strip()
        if name:
            prior_by_name[name] = sf

    for sf in new_sf:
        name = sf.get("name", "").lower().strip()
        if name and name in prior_by_name:
            prior_counter = prior_by_name[name].get("untestable_consecutive", 0)
            sf.setdefault("untestable_consecutive", prior_counter)
            # Inherit generation_market_value for staleness gate
            gmv = prior_by_name[name].get("generation_market_value")
            if gmv is not None:
                sf.setdefault("generation_market_value", gmv)

    h_data["soft_falsifiers"] = json.dumps(new_sf)


def _get_current_prices_for_threads(db: Session, run: Run) -> dict[str, float]:
    """Get current price snapshot for thread entry prices.

    Uses existing RunPriceSnapshot if available, otherwise returns empty dict.
    The full price capture happens later during elimination import.
    """
    # Check if this run already has price snapshots (from a prior step)
    snapshots = db.query(RunPriceSnapshot).filter(RunPriceSnapshot.run_id == run.id).all()
    if snapshots:
        return {s.ticker: s.price for s in snapshots}

    # Try loading from briefing packet market data as fallback
    briefing = _load_briefing()
    markets = briefing.get("markets", {})
    prices = {}
    for ticker, data in markets.items():
        if isinstance(data, dict) and "price" in data:
            prices[ticker] = data["price"]
        elif isinstance(data, (int, float)):
            prices[ticker] = float(data)
    return prices


def _get_or_create_active_run(db: Session, activation_results=None) -> Run:
    """Get the current active (partial) run, or create a new one."""
    latest = db.query(Run).order_by(desc(Run.timestamp)).first()
    if latest and latest.status != "complete":
        return latest

    run_id = f"R-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    activation_json = None
    if activation_results:
        activation_json = json.dumps([ar.model_dump() for ar in activation_results])

    # Snapshot the briefing packet at run creation time
    briefing_data = _load_briefing()
    briefing_json = json.dumps(briefing_data) if briefing_data else None

    run = Run(
        id=run_id,
        timestamp=datetime.now().isoformat(),
        status="partial",
        activation_scores=activation_json,
        briefing_snapshot=briefing_json,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
