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
    triggered_soft_falsifiers: List[Dict] = []  # [{severity: ...}] inputs that produced D_f
    untestable_discount: float = 0.0      # the D_u multiplier for UNTESTABLE falsifiers
    untestable_soft_falsifiers: List[Dict] = []  # [{severity: ..., status: ...}] inputs that produced D_u
    sector_falsifier_discount: float = 1.0  # sector-level D_f multiplier (triggered AND relevant only)
    sector_falsifier_entries: List[Dict] = []  # sector audit entries that produced discounts
    regime_discount: float = 1.0          # the D_r multiplier from channel-regime alignment
    overlap_same_theory: int = 0          # same-theory overlap count input
    overlap_diff_theory: int = 0          # cross-theory overlap count input
    overlap_adjustment: float = 0.0       # additive: same-theory penalty + cross-theory bonus
    adjusted: float = 0.0                 # (raw * D_f * D_u * D_r) + overlap_adjustment


class Stage3Gates(BaseModel):
    """Stage 3: Hard caps from horizon alignment, expression efficiency, and realization."""
    horizon_score: float = 0.0
    horizon_cap: Optional[float] = None
    expression_score: float = 0.0
    expression_cap: Optional[float] = None
    realization_cap: Optional[float] = None
    freshness_label: str = ""
    final: float = 0.0
    floor_killed: bool = False
    kill_reason: str = ""


class ConvictionMath(BaseModel):
    """Full three-stage conviction scoring breakdown."""
    stage1: Stage1Raw = Stage1Raw()
    stage2: Stage2Discounts = Stage2Discounts()
    stage3: Stage3Gates = Stage3Gates()


class MechanicalConvictionInputs(BaseModel):
    """Mechanically computed Stage 1 inputs — no LLM involvement."""
    support_strength: float = 0.0
    evidence_quality: float = 0.0
    convergence: float = 0.0
    falsifier_clarity: float = 0.0


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
    untestable_soft_falsifiers: List[Dict] = []  # [{severity: ..., status: "UNTESTABLE"|"ESCALATED_UNTESTABLE"}]
    same_theory_overlap: int = 0   # other surviving hypotheses on same asset from same theory
    diff_theory_overlap: int = 0   # other surviving hypotheses on same asset from different theories
    resolution_channel: str = ""   # one of RESOLUTION_CHANNELS keys, for regime alignment
    active_regime_flags: List[Dict] = []  # active flags from compute_regime_flags()
    # Stage 3 inputs
    sector_falsifier_audit: List[Dict] = []  # parsed sector audit entries from output_parser
    horizon_alignment: float = 0.0  # H, 0.0-1.0
    expression_efficiency: float = 0.0  # E, 0.0-1.0
    freshness_label: str = ""  # v6: from compute_freshness_label() — drives realization cap
