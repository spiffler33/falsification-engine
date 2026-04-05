# theory.py — Pydantic models for parsed theory modules.
# Depends on: nothing
# Depended on by: engine/theory_parser.py, engine/activation.py, api/theories.py
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel


class Direction(str, Enum):
    ABOVE = "above"
    BELOW = "below"
    RISING = "rising"
    FALLING = "falling"
    BETWEEN = "between"


class Severity(str, Enum):
    MINOR = "minor"
    MEDIUM = "medium"
    MAJOR = "major"


class ActivationTier(str, Enum):
    ACTIVE = "Active"
    ADJACENT = "Adjacent"
    INACTIVE = "Inactive"


class Indicator(BaseModel):
    """A single activation condition indicator from a theory module table."""
    name: str
    metric_source: str
    threshold: str  # kept as string — may be numeric or descriptive
    direction: Direction
    weight: float  # 0.0-1.0, or -1 for qualitative
    rationale: str = ""
    requires_web_search: bool = False
    is_qualitative: bool = False


class HardFalsifier(BaseModel):
    id: str  # e.g. "H1"
    condition: str
    metric: str
    threshold: str
    rationale: str = ""


class SoftFalsifier(BaseModel):
    id: str  # e.g. "S1"
    severity: Severity
    condition: str
    metric: str
    threshold: str
    implication: str = ""


class DirectionalPrediction(BaseModel):
    asset: str
    direction: str
    magnitude_range: str
    timeframe: str
    mechanism: str = ""


class ConditionalPrediction(BaseModel):
    type: str  # e.g. "Mechanism interaction"
    condition: str
    prediction: str
    specificity_gain: str


class DownstreamEffect(BaseModel):
    target_theory_id: str
    relationship: str  # extends, accelerates, contradicts, triggers, modifies
    description: str


class TheoryMetadata(BaseModel):
    theory_id: str
    version: int = 1
    last_updated: str = ""
    update_type: str = ""  # refinement, extension, new
    confidence_in_specification: str = ""
    notes: str = ""
    historical_episodes_referenced: list[str] = []


class ActivationPhase(BaseModel):
    """Activation conditions for a single phase of a theory module."""
    phase_name: str  # e.g. "Phase A: Fragility Building" or "single"
    phase_label: str  # e.g. "Building", "Resolving", "Expansion", "Contraction"
    indicators: list[Indicator] = []


class TheoryModule(BaseModel):
    """Complete parsed representation of a theory module markdown file."""
    theory_id: str
    title: str = ""
    is_two_phase: bool = False
    phases: list[ActivationPhase] = []  # 1 for single-phase, 2 for two-phase
    hard_falsifiers: list[HardFalsifier] = []
    soft_falsifiers: list[SoftFalsifier] = []
    directional_predictions: list[DirectionalPrediction] = []
    conditional_predictions: list[ConditionalPrediction] = []
    downstream_effects: list[DownstreamEffect] = []
    metadata: Optional[TheoryMetadata] = None
    scope_limits: str = ""
    raw_markdown: str = ""  # preserve full text for prompt building


class ActivationResult(BaseModel):
    """Result of activation scoring for a single theory."""
    theory_id: str
    is_two_phase: bool = False
    # For single-phase theories
    score: Optional[float] = None
    tier: Optional[ActivationTier] = None
    # For two-phase theories
    phase_scores: Optional[dict[str, float]] = None  # phase_label → score
    phase_tiers: Optional[dict[str, ActivationTier]] = None
    effective_tier: Optional[ActivationTier] = None
    effective_phase: Optional[str] = None  # which phase is operative
    # Details
    indicator_results: dict[str, dict] = {}  # indicator_name → {triggered, value, threshold}
    skipped_indicators: list[str] = []  # web-search or qualitative indicators


# ---------------------------------------------------------------------------
# v8 Theory Package models (four-file directory structure)
# ---------------------------------------------------------------------------

class FalsifierEntry(BaseModel):
    """Pre-joined falsifier: condition from CORE.md + classification/severity from ACTIVATION.md."""
    falsifier_id: str  # e.g. "H1", "S3"
    condition: str     # from CORE.md deep_falsifiers
    logic: str         # from CORE.md deep_falsifiers
    classification: Literal["hard", "soft"]  # from ACTIVATION.md
    severity: Optional[Severity] = None      # minor/medium/major for soft; None for hard
    discount: Optional[float] = None         # 0.10/0.25/0.45 for soft; None for hard


class IndicatorOwnership(BaseModel):
    """Data ownership classification for a scored indicator from ACTIVATION.md."""
    indicator_name: str
    metric_source: str
    data_ownership: Literal["mechanical", "computed-mechanical", "web-search", "qualitative"]
    dependencies: Optional[list[str]] = None  # for computed-mechanical only


class ContextFlag(BaseModel):
    """Qualitative context flag from ACTIVATION.md -- routed to generator, excluded from scoring."""
    flag_name: str
    source: str
    data_ownership: str
    description: str
    usage: str


class TheoryPackage(BaseModel):
    """Complete four-file theory package. Replaces monolithic TheoryModule for v8."""
    theory_id: str
    core: str          # full text of CORE.md
    activation: str    # full text of ACTIVATION.md
    tactical: str      # full text of TACTICAL.md
    playbook: str      # full text of PLAYBOOK.md
    falsifier_registry: list[FalsifierEntry] = []
    data_ownership: list[IndicatorOwnership] = []
    context_flags: list[ContextFlag] = []
