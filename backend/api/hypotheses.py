# hypotheses.py -- Hypothesis CRUD + delta endpoint.
# Depends on: db/database.py, db/models.py, schemas/hypothesis.py
# Depended on by: main.py (router registration)
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Hypothesis as HypothesisModel
from backend.db.models import JournalEntry, InboxItem, Run, RunPriceSnapshot, SectorFalsifierAudit
from backend.realization import compute_expression_return, compute_realization_ratios, compute_time_elapsed_pct

router = APIRouter(tags=["hypotheses"])

SECTOR_DISPLAY_NAMES = {
    "tech_ai": "Technology / AI Concentration",
    "energy": "Energy",
    "financials": "Financials",
}


def _build_falsifier_condition_map() -> dict[str, str]:
    """Build falsifier_id -> condition text lookup from sector appendix dicts."""
    from backend.engine.sector_appendices import (
        TECH_AI_APPENDIX, ENERGY_APPENDIX, FINANCIALS_APPENDIX,
    )
    mapping: dict[str, str] = {}
    for appendix in (TECH_AI_APPENDIX, ENERGY_APPENDIX, FINANCIALS_APPENDIX):
        for mf in appendix.get("mechanical_falsifiers", []):
            mapping[mf["falsifier_id"]] = mf["condition"]
    return mapping


_FALSIFIER_CONDITIONS: dict[str, str] = _build_falsifier_condition_map()


def _model_to_dict(h: HypothesisModel, db: Session, *, for_snapshot: bool = False) -> dict:
    """Convert a SQLAlchemy Hypothesis row to the frontend Hypothesis shape."""
    hard_f = json.loads(h.hard_falsifiers) if h.hard_falsifiers else []
    soft_f = json.loads(h.soft_falsifiers) if h.soft_falsifiers else []
    conv_math = None if for_snapshot else (json.loads(h.conviction_math) if h.conviction_math else None)
    assets = json.loads(h.predicted_assets) if h.predicted_assets else []
    directions = json.loads(h.asset_direction) if h.asset_direction else {}
    source_theories = json.loads(h.source_theories) if h.source_theories else [h.source_theory]

    # Compute falsifier health
    triggered = sum(1 for sf in soft_f if sf.get("status") == "TRIGGERED")

    # Compute age
    try:
        gen_date = date.fromisoformat(h.generated_date)
        age = (date.today() - gen_date).days
    except (ValueError, TypeError):
        age = 0

    # Check for journal actions
    has_action = db.query(JournalEntry).filter(JournalEntry.hypothesis_id == h.id).first() is not None

    # Get research notes (inbox items linked to this hypothesis)
    # Skipped in snapshot mode — saves ~2-5 KB per hypothesis + a DB query
    if for_snapshot:
        research_notes = []
    else:
        notes = db.query(InboxItem).filter(InboxItem.hypothesis_id == h.id).all()
        research_notes = [
            {
                "id": n.id,
                "date": n.date,
                "type": n.type,
                "content": n.content,
                "source": n.source or "",
            }
            for n in notes
        ]

    # Get conviction history from prior runs
    prior = (
        db.query(HypothesisModel.conviction)
        .filter(
            HypothesisModel.short_name == h.short_name,
            HypothesisModel.source_theory == h.source_theory,
            HypothesisModel.conviction.isnot(None),
        )
        .order_by(HypothesisModel.generated_date)
        .all()
    )
    conviction_history = [row[0] for row in prior if row[0] is not None]

    # Conviction previous (from prior run of same hypothesis)
    conviction_prev = conviction_history[-2] if len(conviction_history) >= 2 else h.conviction or 0.0

    # Delta type
    delta_type = _compute_delta_type(h, conviction_prev)

    # Theory label
    from backend.engine.prompt_builder import THEORY_LABEL_MAP
    source_theory_label = THEORY_LABEL_MAP.get(h.source_theory, h.source_theory)

    return {
        "id": h.id,
        "run_id": h.run_id,
        "short_name": h.short_name,
        "full_statement": h.full_statement or "",
        "source_theory": h.source_theory,
        "source_theory_label": source_theory_label,
        "source_theories": source_theories,
        "generated_date": h.generated_date,
        "status": h.status,
        "conviction": h.conviction or 0.0,
        "conviction_prev": conviction_prev,
        "conviction_history": conviction_history,
        "conviction_math": conv_math,
        "hard_falsifiers": hard_f,
        "soft_falsifiers": soft_f,
        "falsifier_health": {"triggered": triggered, "total": len(soft_f)},
        "predicted_assets": assets,
        "asset_direction": directions,
        "timeframe": h.timeframe or "",
        "resolution_channel": h.resolution_channel or "",
        "resolution_channel_original": h.resolution_channel_original or "",
        "elimination_notes": h.elimination_notes or "",
        "sector_appendices_applied": [
            {"sector_id": sid, "display_name": SECTOR_DISPLAY_NAMES.get(sid, sid)}
            for sid in (json.loads(h.sector_appendices_applied) if h.sector_appendices_applied else [])
        ],
        # Skipped in snapshot mode — saves ~2-5 KB per hypothesis + a DB query
        "sector_falsifier_audit": [] if for_snapshot else [
            {
                "id": a.id,
                "sector_id": a.sector_id,
                "falsifier_id": a.falsifier_id,
                "condition": _FALSIFIER_CONDITIONS.get(a.falsifier_id, a.falsifier_id),
                "metric_value_found": a.metric_value_found or "",
                "triggered": a.triggered,
                "relevant": a.relevant,
                "reasoning": a.reasoning or "",
                "severity_applied": a.severity_applied or "NONE",
            }
            for a in db.query(SectorFalsifierAudit)
            .filter(SectorFalsifierAudit.hypothesis_id == h.id)
            .all()
        ],
        "age": age,
        "delta_type": delta_type,
        "has_action": has_action,
        "research_notes": research_notes,
        "outcome_status": h.outcome_status,
        "outcome_date": h.outcome_date,
        "outcome_notes": h.outcome_notes,
        "outcome_pnl_pct": h.outcome_pnl_pct,
        # v6: Realization primitives (stored at scoring time)
        "predicted_magnitude_lower": h.predicted_magnitude_lower,
        "predicted_magnitude_upper": h.predicted_magnitude_upper,
        "timeframe_end_date": h.timeframe_end_date,
        "expression_return": h.expression_return,
        "realization_vs_lower": h.realization_vs_lower,
        "realization_vs_upper": h.realization_vs_upper,
        "time_elapsed_pct": h.time_elapsed_pct,
        # v6: Continuation lineage
        "continuation_of": h.continuation_of,
        "continuation_generation": h.continuation_generation or 1,
        "continuation_justification": h.continuation_justification,
    }


def _compute_delta_type(h: HypothesisModel, conviction_prev: float) -> str:
    if h.status == "KILLED":
        return "KILLED"
    current = h.conviction or 0.0
    diff = current - conviction_prev
    if diff > 0.5:
        return "IMPROVED"
    if diff < -0.5:
        return "DETERIORATED"
    return "STABLE"


@router.get("/hypotheses")
def list_hypotheses(
    status: Optional[str] = Query(None),
    theory_id: Optional[str] = Query(None),
    asset: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(HypothesisModel)
    if status:
        query = query.filter(HypothesisModel.status == status.upper())
    if theory_id:
        query = query.filter(HypothesisModel.source_theory == theory_id)
    # Default sort: conviction descending
    query = query.order_by(desc(HypothesisModel.conviction))
    rows = query.all()

    results = [_model_to_dict(h, db) for h in rows]

    # Asset filter (post-query since it's in a JSON column)
    if asset:
        asset_upper = asset.upper()
        results = [
            r for r in results
            if asset_upper in [a.upper() for a in r["predicted_assets"]]
        ]

    return results


@router.get("/hypotheses/delta")
def get_delta(
    since_run_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Return categorized hypothesis changes since a specific run."""
    all_hyps = db.query(HypothesisModel).order_by(desc(HypothesisModel.conviction)).all()
    all_dicts = [_model_to_dict(h, db) for h in all_hyps]

    if not since_run_id:
        # No previous review: everything is NEW
        return {
            "killed": [],
            "deteriorated": [],
            "improved": [],
            "new_hypotheses": all_dicts,
            "stable": [],
        }

    # Find hypotheses from the reference run
    ref_hyps = db.query(HypothesisModel).filter(HypothesisModel.run_id == since_run_id).all()
    ref_ids = {h.id for h in ref_hyps}
    ref_map = {h.id: h for h in ref_hyps}

    killed = []
    deteriorated = []
    improved = []
    new_hypotheses = []
    stable = []

    for d in all_dicts:
        if d["id"] not in ref_ids:
            new_hypotheses.append(d)
        elif d["status"] == "KILLED":
            ref = ref_map.get(d["id"])
            if ref and ref.status != "KILLED":
                killed.append(d)
            else:
                stable.append(d)
        elif d["delta_type"] == "DETERIORATED":
            deteriorated.append(d)
        elif d["delta_type"] == "IMPROVED":
            improved.append(d)
        else:
            stable.append(d)

    return {
        "killed": killed,
        "deteriorated": deteriorated,
        "improved": improved,
        "new_hypotheses": new_hypotheses,
        "stable": stable,
    }


@router.get("/hypotheses/{hypothesis_id}")
def get_hypothesis(hypothesis_id: str, db: Session = Depends(get_db)):
    h = db.query(HypothesisModel).filter(HypothesisModel.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail=f"Hypothesis {hypothesis_id} not found")
    return _model_to_dict(h, db)


@router.patch("/hypotheses/{hypothesis_id}/outcome")
def record_outcome(hypothesis_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Record the walk-forward outcome for a hypothesis."""
    h = db.query(HypothesisModel).filter(HypothesisModel.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail=f"Hypothesis {hypothesis_id} not found")

    VALID_STATUSES = {"CORRECT", "INCORRECT", "PARTIAL", "EXPIRED"}
    status = payload.get("outcome_status", "").upper()
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"outcome_status must be one of: {', '.join(sorted(VALID_STATUSES))}")

    notes = payload.get("outcome_notes", "").strip()
    if not notes:
        raise HTTPException(status_code=422, detail="outcome_notes is required -- state WHY this verdict")

    h.outcome_status = status
    h.outcome_notes = notes
    h.outcome_date = date.today().isoformat()
    h.outcome_pnl_pct = payload.get("outcome_pnl_pct")

    db.commit()
    return _model_to_dict(h, db)


@router.get("/hypotheses/{hypothesis_id}/history")
def get_conviction_history(hypothesis_id: str, db: Session = Depends(get_db)):
    """Return conviction score history for sparkline display."""
    h = db.query(HypothesisModel).filter(HypothesisModel.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail=f"Hypothesis {hypothesis_id} not found")

    # Find all versions of this hypothesis across runs
    prior = (
        db.query(HypothesisModel.run_id, HypothesisModel.conviction, HypothesisModel.generated_date)
        .filter(
            HypothesisModel.short_name == h.short_name,
            HypothesisModel.source_theory == h.source_theory,
            HypothesisModel.conviction.isnot(None),
        )
        .order_by(HypothesisModel.generated_date)
        .all()
    )

    return [
        {"run_id": row[0], "conviction": row[1], "date": row[2]}
        for row in prior
    ]


@router.get("/hypotheses/{hypothesis_id}/realization")
def get_hypothesis_realization(hypothesis_id: str, db: Session = Depends(get_db)):
    """Compute and return realization primitives for a single hypothesis."""
    from backend.api.trades import _fetch_current_price

    h = db.query(HypothesisModel).filter(HypothesisModel.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail=f"Hypothesis {hypothesis_id} not found")

    assets = json.loads(h.predicted_assets) if h.predicted_assets else []
    directions = json.loads(h.asset_direction) if h.asset_direction else {}

    # Entry prices from the originating run's price snapshots
    snapshots = db.query(RunPriceSnapshot).filter(RunPriceSnapshot.run_id == h.run_id).all()
    entry_prices = {s.ticker: s.price for s in snapshots}

    # Fetch current prices
    current_prices: dict[str, float] = {}
    for ticker in assets:
        price = _fetch_current_price(ticker)
        if price is not None:
            current_prices[ticker] = price

    # Compute expression return
    expr_return = compute_expression_return(assets, directions, entry_prices, current_prices)

    # Build per-leg detail
    legs = []
    for ticker in assets:
        entry_p = entry_prices.get(ticker)
        current_p = current_prices.get(ticker)
        leg_return = None
        if entry_p and current_p and entry_p > 0:
            raw = (current_p - entry_p) / entry_p
            if directions.get(ticker, "LONG") == "SHORT":
                raw = -raw
            leg_return = round(raw, 6)
        legs.append({
            "ticker": ticker,
            "direction": directions.get(ticker, "LONG"),
            "entry": entry_p,
            "current": current_p,
            "return": leg_return,
        })

    # Realization ratios (only if payoff band is set)
    realization_vs_lower = None
    realization_vs_upper = None
    if expr_return is not None and h.predicted_magnitude_lower and h.predicted_magnitude_upper:
        ratios = compute_realization_ratios(
            expr_return, h.predicted_magnitude_lower, h.predicted_magnitude_upper
        )
        realization_vs_lower = ratios.get("realization_vs_lower")
        realization_vs_upper = ratios.get("realization_vs_upper")

    # Time elapsed (only if timeframe_end_date is set)
    time_elapsed = None
    run = db.query(Run).filter(Run.id == h.run_id).first()
    entry_date_str = run.price_snapshot_date if run else None
    if h.timeframe_end_date and entry_date_str:
        time_elapsed = compute_time_elapsed_pct(entry_date_str, h.timeframe_end_date)

    return {
        "hypothesis_id": h.id,
        "expression_return": round(expr_return, 6) if expr_return is not None else None,
        "legs": legs,
        "realization_vs_lower": round(realization_vs_lower, 3) if realization_vs_lower is not None else None,
        "realization_vs_upper": round(realization_vs_upper, 3) if realization_vs_upper is not None else None,
        "time_elapsed_pct": round(time_elapsed, 4) if time_elapsed is not None else None,
        "payoff_band": {
            "lower": h.predicted_magnitude_lower,
            "upper": h.predicted_magnitude_upper,
            "end_date": h.timeframe_end_date,
        },
        "as_of_date": date.today().isoformat(),
        "continuation_of": None,
        "continuation_generation": 1,
    }
