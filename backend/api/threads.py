# threads.py -- Thread list endpoint for thread-centered Ledger.
# Depends on: db/database.py, db/models.py
# Depended on by: main.py (router registration), frontend ObservatoryView
from __future__ import annotations

import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Hypothesis as HypothesisModel
from backend.db.models import HypothesisThread, JournalEntry

router = APIRouter(tags=["threads"])


def _thread_to_dict(thread: HypothesisThread, latest: HypothesisModel, db: Session) -> dict:
    """Build a thread-level dict with latest instance data for the Ledger."""
    # Parse JSON fields from latest instance
    soft_f = json.loads(latest.soft_falsifiers) if latest.soft_falsifiers else []
    assets = json.loads(latest.predicted_assets) if latest.predicted_assets else []
    directions = json.loads(latest.asset_direction) if latest.asset_direction else {}
    conv_math = json.loads(latest.conviction_math) if latest.conviction_math else None

    # Compute flags from soft falsifiers
    triggered = sum(1 for sf in soft_f if sf.get("status") == "TRIGGERED")
    stale_count = sum(
        1 for sf in soft_f if sf.get("staleness_flag") == "STALE"
        or sf.get("staleness_classification") == "STALE"
    )
    escalated_count = sum(
        1 for sf in soft_f if sf.get("status") == "ESCALATED_UNTESTABLE"
    )
    has_emergent_risk = bool(latest.emergent_risk_condition)

    # Thread age in days
    try:
        created = date.fromisoformat(thread.created_date)
        thread_age_days = (date.today() - created).days
    except (ValueError, TypeError):
        thread_age_days = 0

    # Conviction previous: find prior instance in this thread
    prior_instances = (
        db.query(HypothesisModel.conviction)
        .filter(
            HypothesisModel.thread_id == thread.thread_id,
            HypothesisModel.conviction.isnot(None),
            HypothesisModel.id != latest.id,
        )
        .order_by(desc(HypothesisModel.generated_date))
        .first()
    )
    conviction_prev = prior_instances[0] if prior_instances else latest.conviction or 0.0

    # Has journal action on any instance in this thread
    has_action = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.hypothesis_id.in_(
                db.query(HypothesisModel.id).filter(
                    HypothesisModel.thread_id == thread.thread_id
                )
            )
        )
        .first()
        is not None
    )

    # Theory label
    from backend.engine.prompt_builder import THEORY_LABEL_MAP
    source_theory_label = THEORY_LABEL_MAP.get(thread.source_theory, thread.source_theory)

    # Freshness label from conviction math (computed at scoring time)
    freshness_label = None
    if conv_math and conv_math.get("stage3"):
        freshness_label = conv_math["stage3"].get("freshness_label")

    return {
        # Thread identity
        "thread_id": thread.thread_id,
        "thread_status": thread.status,
        "created_date": thread.created_date,
        "thread_age_days": thread_age_days,
        "confirmation_count": thread.confirmation_count or 0,
        "total_instances": thread.total_instances or 1,
        "renewed_from": thread.renewed_from,

        # Latest instance data (for display + detail navigation)
        "id": latest.id,
        "latest_instance_id": latest.id,
        "run_id": latest.run_id,
        "short_name": latest.short_name,
        "full_statement": latest.full_statement or "",
        "source_theory": thread.source_theory,
        "source_theory_label": source_theory_label,
        "status": latest.status,
        "conviction": latest.conviction or 0.0,
        "conviction_prev": conviction_prev,
        "lifecycle_action": latest.lifecycle_action,
        "lifecycle_reasoning": latest.lifecycle_reasoning,
        "generated_date": latest.generated_date,

        # Falsifiers
        "falsifier_health": {"triggered": triggered, "total": len(soft_f)},
        "soft_falsifiers": soft_f,

        # Flags
        "stale_count": stale_count,
        "escalated_count": escalated_count,
        "has_emergent_risk": has_emergent_risk,
        "emergent_risk_condition": latest.emergent_risk_condition,
        "emergent_risk_severity": latest.emergent_risk_severity,

        # Assets + expression
        "predicted_assets": assets,
        "asset_direction": directions,
        "resolution_channel": latest.resolution_channel or "",
        "timeframe": latest.timeframe or "",

        # Realization (from latest instance)
        "realization_vs_lower": latest.realization_vs_lower,
        "realization_vs_upper": latest.realization_vs_upper,
        "time_elapsed_pct": latest.time_elapsed_pct,
        "expression_return": latest.expression_return,
        "freshness_label": freshness_label,

        # Display helpers
        "has_action": has_action,
        "age": thread_age_days,

        # Outcome (from latest instance)
        "outcome_status": latest.outcome_status,
    }


@router.get("/threads")
def list_threads(
    status: Optional[str] = Query(None, description="ACTIVE, RETIRED, or omit for all"),
    db: Session = Depends(get_db),
):
    """Return threads with latest instance data for the thread-centered Ledger."""
    query = db.query(HypothesisThread)
    if status:
        query = query.filter(HypothesisThread.status == status.upper())
    threads = query.all()

    results = []
    for thread in threads:
        # Find the latest instance for this thread (most recent by generated_date, then run_id)
        latest = (
            db.query(HypothesisModel)
            .filter(HypothesisModel.thread_id == thread.thread_id)
            .order_by(
                desc(HypothesisModel.generated_date),
                desc(HypothesisModel.run_id),
            )
            .first()
        )
        if not latest:
            continue

        results.append(_thread_to_dict(thread, latest, db))

    # Sort: ACTIVE threads first (by conviction desc), then RETIRED (by conviction desc)
    results.sort(key=lambda t: (
        0 if t["thread_status"] == "ACTIVE" else 1,
        -(t["conviction"] or 0),
    ))

    return results
