"""Compiled activation artifact schema for v9 spike.

This schema represents the OUTPUT of the Haiku semantic compiler.

Each indicator's English threshold/direction description is compiled into
a deterministic rule object that the Python evaluator can execute without
interpreting prose.

Rule type taxonomy:
- scalar_comparison: "Above 30", "Below 1.0%"
- field_comparison:  "Fed funds below nominal GDP growth"
- trend:            "declining for 3+ months"
- persistence:      "positive for 2 of last 3 months"
- lookback_extreme: "above 2-year high"
- compound:         boolean combinations (all/any) of sub-rules
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel


class Operator(str, Enum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    BETWEEN = "between"


class TrendDirection(str, Enum):
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"


class TimeUnit(str, Enum):
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    QUARTERS = "quarters"
    YEARS = "years"


class ValueUnit(str, Enum):
    PERCENT = "percent"
    BASIS_POINTS = "basis_points"
    RATIO = "ratio"
    INDEX_POINTS = "index_points"
    THOUSANDS = "thousands"
    MILLIONS = "millions"
    BILLIONS = "billions"
    TRILLIONS = "trillions"
    DOLLARS = "dollars"
    DIMENSIONLESS = "dimensionless"
    UNKNOWN = "unknown"


class CompoundOp(str, Enum):
    ALL = "all"
    ANY = "any"


class AmbiguityLevel(str, Enum):
    NONE = "none"
    LOW = "low"        # minor interpretation needed, high confidence
    MEDIUM = "medium"  # meaningful interpretation, moderate confidence
    HIGH = "high"      # significant ambiguity, low confidence


# --- Rule types ---

class ScalarComparisonRule(BaseModel):
    """Compare a field's latest value against a fixed threshold."""
    rule_type: str = "scalar_comparison"
    field: str                      # briefing packet field path
    operator: Operator
    value: float
    unit: ValueUnit = ValueUnit.DIMENSIONLESS


class FieldComparisonRule(BaseModel):
    """Compare two briefing fields against each other."""
    rule_type: str = "field_comparison"
    field_a: str                    # e.g., "rates.fed_funds"
    field_b: str                    # e.g., "growth.gdp_latest" (nominal growth rate)
    operator: Operator              # field_a <op> field_b
    offset: float = 0.0            # field_a <op> field_b + offset
    unit: ValueUnit = ValueUnit.DIMENSIONLESS


class TrendRule(BaseModel):
    """Check directional trend over a time window."""
    rule_type: str = "trend"
    field: str
    direction: TrendDirection
    window_value: int
    window_unit: TimeUnit
    unit: ValueUnit = ValueUnit.DIMENSIONLESS


class PersistenceRule(BaseModel):
    """Check n-of-last-k pattern (e.g., 'positive for 2 of last 3 months')."""
    rule_type: str = "persistence"
    field: str
    condition_operator: Operator    # the per-period condition
    condition_value: float
    n: int                          # must satisfy n periods
    k: int                          # out of last k periods
    period_unit: TimeUnit


class LookbackExtremeRule(BaseModel):
    """Check against historical extreme (e.g., 'above 2-year high')."""
    rule_type: str = "lookback_extreme"
    field: str
    extreme_type: str               # "high" or "low"
    lookback_value: int
    lookback_unit: TimeUnit
    operator: Operator              # typically GT for "above X-year high"


class CompoundRule(BaseModel):
    """Boolean combination of sub-rules."""
    rule_type: str = "compound"
    operator: CompoundOp            # all = AND, any = OR
    rules: List["CompiledRule"]


# Union of all rule types
RuleUnion = Union[
    ScalarComparisonRule,
    FieldComparisonRule,
    TrendRule,
    PersistenceRule,
    LookbackExtremeRule,
    CompoundRule,
]


class CompiledRule(BaseModel):
    """Wrapper that dispatches to the correct rule type."""
    scalar_comparison: Optional[ScalarComparisonRule] = None
    field_comparison: Optional[FieldComparisonRule] = None
    trend: Optional[TrendRule] = None
    persistence: Optional[PersistenceRule] = None
    lookback_extreme: Optional[LookbackExtremeRule] = None
    compound: Optional[CompoundRule] = None

    def active_rule(self) -> Optional[RuleUnion]:
        """Return the single active rule, or None."""
        for field_name in (
            "scalar_comparison", "field_comparison", "trend",
            "persistence", "lookback_extreme", "compound",
        ):
            val = getattr(self, field_name)
            if val is not None:
                return val
        return None

    @property
    def rule_type(self) -> str:
        r = self.active_rule()
        return r.rule_type if r else "empty"


# --- Compiled indicator ---

class CompiledIndicator(BaseModel):
    """A single compiled indicator — the output of Haiku compilation."""
    indicator_name: str
    source_text: str                # original English threshold + direction
    rule: CompiledRule
    weight: float
    direction_label: str            # original direction string (above, below, etc.)
    field_refs: List[str]           # all briefing packet fields referenced
    unit: ValueUnit = ValueUnit.DIMENSIONLESS
    ambiguity: AmbiguityLevel = AmbiguityLevel.NONE
    ambiguity_notes: str = ""       # explain what was ambiguous
    compiler_warnings: List[str] = []
    requires_time_series: bool = False  # True if rule needs historical data


class CompiledPhase(BaseModel):
    """All compiled indicators for one activation phase."""
    phase_name: str                 # "single", "phase_a", "phase_b"
    phase_label: str                # "Active", "Expansion", "Contraction"
    indicators: List[CompiledIndicator]


class CompiledTheoryActivation(BaseModel):
    """The complete compiled activation artifact for one theory."""
    theory_id: str
    is_two_phase: bool
    phases: List[CompiledPhase]
    compilation_model: str = ""     # e.g., "claude-haiku-4-5-20251001"
    compilation_timestamp: str = ""
    total_indicators: int = 0
    clean_count: int = 0            # compiled without warnings
    warning_count: int = 0          # compiled with warnings
    blocked_count: int = 0          # could not compile
    ambiguity_summary: str = ""


# Forward ref resolution for CompoundRule
CompoundRule.model_rebuild()
CompiledRule.model_rebuild()
