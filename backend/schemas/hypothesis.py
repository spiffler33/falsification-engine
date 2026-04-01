# hypothesis.py — Pydantic models for the central hypothesis data object.
# Depends on: schemas/scoring.py
# Depended on by: api/hypotheses.py, api/pipeline.py, frontend
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .scoring import ConvictionMath


class HardFalsifierState(BaseModel):
    condition: str
    status: str = "passed"  # "passed" | "FAILED"
    detail: str = ""


class SoftFalsifierState(BaseModel):
    name: str
    severity: str  # "minor" | "medium" | "major"
    status: str = "clear"  # "clear" | "TRIGGERED"
    metric: str = ""
    threshold: str = ""


class FalsifierHealth(BaseModel):
    triggered: int = 0
    total: int = 0


class ResearchNote(BaseModel):
    id: str
    date: str
    type: str = "note"  # "link" | "note"
    content: str
    source: str = ""


class Hypothesis(BaseModel):
    """Central data object matching FRONTEND_SPEC Section 5."""
    # Identity
    id: str
    run_id: str
    short_name: str
    full_statement: str = ""

    # Provenance
    source_theory: str
    source_theory_label: str = ""
    source_theories: list[str] = []
    generated_date: str = ""

    # Pipeline state
    status: str = "SURVIVED"  # SURVIVED | WOUNDED | KILLED
    conviction: float = 0.0
    conviction_prev: float = 0.0
    conviction_history: list[float] = []

    # Conviction math
    conviction_math: Optional[ConvictionMath] = None

    # Falsifiers
    hard_falsifiers: list[HardFalsifierState] = []
    soft_falsifiers: list[SoftFalsifierState] = []
    falsifier_health: FalsifierHealth = FalsifierHealth()

    # Predictions
    predicted_assets: list[str] = []
    asset_direction: dict[str, str] = {}  # ticker → "LONG" | "SHORT"
    timeframe: str = ""

    # Elimination
    elimination_notes: str = ""

    # Metadata
    age: int = 0
    delta_type: str = "NEW"  # NEW | IMPROVED | DETERIORATED | KILLED | STABLE

    # Continuation lineage
    continuation_of: Optional[str] = None  # Parent hypothesis ID
    continuation_generation: int = 1  # 1=original, 2=first continuation, etc.
    continuation_justification: Optional[str] = None

    # Human annotations
    has_action: bool = False
    research_notes: list[ResearchNote] = []
