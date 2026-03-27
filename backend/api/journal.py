# journal.py -- Journal CRUD endpoints for decision recording.
# Depends on: db/database.py, db/models.py
# Depended on by: main.py (router registration)
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Hypothesis as HypothesisModel
from backend.db.models import JournalEntry

router = APIRouter(tags=["journal"])


@router.get("/journal")
def list_journal_entries(db: Session = Depends(get_db)):
    entries = db.query(JournalEntry).order_by(desc(JournalEntry.date)).all()
    results = []
    for e in entries:
        # Get current conviction for the linked hypothesis
        h = db.query(HypothesisModel).filter(HypothesisModel.id == e.hypothesis_id).first()
        results.append({
            "id": e.id,
            "hypothesis_id": e.hypothesis_id,
            "hypothesis_name": h.short_name if h else "",
            "hypothesis_status": h.status if h else "",
            "date": e.date,
            "action": e.action,
            "size": e.size,
            "conviction_at_entry": e.conviction_at_entry,
            "conviction_current": h.conviction if h else None,
            "reasoning": e.reasoning,
            "status": e.status,
            "outcome": e.outcome,
            "closed_date": e.closed_date,
        })
    return results


@router.post("/journal")
def create_journal_entry(payload: dict = Body(...), db: Session = Depends(get_db)):
    hypothesis_id = payload.get("hypothesis_id")
    if not hypothesis_id:
        raise HTTPException(status_code=400, detail="hypothesis_id is required")

    h = db.query(HypothesisModel).filter(HypothesisModel.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail=f"Hypothesis {hypothesis_id} not found")

    entry = JournalEntry(
        id=str(uuid.uuid4()),
        hypothesis_id=hypothesis_id,
        date=payload.get("date", date.today().isoformat()),
        action=payload.get("action", ""),
        size=payload.get("size"),
        conviction_at_entry=h.conviction,
        reasoning=payload.get("reasoning", ""),
        status="OPEN",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "id": entry.id,
        "hypothesis_id": entry.hypothesis_id,
        "date": entry.date,
        "action": entry.action,
        "size": entry.size,
        "conviction_at_entry": entry.conviction_at_entry,
        "reasoning": entry.reasoning,
        "status": entry.status,
    }


@router.patch("/journal/{entry_id}")
def update_journal_entry(entry_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Journal entry {entry_id} not found")

    if "outcome" in payload:
        entry.outcome = payload["outcome"]
    if "closed_date" in payload:
        entry.closed_date = payload["closed_date"]
        entry.status = "CLOSED"
    if "status" in payload:
        entry.status = payload["status"]
    if "reasoning" in payload:
        entry.reasoning = payload["reasoning"]

    db.commit()
    db.refresh(entry)

    return {
        "id": entry.id,
        "hypothesis_id": entry.hypothesis_id,
        "date": entry.date,
        "action": entry.action,
        "status": entry.status,
        "outcome": entry.outcome,
        "closed_date": entry.closed_date,
    }
