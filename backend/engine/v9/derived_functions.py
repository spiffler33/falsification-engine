"""v9 Phase 1: Derived function registry.

DerivedOperand in the rule AST references functions by name
(e.g., "nominal_gdp_growth"). This module registers those functions
and provides a dispatch mechanism for the rule evaluator.

Each derived function takes a briefing packet and returns a float
or None (if inputs are unavailable).
"""
from __future__ import annotations

from typing import Callable, Optional

from backend.schemas.briefing import BriefingPacket


# Type alias for a derived function.
# Takes a briefing packet, returns the computed value or None.
DerivedFunction = Callable[[BriefingPacket], Optional[float]]


# ---------------------------------------------------------------------------
# Derived function implementations
# ---------------------------------------------------------------------------

def _nominal_gdp_growth(briefing: BriefingPacket) -> Optional[float]:
    """Estimate nominal GDP growth rate.

    Nominal GDP growth ~ real GDP growth + inflation.
    This is needed for field_comparison rules like
    "fed funds below nominal GDP growth".
    """
    real_gdp = briefing.get_field("growth.real_gdp")
    cpi_yoy = briefing.get_field("inflation.cpi_yoy")
    if real_gdp is None or cpi_yoy is None:
        return None
    return round(real_gdp + cpi_yoy, 2)


def _nominal_gdp_growth_plus_offset(
    briefing: BriefingPacket, offset: float = 0.0,
) -> Optional[float]:
    """Nominal GDP growth + offset (for "fed funds above GDP growth + 1%")."""
    base = _nominal_gdp_growth(briefing)
    if base is None:
        return None
    return round(base + offset, 2)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

DERIVED_FUNCTION_REGISTRY: dict[str, DerivedFunction] = {
    "nominal_gdp_growth": _nominal_gdp_growth,
}


def evaluate_derived(
    function_name: str,
    briefing: BriefingPacket,
    arguments: list[str] | None = None,
) -> Optional[float]:
    """Evaluate a named derived function against a briefing packet.

    Returns the computed value, or None if the function is unknown
    or inputs are unavailable.
    """
    fn = DERIVED_FUNCTION_REGISTRY.get(function_name)
    if fn is None:
        return None
    return fn(briefing)


def is_registered(function_name: str) -> bool:
    """Check whether a derived function name is registered."""
    return function_name in DERIVED_FUNCTION_REGISTRY
