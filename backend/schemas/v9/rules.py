"""v9 canonical rule schema — the rule AST for runtime evaluation.

This is a discriminated union on the `rule_type` field. The runtime
evaluator pattern-matches on rule_type and dispatches to the appropriate
evaluation primitive. No prose interpretation. No regex. Just typed rules.

Supported rule types:
  1. scalar_comparison  — field vs literal threshold
  2. field_comparison   — field vs field (optionally with offset/derived fn)
  3. compound           — boolean all/any over sub-rules
  4. persistence        — n-of-last-k temporal pattern
  5. trend_state        — directional trend over window
  6. historical_extreme — above/below N-period high/low
  7. named_pattern      — well-known statistical patterns (Sahm Rule, etc.)
  8. delta_change       — absolute or percent change over window

Design decisions:
  - Discriminated union via Literal rule_type, not optional-field wrapper.
    The spike used Optional fields for each rule type on a wrapper model.
    That pattern is fragile (multiple fields can be non-None). A proper
    discriminated union on rule_type is the canonical v9 pattern.
  - Every operand carries its unit. The runtime normalizes before comparing.
  - Rules are recursively composable via compound.
  - Named patterns are escape hatches for complex statistical patterns
    that don't decompose cleanly into primitives (Sahm Rule, etc.).
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field

from backend.schemas.v9.units import SemanticType, TimeWindow, ValueUnit


# ---------------------------------------------------------------------------
# Comparators
# ---------------------------------------------------------------------------

class Comparator(str, Enum):
    """Comparison operators for rules."""
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"


class CompoundOperator(str, Enum):
    """Boolean operators for compound rules."""
    ALL = "all"   # AND — all sub-rules must be true
    ANY = "any"   # OR  — at least one sub-rule must be true


class TrendDirection(str, Enum):
    """Directional state for trend rules."""
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"


class ExtremeType(str, Enum):
    """Which extreme to check against."""
    HIGH = "high"
    LOW = "low"


class PersistenceMode(str, Enum):
    """How to count persistence."""
    N_OF_LAST_K = "n_of_last_k"      # at least n of last k periods
    CONSECUTIVE = "consecutive"        # n consecutive periods


class DeltaMode(str, Enum):
    """Whether delta_change measures absolute or percent change."""
    ABSOLUTE = "absolute"
    PERCENT = "percent"


# ---------------------------------------------------------------------------
# Operands — left/right sides of comparisons
# ---------------------------------------------------------------------------

class FieldOperand(BaseModel):
    """A reference to a briefing packet field."""
    operand_type: Literal["field"] = "field"
    field_id: str                           # canonical field registry ID
    unit: ValueUnit = ValueUnit.UNKNOWN     # declared unit of this field
    semantic_type: SemanticType = SemanticType.LEVEL  # what kind of quantity


class LiteralOperand(BaseModel):
    """A fixed numeric threshold."""
    operand_type: Literal["literal"] = "literal"
    value: float
    unit: ValueUnit = ValueUnit.DIMENSIONLESS


class DerivedOperand(BaseModel):
    """A value computed from a named function over fields.

    Used for cases like "nominal GDP growth" which requires
    a computation, not a direct field lookup.
    """
    operand_type: Literal["derived"] = "derived"
    function_name: str                      # e.g., "nominal_gdp_growth"
    arguments: list[str] = []               # field_ids as inputs
    unit: ValueUnit = ValueUnit.UNKNOWN
    semantic_type: SemanticType = SemanticType.LEVEL


Operand = Annotated[
    Union[FieldOperand, LiteralOperand, DerivedOperand],
    Field(discriminator="operand_type"),
]


# ---------------------------------------------------------------------------
# Rule types
# ---------------------------------------------------------------------------

class ScalarComparisonRule(BaseModel):
    """Compare a field's value against a literal threshold.

    Example: "CAPE above 30" -> field=shiller_cape, comparator=gt, threshold=30
    """
    rule_type: Literal["scalar_comparison"] = "scalar_comparison"
    field: FieldOperand
    comparator: Comparator
    threshold: LiteralOperand


class FieldComparisonRule(BaseModel):
    """Compare two fields (or a field and a derived value) against each other.

    Example: "Fed funds below nominal GDP growth"
      -> left=FieldOperand(fed_funds), comparator=lt, right=DerivedOperand(nominal_gdp_growth)
    """
    rule_type: Literal["field_comparison"] = "field_comparison"
    left: Operand
    comparator: Comparator
    right: Operand
    offset: Optional[LiteralOperand] = None  # optional: left <cmp> right + offset


class CompoundRule(BaseModel):
    """Boolean combination of sub-rules.

    ALL = all sub-rules must be true (AND)
    ANY = at least one sub-rule must be true (OR)
    """
    rule_type: Literal["compound"] = "compound"
    operator: CompoundOperator
    clauses: list["Rule"]


class PersistenceRule(BaseModel):
    """Check a condition over a time window with persistence semantics.

    Example: "Net liquidity positive for 2 of last 3 months"
      -> condition: scalar_comparison(net_liquidity, gt, 0)
         mode: n_of_last_k, n=2, k=3, window_unit=months

    Example: "Fed funds above 4% for 12 consecutive months"
      -> condition: scalar_comparison(fed_funds, gt, 4.0)
         mode: consecutive, n=12, window_unit=months
    """
    rule_type: Literal["persistence"] = "persistence"
    condition: "Rule"                       # the per-period condition to check
    mode: PersistenceMode
    n: int                                  # must satisfy n periods
    k: Optional[int] = None                 # out of last k (only for n_of_last_k)
    window: TimeWindow                      # the time unit for periods


class TrendStateRule(BaseModel):
    """Check directional trend over a window.

    Example: "ISM declining for 3+ months"
      -> field=ism_proxy, direction=falling, window=3 months
    """
    rule_type: Literal["trend_state"] = "trend_state"
    field: FieldOperand
    direction: TrendDirection
    window: TimeWindow


class HistoricalExtremeRule(BaseModel):
    """Check against historical extreme (high or low) over a lookback window.

    Example: "QQQ/IWM ratio above 2-year high"
      -> field=qqq_iwm_ratio, extreme=high, lookback=24 months, comparator=gt
    """
    rule_type: Literal["historical_extreme"] = "historical_extreme"
    field: FieldOperand
    extreme: ExtremeType
    lookback: TimeWindow
    comparator: Comparator                  # typically gt for "above high", lt for "below low"
    margin: Optional[LiteralOperand] = None  # "within 10% of record high" -> margin=0.10


class NamedPatternRule(BaseModel):
    """A well-known statistical pattern with a named deterministic evaluator.

    Used for complex patterns that don't decompose cleanly into the
    primitive rule types. Each named pattern must have a registered
    evaluator in the runtime.

    Example: "Sahm Rule triggered"
      -> name=sahm_rule, params={field: unemployment_rate, threshold: 0.50, ...}

    Example: "Yield curve re-steepened after deep inversion"
      -> name=resteepened_after_inversion, params={curve_field: curve_2s10s, ...}
    """
    rule_type: Literal["named_pattern"] = "named_pattern"
    name: str                               # registered pattern name
    params: dict[str, Any] = {}             # pattern-specific parameters
    field_dependencies: list[str] = []      # field_ids needed for evaluation


class DeltaChangeRule(BaseModel):
    """Check absolute or percent change over a time window.

    Example: "TGA declining by $100B+ over 60 days"
      -> field=tga, direction=falling, magnitude=100.0,
         magnitude_unit=usd_billions, mode=absolute, window=60 days

    This was identified in the full-compilation spike as a gap:
    ~3-5 indicators need this pattern. Using lookback_extreme as a
    workaround is semantically imprecise.
    """
    rule_type: Literal["delta_change"] = "delta_change"
    field: FieldOperand
    direction: TrendDirection               # rising or falling
    magnitude: LiteralOperand               # minimum absolute or percent change
    mode: DeltaMode                         # absolute or percent
    window: TimeWindow


# ---------------------------------------------------------------------------
# The Rule union — discriminated on rule_type
# ---------------------------------------------------------------------------

Rule = Annotated[
    Union[
        ScalarComparisonRule,
        FieldComparisonRule,
        CompoundRule,
        PersistenceRule,
        TrendStateRule,
        HistoricalExtremeRule,
        NamedPatternRule,
        DeltaChangeRule,
    ],
    Field(discriminator="rule_type"),
]

# Rebuild forward refs for recursive CompoundRule
CompoundRule.model_rebuild()


# ---------------------------------------------------------------------------
# Named pattern registry — patterns that must have runtime evaluators
# ---------------------------------------------------------------------------

REGISTERED_NAMED_PATTERNS: set[str] = {
    "sahm_rule",
    "resteepened_after_inversion",
    "breakout_after_range",
}
