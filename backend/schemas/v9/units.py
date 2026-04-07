"""v9 canonical unit model.

This module makes it impossible to silently compare:
  - rates to levels
  - raw counts to thousands
  - billions to millions
without an explicit conversion rule.

Three layers:
  1. ValueUnit enum — what unit a number is expressed in
  2. SemanticType enum — what kind of economic quantity it represents
  3. Comparison legality — which (unit, semantic_type) pairs can be compared

The unit model is the foundation of the entire v9 contract.
If a comparison is not explicitly legal, it fails loudly.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Layer 1: Value unit — the dimensional unit of a numeric value
# ---------------------------------------------------------------------------

class ValueUnit(str, Enum):
    """The dimensional unit a numeric value is expressed in.

    Every literal and every field must declare its unit.
    Comparisons across mismatched units require explicit conversion.
    """
    # Rates and ratios
    PERCENT = "percent"                 # 3.5 means 3.5%
    BASIS_POINTS = "basis_points"       # 350 means 350bp = 3.5%
    RATIO = "ratio"                     # 1.5 means 1.5x
    SHARE = "share"                     # 0.35 means 35% (fraction, not percent)

    # Monetary amounts
    USD = "usd"                         # raw dollars
    USD_THOUSANDS = "usd_thousands"     # value in thousands of USD
    USD_MILLIONS = "usd_millions"       # value in millions of USD
    USD_BILLIONS = "usd_billions"       # value in billions of USD
    USD_TRILLIONS = "usd_trillions"     # value in trillions of USD

    # Counts
    COUNT = "count"                     # raw count (e.g., initial claims = 202000)
    THOUSANDS = "thousands"             # value in thousands (e.g., initial claims = 202)
    MILLIONS = "millions"               # value in millions
    TONS = "tons"                       # metric tons (gold purchases)

    # Index / score
    INDEX_POINTS = "index_points"       # ISM = 52.3, CAPE = 35.2
    SCORE = "score"                     # generic 0-100 or similar scores

    # Time
    MONTHS = "months"
    YEARS = "years"
    DAYS = "days"

    # Dimensionless
    DIMENSIONLESS = "dimensionless"     # unitless number (e.g., boolean-like flags)

    # Sentinel for compilation failures
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Layer 2: Semantic type — what kind of economic quantity
# ---------------------------------------------------------------------------

class SemanticType(str, Enum):
    """The economic meaning of a quantity.

    Two fields with the same ValueUnit but different SemanticType
    should NOT be compared without an explicit rule. For example:
      - fed_funds (rate) vs gdp_latest (level) are both floats,
        but comparing them is a category error.
      - equity_risk_premium (spread) vs shiller_cape (ratio) are
        both dimensionless-ish, but measure fundamentally different things.

    The semantic type constrains which comparisons are meaningful,
    independent of the unit dimension.
    """
    LEVEL = "level"                     # an absolute quantity (GDP in $B, price in $)
    RATE = "rate"                       # an interest rate, policy rate, yield
    GROWTH_RATE = "growth_rate"         # year-over-year or period change rate
    RATIO = "ratio"                     # a ratio of two quantities (P/E, debt/GDP)
    SPREAD = "spread"                   # difference between two rates (HY - IG, etc.)
    COUNT = "count"                     # a count of events or items
    PRICE = "price"                     # market price of an asset
    RETURN = "return"                   # percentage return over a period
    BALANCE = "balance"                 # an account balance or stock (RRP, TGA)
    FLOW = "flow"                       # a flow quantity per period (deficit, purchases)
    SHARE_OF_TOTAL = "share_of_total"   # a fraction of a whole (top-10 weight, passive share)
    INDEX = "index"                     # a composite index value (ISM, consumer confidence)
    CATEGORICAL_STATE = "categorical_state"  # qualitative state encoded as numeric
    DURATION = "duration"               # a time period (months of inversion, etc.)
    VOLATILITY = "volatility"           # volatility measure (VIX, realized vol)
    RELATIVE_PERFORMANCE = "relative_performance"  # relative return between two assets


# ---------------------------------------------------------------------------
# Layer 3: Comparison legality
# ---------------------------------------------------------------------------

class ComparisonClass(str, Enum):
    """Groups of semantic types that can legally be compared to each other.

    Two operands can only be compared if they belong to the same
    comparison class. This prevents category errors like comparing
    a rate to a level or a count to a price.
    """
    RATE_LIKE = "rate_like"         # rate, spread, growth_rate, return
    LEVEL_LIKE = "level_like"       # level, balance, price, flow
    RATIO_LIKE = "ratio_like"       # ratio, share_of_total
    COUNT_LIKE = "count_like"       # count
    INDEX_LIKE = "index_like"       # index, score, volatility
    RELATIVE = "relative"           # relative_performance, return
    CATEGORICAL = "categorical"     # categorical_state
    TEMPORAL = "temporal"           # duration
    DIMENSIONLESS = "dimensionless" # explicit dimensionless


# Mapping from SemanticType -> ComparisonClass
SEMANTIC_TYPE_TO_COMPARISON_CLASS: dict[SemanticType, ComparisonClass] = {
    SemanticType.LEVEL: ComparisonClass.LEVEL_LIKE,
    SemanticType.RATE: ComparisonClass.RATE_LIKE,
    SemanticType.GROWTH_RATE: ComparisonClass.RATE_LIKE,
    SemanticType.RATIO: ComparisonClass.RATIO_LIKE,
    SemanticType.SPREAD: ComparisonClass.RATE_LIKE,
    SemanticType.COUNT: ComparisonClass.COUNT_LIKE,
    SemanticType.PRICE: ComparisonClass.LEVEL_LIKE,
    SemanticType.RETURN: ComparisonClass.RATE_LIKE,
    SemanticType.BALANCE: ComparisonClass.LEVEL_LIKE,
    SemanticType.FLOW: ComparisonClass.LEVEL_LIKE,
    SemanticType.SHARE_OF_TOTAL: ComparisonClass.RATIO_LIKE,
    SemanticType.INDEX: ComparisonClass.INDEX_LIKE,
    SemanticType.CATEGORICAL_STATE: ComparisonClass.CATEGORICAL,
    SemanticType.DURATION: ComparisonClass.TEMPORAL,
    SemanticType.VOLATILITY: ComparisonClass.INDEX_LIKE,
    SemanticType.RELATIVE_PERFORMANCE: ComparisonClass.RELATIVE,
}


def get_comparison_class(semantic_type: SemanticType) -> ComparisonClass:
    """Get the comparison class for a semantic type."""
    cls = SEMANTIC_TYPE_TO_COMPARISON_CLASS.get(semantic_type)
    if cls is None:
        raise ValueError(f"No comparison class defined for semantic type: {semantic_type}")
    return cls


def are_comparable(type_a: SemanticType, type_b: SemanticType) -> bool:
    """Check whether two semantic types can legally be compared.

    Returns True if both types map to the same comparison class.
    Returns False otherwise — the comparison requires an explicit
    conversion or is a category error.
    """
    return get_comparison_class(type_a) == get_comparison_class(type_b)


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------

# Conversion factors: (from_unit, to_unit) -> multiply factor
# If a pair is not in this table, no automatic conversion exists.
UNIT_CONVERSIONS: dict[tuple[ValueUnit, ValueUnit], float] = {
    # Rate conversions
    (ValueUnit.PERCENT, ValueUnit.BASIS_POINTS): 100.0,
    (ValueUnit.BASIS_POINTS, ValueUnit.PERCENT): 0.01,
    (ValueUnit.SHARE, ValueUnit.PERCENT): 100.0,
    (ValueUnit.PERCENT, ValueUnit.SHARE): 0.01,

    # Monetary scale conversions
    (ValueUnit.USD, ValueUnit.USD_THOUSANDS): 0.001,
    (ValueUnit.USD, ValueUnit.USD_MILLIONS): 1e-6,
    (ValueUnit.USD, ValueUnit.USD_BILLIONS): 1e-9,
    (ValueUnit.USD, ValueUnit.USD_TRILLIONS): 1e-12,
    (ValueUnit.USD_THOUSANDS, ValueUnit.USD): 1_000.0,
    (ValueUnit.USD_THOUSANDS, ValueUnit.USD_MILLIONS): 0.001,
    (ValueUnit.USD_THOUSANDS, ValueUnit.USD_BILLIONS): 1e-6,
    (ValueUnit.USD_MILLIONS, ValueUnit.USD): 1_000_000.0,
    (ValueUnit.USD_MILLIONS, ValueUnit.USD_BILLIONS): 0.001,
    (ValueUnit.USD_MILLIONS, ValueUnit.USD_TRILLIONS): 1e-6,
    (ValueUnit.USD_BILLIONS, ValueUnit.USD): 1e9,
    (ValueUnit.USD_BILLIONS, ValueUnit.USD_MILLIONS): 1_000.0,
    (ValueUnit.USD_BILLIONS, ValueUnit.USD_TRILLIONS): 0.001,
    (ValueUnit.USD_TRILLIONS, ValueUnit.USD): 1e12,
    (ValueUnit.USD_TRILLIONS, ValueUnit.USD_BILLIONS): 1_000.0,
    (ValueUnit.USD_TRILLIONS, ValueUnit.USD_MILLIONS): 1_000_000.0,

    # Count scale conversions
    (ValueUnit.COUNT, ValueUnit.THOUSANDS): 0.001,
    (ValueUnit.THOUSANDS, ValueUnit.COUNT): 1_000.0,
    (ValueUnit.COUNT, ValueUnit.MILLIONS): 1e-6,
    (ValueUnit.MILLIONS, ValueUnit.COUNT): 1_000_000.0,
    (ValueUnit.THOUSANDS, ValueUnit.MILLIONS): 0.001,
    (ValueUnit.MILLIONS, ValueUnit.THOUSANDS): 1_000.0,

    # Identity (optimization for common case)
    (ValueUnit.PERCENT, ValueUnit.PERCENT): 1.0,
    (ValueUnit.BASIS_POINTS, ValueUnit.BASIS_POINTS): 1.0,
    (ValueUnit.COUNT, ValueUnit.COUNT): 1.0,
    (ValueUnit.USD_BILLIONS, ValueUnit.USD_BILLIONS): 1.0,
    (ValueUnit.INDEX_POINTS, ValueUnit.INDEX_POINTS): 1.0,
    (ValueUnit.RATIO, ValueUnit.RATIO): 1.0,
}


def can_convert(from_unit: ValueUnit, to_unit: ValueUnit) -> bool:
    """Check whether a unit conversion exists."""
    if from_unit == to_unit:
        return True
    return (from_unit, to_unit) in UNIT_CONVERSIONS


def convert_value(value: float, from_unit: ValueUnit, to_unit: ValueUnit) -> float:
    """Convert a value between units.

    Raises ValueError if no conversion exists.
    """
    if from_unit == to_unit:
        return value
    factor = UNIT_CONVERSIONS.get((from_unit, to_unit))
    if factor is None:
        raise ValueError(
            f"No conversion from {from_unit.value} to {to_unit.value}. "
            f"This comparison requires explicit unit handling."
        )
    return value * factor


def normalize_to_common_unit(
    value_a: float, unit_a: ValueUnit,
    value_b: float, unit_b: ValueUnit,
) -> tuple[float, float, ValueUnit]:
    """Normalize two values to a common unit for comparison.

    Prefers the unit of value_a as the target. If that conversion
    doesn't exist, tries value_b's unit as target. If neither works,
    raises ValueError.

    Returns (normalized_a, normalized_b, common_unit).
    """
    if unit_a == unit_b:
        return value_a, value_b, unit_a

    # Try converting b to a's unit
    if can_convert(unit_b, unit_a):
        return value_a, convert_value(value_b, unit_b, unit_a), unit_a

    # Try converting a to b's unit
    if can_convert(unit_a, unit_b):
        return convert_value(value_a, unit_a, unit_b), value_b, unit_b

    raise ValueError(
        f"Cannot normalize units: {unit_a.value} and {unit_b.value} "
        f"have no common conversion."
    )


# ---------------------------------------------------------------------------
# Operand model — a value with its unit
# ---------------------------------------------------------------------------

class UnitValue(BaseModel):
    """A numeric value with explicit unit declaration.

    Used for literal thresholds in rules. Every threshold the compiler
    emits must carry its unit. The runtime uses this for normalization
    before comparison.
    """
    value: float
    unit: ValueUnit

    def convert_to(self, target_unit: ValueUnit) -> "UnitValue":
        """Return a new UnitValue converted to the target unit."""
        return UnitValue(
            value=convert_value(self.value, self.unit, target_unit),
            unit=target_unit,
        )


# ---------------------------------------------------------------------------
# Time window model — used by temporal rules
# ---------------------------------------------------------------------------

class TimeUnit(str, Enum):
    """Unit for time windows in temporal rules."""
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    QUARTERS = "quarters"
    YEARS = "years"


class TimeWindow(BaseModel):
    """A time window specification for temporal rules."""
    value: int
    unit: TimeUnit
