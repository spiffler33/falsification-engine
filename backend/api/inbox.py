# inbox.py -- Research inbox CRUD endpoints.
# Depends on: db/database.py, db/models.py
# Depended on by: main.py (router registration)
from __future__ import annotations

import json
import uuid
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import InboxItem

router = APIRouter(tags=["inbox"])


@router.get("/inbox")
def list_inbox(db: Session = Depends(get_db)):
    items = db.query(InboxItem).order_by(desc(InboxItem.date)).all()
    return [_item_to_dict(item) for item in items]


@router.get("/inbox/queued")
def list_queued(db: Session = Depends(get_db)):
    items = db.query(InboxItem).filter(InboxItem.status == "queued").order_by(desc(InboxItem.date)).all()
    return [_item_to_dict(item) for item in items]


@router.post("/inbox")
def add_inbox_item(payload: dict = Body(...), db: Session = Depends(get_db)):
    content = payload.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")

    # Auto-detect type
    item_type = "link" if content.startswith("http") else "note"

    theories = payload.get("theories", [])

    item = InboxItem(
        id=str(uuid.uuid4()),
        date=payload.get("date", date.today().isoformat()),
        type=item_type,
        content=content,
        source=payload.get("source"),
        theories=json.dumps(theories) if theories else None,
        hypothesis_id=payload.get("hypothesis_id"),
        status="queued",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return _item_to_dict(item)


def _item_to_dict(item: InboxItem) -> dict:
    return {
        "id": item.id,
        "date": item.date,
        "type": item.type,
        "content": item.content,
        "source": item.source,
        "theories": json.loads(item.theories) if item.theories else [],
        "hypothesis_id": item.hypothesis_id,
        "status": item.status,
        "incorporated_run_id": item.incorporated_run_id,
    }
