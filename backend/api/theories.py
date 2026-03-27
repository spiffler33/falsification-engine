# theories.py -- Theory listing and activation score endpoints.
# Depends on: engine/theory_parser.py, engine/activation.py, schemas/briefing.py
# Depended on by: main.py (router registration)
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.engine import activation, theory_parser
from backend.engine.prompt_builder import THEORY_LABEL_MAP
from backend.schemas.briefing import BriefingPacket

router = APIRouter(tags=["theories"])


def _load_briefing_packet() -> dict | None:
    from backend.config import DATA_DIR, MOCK_DATA_DIR

    for path in [DATA_DIR / "briefing_packet.json", MOCK_DATA_DIR / "briefing_packet.json"]:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


@router.get("/theories")
def list_theories():
    """Return all theory modules with current activation scores."""
    theories = theory_parser.load_all_theories()
    briefing_data = _load_briefing_packet()

    activation_results = []
    if briefing_data:
        briefing = BriefingPacket(**briefing_data)
        activation_results = activation.score_all_theories(theories, briefing)

    ar_map = {ar.theory_id: ar for ar in activation_results}

    result = []
    for t in theories:
        ar = ar_map.get(t.theory_id)
        label = THEORY_LABEL_MAP.get(t.theory_id, t.theory_id)

        entry = {
            "theory_id": t.theory_id,
            "title": t.title or label,
            "label": label,
            "is_two_phase": t.is_two_phase,
            "hard_falsifier_count": len(t.hard_falsifiers),
            "soft_falsifier_count": len(t.soft_falsifiers),
            "prediction_count": len(t.directional_predictions),
        }

        if ar:
            entry["activation"] = ar.model_dump()
        else:
            entry["activation"] = None

        result.append(entry)

    return result


@router.get("/theories/activation")
def get_activation_scores():
    """Return current activation tier and score for all theories."""
    theories = theory_parser.load_all_theories()
    briefing_data = _load_briefing_packet()

    if not briefing_data:
        return {"error": "No briefing packet available", "scores": []}

    briefing = BriefingPacket(**briefing_data)
    results = activation.score_all_theories(theories, briefing)

    return {
        "scores": [ar.model_dump() for ar in results],
        "active": [ar.theory_id for ar in results
                    if (ar.tier if not ar.is_two_phase else ar.effective_tier) == activation.ActivationTier.ACTIVE],
        "adjacent": [ar.theory_id for ar in results
                     if (ar.tier if not ar.is_two_phase else ar.effective_tier) == activation.ActivationTier.ADJACENT],
        "inactive": [ar.theory_id for ar in results
                     if (ar.tier if not ar.is_two_phase else ar.effective_tier) == activation.ActivationTier.INACTIVE],
    }


@router.get("/theories/{theory_id}")
def get_theory(theory_id: str):
    """Return a single theory module with full detail."""
    theories = theory_parser.load_all_theories()
    for t in theories:
        if t.theory_id == theory_id:
            briefing_data = _load_briefing_packet()
            ar = None
            if briefing_data:
                briefing = BriefingPacket(**briefing_data)
                ar = activation.score_theory(t, briefing)

            return {
                "theory": t.model_dump(),
                "activation": ar.model_dump() if ar else None,
                "label": THEORY_LABEL_MAP.get(theory_id, theory_id),
            }

    raise HTTPException(status_code=404, detail=f"Theory {theory_id} not found")
