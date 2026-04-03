# threads.py -- Thread list + detail endpoints for thread-centered views.
# Depends on: db/database.py, db/models.py
# Depended on by: main.py (router registration), frontend ObservatoryView, ThreadDetail overlay
from __future__ import annotations

import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Hypothesis as HypothesisModel
from backend.db.models import HypothesisThread, InboxItem, JournalEntry, SectorFalsifierAudit

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


def _instance_to_detail(h: HypothesisModel, db: Session, *, for_snapshot: bool = False) -> dict:
    """Full instance dict for ThreadDetail overlay (same depth as hypotheses/_model_to_dict)."""
    hard_f = json.loads(h.hard_falsifiers) if h.hard_falsifiers else []
    soft_f = json.loads(h.soft_falsifiers) if h.soft_falsifiers else []
    conv_math = json.loads(h.conviction_math) if h.conviction_math else None
    assets = json.loads(h.predicted_assets) if h.predicted_assets else []
    directions = json.loads(h.asset_direction) if h.asset_direction else {}
    source_theories = json.loads(h.source_theories) if h.source_theories else [h.source_theory]

    triggered = sum(1 for sf in soft_f if sf.get("status") == "TRIGGERED")

    from backend.api.hypotheses import _FALSIFIER_CONDITIONS, SECTOR_DISPLAY_NAMES

    # Research notes + sector audit skipped in snapshot mode (saves DB queries + payload size)
    if for_snapshot:
        research_notes = []
        sector_audit = []
    else:
        # Research notes (inbox items linked to this instance)
        notes = db.query(InboxItem).filter(InboxItem.hypothesis_id == h.id).all()
        research_notes = [
            {"id": n.id, "date": n.date, "type": n.type, "content": n.content, "source": n.source or ""}
            for n in notes
        ]

        # Sector falsifier audit
        sector_audit = [
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
        ]

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
        "conviction_math": conv_math,
        "hard_falsifiers": hard_f,
        "soft_falsifiers": soft_f,
        "falsifier_health": {"triggered": triggered, "total": len(soft_f)},
        "predicted_assets": assets,
        "asset_direction": directions,
        "timeframe": h.timeframe or "",
        "resolution_channel": h.resolution_channel or "",
        "elimination_notes": h.elimination_notes or "",
        "sector_appendices_applied": [
            {"sector_id": sid, "display_name": SECTOR_DISPLAY_NAMES.get(sid, sid)}
            for sid in (json.loads(h.sector_appendices_applied) if h.sector_appendices_applied else [])
        ],
        "sector_falsifier_audit": sector_audit,
        "research_notes": research_notes,
        # Realization
        "predicted_magnitude_lower": h.predicted_magnitude_lower,
        "predicted_magnitude_upper": h.predicted_magnitude_upper,
        "timeframe_end_date": h.timeframe_end_date,
        "expression_return": h.expression_return,
        "realization_vs_lower": h.realization_vs_lower,
        "realization_vs_upper": h.realization_vs_upper,
        "time_elapsed_pct": h.time_elapsed_pct,
        # Lifecycle
        "lifecycle_action": h.lifecycle_action,
        "lifecycle_reasoning": h.lifecycle_reasoning,
        # Emergent risk
        "emergent_risk_condition": h.emergent_risk_condition,
        "emergent_risk_severity": h.emergent_risk_severity,
        "emergent_risk_causal_chain": h.emergent_risk_causal_chain,
        # Outcome
        "outcome_status": h.outcome_status,
        "outcome_date": h.outcome_date,
        "outcome_notes": h.outcome_notes,
        "outcome_pnl_pct": h.outcome_pnl_pct,
        # Continuation lineage (v6)
        "continuation_of": h.continuation_of,
        "continuation_generation": h.continuation_generation or 1,
        "continuation_justification": h.continuation_justification,
    }


def _instance_to_summary(h: HypothesisModel) -> dict:
    """Compact instance summary for the lineage panel."""
    soft_f = json.loads(h.soft_falsifiers) if h.soft_falsifiers else []
    triggered = sum(1 for sf in soft_f if sf.get("status") == "TRIGGERED")
    stale = sum(
        1 for sf in soft_f
        if sf.get("staleness_flag") == "STALE" or sf.get("staleness_classification") == "STALE"
    )
    escalated = sum(1 for sf in soft_f if sf.get("status") == "ESCALATED_UNTESTABLE")
    untestable = sum(1 for sf in soft_f if sf.get("status") == "UNTESTABLE")

    return {
        "id": h.id,
        "run_id": h.run_id,
        "generated_date": h.generated_date,
        "lifecycle_action": h.lifecycle_action,
        "status": h.status,
        "conviction": h.conviction or 0.0,
        "falsifier_summary": {
            "triggered": triggered,
            "total": len(soft_f),
            "stale": stale,
            "escalated": escalated,
            "untestable": untestable,
        },
        "has_emergent_risk": bool(h.emergent_risk_condition),
    }


@router.get("/threads/{thread_id}")
def get_thread_detail(thread_id: str, db: Session = Depends(get_db)):
    """Return full thread detail: thread metadata, latest instance (full), all instances (compact)."""
    thread = db.query(HypothesisThread).filter(HypothesisThread.thread_id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

    # All instances in this thread, newest first
    instances = (
        db.query(HypothesisModel)
        .filter(HypothesisModel.thread_id == thread.thread_id)
        .order_by(desc(HypothesisModel.generated_date), desc(HypothesisModel.run_id))
        .all()
    )
    if not instances:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} has no instances")

    latest = instances[0]

    # Thread age
    try:
        created = date.fromisoformat(thread.created_date)
        thread_age_days = (date.today() - created).days
    except (ValueError, TypeError):
        thread_age_days = 0

    # Conviction history across all instances in this thread
    conviction_history = [
        inst.conviction for inst in reversed(instances) if inst.conviction is not None
    ]

    from backend.engine.prompt_builder import THEORY_LABEL_MAP
    source_theory_label = THEORY_LABEL_MAP.get(thread.source_theory, thread.source_theory)

    return {
        # Thread identity
        "thread_id": thread.thread_id,
        "thread_status": thread.status,
        "source_theory": thread.source_theory,
        "source_theory_label": source_theory_label,
        "created_date": thread.created_date,
        "thread_age_days": thread_age_days,
        "confirmation_count": thread.confirmation_count or 0,
        "total_instances": thread.total_instances or 1,
        "renewed_from": thread.renewed_from,
        # Thread-level realization anchor
        "payoff_band_lower": thread.payoff_band_lower,
        "payoff_band_upper": thread.payoff_band_upper,
        "timeframe_end_date": thread.timeframe_end_date,
        # Latest instance — full detail
        "latest": _instance_to_detail(latest, db),
        # Conviction trail across instances
        "conviction_history": conviction_history,
        # All instances — compact summaries for lineage panel
        "instances": [_instance_to_summary(inst) for inst in instances],
    }
