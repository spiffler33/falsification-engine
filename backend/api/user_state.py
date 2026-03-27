# user_state.py -- User state tracking (last_reviewed, etc).
# Depends on: db/database.py, db/models.py
# Depended on by: main.py (router registration)
from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import UserState

router = APIRouter(tags=["user_state"])


@router.get("/user/last_reviewed")
def get_last_reviewed(db: Session = Depends(get_db)):
    row = db.query(UserState).filter(UserState.key == "last_reviewed_run_id").first()
    return {"run_id": row.value if row else None}


@router.post("/user/last_reviewed")
def set_last_reviewed(payload: dict = Body(...), db: Session = Depends(get_db)):
    run_id = payload.get("run_id", "")
    row = db.query(UserState).filter(UserState.key == "last_reviewed_run_id").first()
    if row:
        row.value = run_id
    else:
        db.add(UserState(key="last_reviewed_run_id", value=run_id))
    db.commit()
    return {"run_id": run_id}
