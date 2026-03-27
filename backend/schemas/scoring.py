# scoring.py — Pydantic models for the three-stage conviction scoring pipeline.
# Depends on: nothing
# Depended on by: engine/conviction.py, api/hypotheses.py
from typing import Dict, List, Optional

from pydantic import BaseModel


class Stage1Raw(BaseModel):
    """Stage 1: Raw conviction from epistemic quality dimensions."""
    support_strength: float = 0.0   # 0.0-1.0, weight 0.30
    evidence_quality: float = 0.0   # 0.0-1.0, weight 0.30
    convergence: float = 0.0        # 0.0-1.0, weight 0.25
    falsifier_clarity: float = 0.0  # 0.0-1.0, weight 0.15
    raw: float = 0.0                # weighted sum, scaled to 0-10


class Stage2Discounts(BaseModel):
    """Stage 2: Multiplicative discounts from falsifier health and overlap."""
    soft_falsifier_discount: float = 0.0  # the D_f multiplier (0.05 to 1.0)
    overlap_penalty: float = 0.0          # the D_o multiplier
    adjusted: float = 0.0                 # raw * D_f * D_o, scaled to 0-10


class Stage3Gates(BaseModel):
    """Stage 3: Hard caps from horizon alignment and expression efficiency."""
    horizon_score: float = 0.0
    horizon_cap: Optional[float] = None
    expression_score: float = 0.0
    expression_cap: Optional[float] = None
    final: float = 0.0


class ConvictionMath(BaseModel):
    """Full three-stage conviction scoring breakdown."""
    stage1: Stage1Raw = Stage1Raw()
    stage2: Stage2Discounts = Stage2Discounts()
    stage3: Stage3Gates = Stage3Gates()


class ConvictionInput(BaseModel):
    """Input to the conviction scoring pipeline for a single hypothesis."""
    hypothesis_id: str
    # Stage 1 inputs (from evaluator output or manual assessment)
    support_strength: float = 0.0
    evidence_quality: float = 0.0
    convergence: float = 0.0
    falsifier_clarity: float = 0.0
    # Stage 2 inputs
    triggered_soft_falsifiers: List[Dict] = []  # [{severity: "minor"|"medium"|"major"}]
    overlap_count: int = 0  # number of other hypotheses sharing primary instrument
    # Stage 3 inputs
    horizon_alignment: float = 0.0  # H, 0.0-1.0
    expression_efficiency: float = 0.0  # E, 0.0-1.0
