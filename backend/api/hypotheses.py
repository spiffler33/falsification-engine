# hypotheses.py -- Hypothesis CRUD + delta endpoint.
# Depends on: db/database.py, db/models.py, schemas/hypothesis.py
# Depended on by: main.py (router registration)
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Hypothesis as HypothesisModel
from backend.db.models import JournalEntry, InboxItem, Run

router = APIRouter(tags=["hypotheses"])


def _model_to_dict(h: HypothesisModel, db: Session) -> dict:
    """Convert a SQLAlchemy Hypothesis row to the frontend Hypothesis shape."""
    hard_f = json.loads(h.hard_falsifiers) if h.hard_falsifiers else []
    soft_f = json.loads(h.soft_falsifiers) if h.soft_falsifiers else []
    conv_math = json.loads(h.conviction_math) if h.conviction_math else None
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
        "age": age,
        "delta_type": delta_type,
        "has_action": has_action,
        "research_notes": research_notes,
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
