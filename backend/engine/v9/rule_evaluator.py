"""v9 Phase 1: Deterministic rule evaluator.

Dispatches on rule_type and evaluates each rule against a briefing
packet and optional series store. Unit normalization before comparison.
Illegal comparisons rejected via field registry.

The evaluator is the core of the deterministic runtime. It:
  1. Resolves field values from the briefing packet
  2. Normalizes units so comparisons are meaningful
  3. Applies the comparison operator
  4. Returns a structured RuleResult (never raises for data issues)

Design decisions:
  - Every rule evaluation returns RuleResult, never raises.
  - Unit normalization happens at comparison time, not at data load time.
  - Semantic legality checks are done at validation time (validator.py),
    not at evaluation time. The evaluator trusts pre-validated artifacts.
  - Series-dependent rules (trend, persistence, historical_extreme,
    delta_change) require a SeriesStore. If no store is provided,
    they return NOT_EVALUABLE.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from backend.schemas.briefing import BriefingPacket
from backend.schemas.v9.field_registry import FieldRegistry
from backend.schemas.v9.rules import (
    Comparator,
    CompoundOperator,
    CompoundRule,
    DeltaChangeRule,
    DeltaMode,
    DerivedOperand,
    ExtremeType,
    FieldComparisonRule,
    FieldOperand,
    HistoricalExtremeRule,
    LiteralOperand,
    NamedPatternRule,
    PersistenceMode,
    PersistenceRule,
    Rule,
    ScalarComparisonRule,
    TrendDirection,
    TrendStateRule,
)
from backend.schemas.v9.units import (
    ValueUnit,
    can_convert,
    convert_value,
    normalize_to_common_unit,
)
from backend.engine.v9.derived_functions import evaluate_derived
from backend.engine.v9.series_engine import BriefingSeriesEngine
from backend.engine.v9.series_interface import (
    PrimitiveResultStatus,
    SeriesStore,
)


# ---------------------------------------------------------------------------
# Rule evaluation result
# ---------------------------------------------------------------------------

class RuleOutcome(str, Enum):
    """Outcome of evaluating a single rule."""
    TRUE = "true"                       # rule condition is satisfied
    FALSE = "false"                     # rule condition is not satisfied
    NOT_EVALUABLE = "not_evaluable"     # cannot evaluate (missing data, needs series)
    ERROR = "error"                     # evaluation error (illegal comparison, etc.)


class RuleResult:
    """Result of evaluating a single rule."""

    def __init__(
        self,
        outcome: RuleOutcome,
        detail: str = "",
        value: Optional[float] = None,
        threshold: Optional[float] = None,
    ):
        self.outcome = outcome
        self.detail = detail
        self.value = value
        self.threshold = threshold

    @property
    def triggered(self) -> bool:
        return self.outcome == RuleOutcome.TRUE

    @property
    def is_evaluable(self) -> bool:
        return self.outcome in (RuleOutcome.TRUE, RuleOutcome.FALSE)


# ---------------------------------------------------------------------------
# Comparator dispatch
# ---------------------------------------------------------------------------

def _apply_comparator(comparator: Comparator, left: float, right: float) -> bool:
    """Apply a comparison operator."""
    if comparator == Comparator.GT:
        return left > right
    elif comparator == Comparator.GTE:
        return left >= right
    elif comparator == Comparator.LT:
        return left < right
    elif comparator == Comparator.LTE:
        return left <= right
    elif comparator == Comparator.EQ:
        return left == right
    return False


# ---------------------------------------------------------------------------
# Operand resolution
# ---------------------------------------------------------------------------

def _resolve_field_value(
    field: FieldOperand,
    briefing: BriefingPacket,
) -> Optional[float]:
    """Resolve a field operand to its numeric value from the briefing."""
    return briefing.get_field(field.field_id)


def _resolve_operand_value(
    operand,
    briefing: BriefingPacket,
) -> tuple[Optional[float], ValueUnit]:
    """Resolve any operand type to (value, unit)."""
    if isinstance(operand, FieldOperand):
        val = _resolve_field_value(operand, briefing)
        return val, operand.unit
    elif isinstance(operand, LiteralOperand):
        return operand.value, operand.unit
    elif isinstance(operand, DerivedOperand):
        val = evaluate_derived(operand.function_name, briefing, operand.arguments)
        return val, operand.unit
    return None, ValueUnit.UNKNOWN


# ---------------------------------------------------------------------------
# Unit normalization for comparison
# ---------------------------------------------------------------------------

def _normalize_for_comparison(
    field_value: float,
    field_unit: ValueUnit,
    threshold_value: float,
    threshold_unit: ValueUnit,
    registry: Optional[FieldRegistry],
    field_id: str = "",
) -> tuple[float, float, str]:
    """Normalize field value and threshold to common units for comparison.

    Returns (normalized_field, normalized_threshold, detail_str).
    Raises ValueError if units are incompatible.
    """
    # If either unit is UNKNOWN, compare as-is (validator would have warned)
    if field_unit == ValueUnit.UNKNOWN or threshold_unit == ValueUnit.UNKNOWN:
        return field_value, threshold_value, "unknown unit, raw comparison"

    # Same unit: no conversion needed
    if field_unit == threshold_unit:
        return field_value, threshold_value, f"same unit ({field_unit.value})"

    # Try unit registry-aware resolution
    # The field's actual unit may come from the registry (more authoritative)
    actual_field_unit = field_unit
    if registry and field_id:
        reg_unit = registry.get_unit(field_id)
        if reg_unit and reg_unit != ValueUnit.UNKNOWN:
            actual_field_unit = reg_unit

    # Normalize to common unit
    try:
        norm_field, norm_thresh, common = normalize_to_common_unit(
            field_value, actual_field_unit,
            threshold_value, threshold_unit,
        )
        return (
            norm_field,
            norm_thresh,
            f"normalized: {actual_field_unit.value} + {threshold_unit.value} -> {common.value}",
        )
    except ValueError as e:
        raise ValueError(
            f"Cannot normalize {field_id} ({actual_field_unit.value}) "
            f"vs threshold ({threshold_unit.value}): {e}"
        )


# ---------------------------------------------------------------------------
# Rule evaluator
# ---------------------------------------------------------------------------

class RuleEvaluator:
    """Deterministic rule evaluator.

    Dispatches on rule_type and evaluates each rule against the
    briefing packet. Uses the field registry for unit normalization.
    """

    def __init__(
        self,
        briefing: BriefingPacket,
        registry: Optional[FieldRegistry] = None,
        series_store: Optional[SeriesStore] = None,
    ):
        self._briefing = briefing
        self._registry = registry
        self._series_engine = (
            BriefingSeriesEngine(series_store) if series_store else None
        )

    def evaluate(self, rule: Rule) -> RuleResult:
        """Evaluate a rule and return the result.

        Dispatches on rule_type to the appropriate handler.
        """
        rule_type = rule.rule_type

        if rule_type == "scalar_comparison":
            return self._eval_scalar(rule)
        elif rule_type == "field_comparison":
            return self._eval_field_comparison(rule)
        elif rule_type == "compound":
            return self._eval_compound(rule)
        elif rule_type == "persistence":
            return self._eval_persistence(rule)
        elif rule_type == "trend_state":
            return self._eval_trend(rule)
        elif rule_type == "historical_extreme":
            return self._eval_historical_extreme(rule)
        elif rule_type == "named_pattern":
            return self._eval_named_pattern(rule)
        elif rule_type == "delta_change":
            return self._eval_delta_change(rule)
        else:
            return RuleResult(
                outcome=RuleOutcome.ERROR,
                detail=f"Unknown rule_type: {rule_type}",
            )

    # ---- scalar_comparison ----

    def _eval_scalar(self, rule: ScalarComparisonRule) -> RuleResult:
        """Evaluate: field <cmp> literal threshold."""
        field_value = _resolve_field_value(rule.field, self._briefing)
        if field_value is None:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail=f"Field {rule.field.field_id} not available in briefing",
            )

        threshold_value = rule.threshold.value
        field_unit = rule.field.unit
        threshold_unit = rule.threshold.unit

        # Get authoritative field unit from registry if available
        if self._registry:
            reg_unit = self._registry.get_unit(rule.field.field_id)
            if reg_unit and reg_unit != ValueUnit.UNKNOWN:
                field_unit = reg_unit

        # Normalize units
        try:
            norm_field, norm_thresh, norm_detail = _normalize_for_comparison(
                field_value, field_unit,
                threshold_value, threshold_unit,
                self._registry, rule.field.field_id,
            )
        except ValueError as e:
            return RuleResult(
                outcome=RuleOutcome.ERROR,
                detail=str(e),
            )

        result = _apply_comparator(rule.comparator, norm_field, norm_thresh)
        return RuleResult(
            outcome=RuleOutcome.TRUE if result else RuleOutcome.FALSE,
            detail=f"{norm_field} {rule.comparator.value} {norm_thresh} ({norm_detail})",
            value=norm_field,
            threshold=norm_thresh,
        )

    # ---- field_comparison ----

    def _eval_field_comparison(self, rule: FieldComparisonRule) -> RuleResult:
        """Evaluate: left <cmp> right [+ offset]."""
        left_val, left_unit = _resolve_operand_value(rule.left, self._briefing)
        right_val, right_unit = _resolve_operand_value(rule.right, self._briefing)

        if left_val is None:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail=f"Left operand not available",
            )
        if right_val is None:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail=f"Right operand not available",
            )

        # Apply offset if present
        if rule.offset is not None:
            right_val = right_val + rule.offset.value

        # Normalize units
        try:
            norm_left, norm_right, norm_detail = _normalize_for_comparison(
                left_val, left_unit,
                right_val, right_unit,
                self._registry,
            )
        except ValueError as e:
            return RuleResult(
                outcome=RuleOutcome.ERROR,
                detail=str(e),
            )

        result = _apply_comparator(rule.comparator, norm_left, norm_right)
        return RuleResult(
            outcome=RuleOutcome.TRUE if result else RuleOutcome.FALSE,
            detail=f"{norm_left} {rule.comparator.value} {norm_right} ({norm_detail})",
            value=norm_left,
            threshold=norm_right,
        )

    # ---- compound ----

    def _eval_compound(self, rule: CompoundRule) -> RuleResult:
        """Evaluate: all/any of sub-rules."""
        if not rule.clauses:
            return RuleResult(
                outcome=RuleOutcome.ERROR,
                detail="Empty compound rule",
            )

        sub_results = [self.evaluate(clause) for clause in rule.clauses]

        evaluable = [r for r in sub_results if r.is_evaluable]
        not_evaluable = [r for r in sub_results if not r.is_evaluable]

        if not evaluable:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail=f"No evaluable sub-rules ({len(not_evaluable)} not evaluable)",
            )

        if rule.operator == CompoundOperator.ALL:
            # All evaluable must be True. Any NOT_EVALUABLE -> NOT_EVALUABLE.
            if not_evaluable:
                return RuleResult(
                    outcome=RuleOutcome.NOT_EVALUABLE,
                    detail=f"AND: {len(not_evaluable)} sub-rules not evaluable",
                )
            all_true = all(r.triggered for r in evaluable)
            return RuleResult(
                outcome=RuleOutcome.TRUE if all_true else RuleOutcome.FALSE,
                detail=f"AND: {sum(r.triggered for r in evaluable)}/{len(evaluable)} true",
            )

        elif rule.operator == CompoundOperator.ANY:
            # Any evaluable True -> True.
            any_true = any(r.triggered for r in evaluable)
            if any_true:
                return RuleResult(
                    outcome=RuleOutcome.TRUE,
                    detail=f"OR: at least one true",
                )
            # All evaluable False, but some not evaluable -> NOT_EVALUABLE
            if not_evaluable:
                return RuleResult(
                    outcome=RuleOutcome.NOT_EVALUABLE,
                    detail=f"OR: all evaluable are false, {len(not_evaluable)} not evaluable",
                )
            return RuleResult(
                outcome=RuleOutcome.FALSE,
                detail=f"OR: none of {len(evaluable)} true",
            )

        return RuleResult(
            outcome=RuleOutcome.ERROR,
            detail=f"Unknown compound operator: {rule.operator}",
        )

    # ---- persistence ----

    def _eval_persistence(self, rule: PersistenceRule) -> RuleResult:
        """Evaluate: condition true for n-of-k or consecutive periods."""
        if self._series_engine is None:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail="Persistence requires series store",
            )

        # Extract the condition's field and threshold from the inner rule
        inner = rule.condition
        field_id, cmp_fn, cmp_val = _extract_scalar_condition(inner, self._briefing)
        if field_id is None:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail="Cannot extract scalar condition from persistence inner rule",
            )

        if rule.mode == PersistenceMode.N_OF_LAST_K:
            k = rule.k if rule.k else rule.n
            result = self._series_engine.n_of_last_k(
                field_id, cmp_fn, cmp_val, rule.n, k,
            )
        elif rule.mode == PersistenceMode.CONSECUTIVE:
            result = self._series_engine.consecutive_true(
                field_id, cmp_fn, cmp_val, rule.n,
            )
        else:
            return RuleResult(
                outcome=RuleOutcome.ERROR,
                detail=f"Unknown persistence mode: {rule.mode}",
            )

        if result.status != PrimitiveResultStatus.OK:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail=result.detail,
            )

        return RuleResult(
            outcome=RuleOutcome.TRUE if result.boolean else RuleOutcome.FALSE,
            detail=result.detail,
        )

    # ---- trend_state ----

    def _eval_trend(self, rule: TrendStateRule) -> RuleResult:
        """Evaluate: field trending in direction over window."""
        if self._series_engine is None:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail="Trend requires series store",
            )

        result = self._series_engine.trend_direction(
            rule.field.field_id, rule.window,
        )
        if result.status != PrimitiveResultStatus.OK:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail=result.detail,
            )

        actual_direction = result.detail  # "rising", "falling", "stable"
        expected = rule.direction.value    # "rising", "falling", "stable"
        matches = actual_direction == expected

        return RuleResult(
            outcome=RuleOutcome.TRUE if matches else RuleOutcome.FALSE,
            detail=f"Trend: {actual_direction} (expected {expected})",
        )

    # ---- historical_extreme ----

    def _eval_historical_extreme(self, rule: HistoricalExtremeRule) -> RuleResult:
        """Evaluate: field at/near historical extreme over lookback."""
        if self._series_engine is None:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail="Historical extreme requires series store",
            )

        margin = rule.margin.value if rule.margin else 0.0
        result = self._series_engine.is_at_extreme(
            rule.field.field_id,
            rule.extreme.value,  # "high" or "low"
            rule.lookback,
            margin=margin,
        )

        if result.status != PrimitiveResultStatus.OK:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail=result.detail,
            )

        return RuleResult(
            outcome=RuleOutcome.TRUE if result.boolean else RuleOutcome.FALSE,
            detail=result.detail,
            value=result.value,
        )

    # ---- named_pattern ----

    def _eval_named_pattern(self, rule: NamedPatternRule) -> RuleResult:
        """Evaluate: registered named pattern."""
        if self._series_engine is None:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail="Named pattern requires series store",
            )

        result = self._series_engine.evaluate_named_pattern(
            rule.name, rule.params,
        )

        if result.status == PrimitiveResultStatus.ERROR:
            return RuleResult(
                outcome=RuleOutcome.ERROR,
                detail=result.detail,
            )
        if result.status != PrimitiveResultStatus.OK:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail=result.detail,
            )

        return RuleResult(
            outcome=RuleOutcome.TRUE if result.boolean else RuleOutcome.FALSE,
            detail=result.detail,
            value=result.value,
        )

    # ---- delta_change ----

    def _eval_delta_change(self, rule: DeltaChangeRule) -> RuleResult:
        """Evaluate: field changed by magnitude over window."""
        if self._series_engine is None:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail="Delta change requires series store",
            )

        if rule.mode == DeltaMode.ABSOLUTE:
            result = self._series_engine.absolute_change(
                rule.field.field_id, rule.window,
            )
        elif rule.mode == DeltaMode.PERCENT:
            result = self._series_engine.percent_change(
                rule.field.field_id, rule.window,
            )
        else:
            return RuleResult(
                outcome=RuleOutcome.ERROR,
                detail=f"Unknown delta mode: {rule.mode}",
            )

        if result.status != PrimitiveResultStatus.OK:
            return RuleResult(
                outcome=RuleOutcome.NOT_EVALUABLE,
                detail=result.detail,
            )

        change = result.value
        magnitude = rule.magnitude.value

        # Check direction and magnitude
        if rule.direction == TrendDirection.FALLING:
            triggered = change <= -magnitude
        elif rule.direction == TrendDirection.RISING:
            triggered = change >= magnitude
        else:
            return RuleResult(
                outcome=RuleOutcome.ERROR,
                detail=f"delta_change does not support direction={rule.direction.value}",
            )

        return RuleResult(
            outcome=RuleOutcome.TRUE if triggered else RuleOutcome.FALSE,
            detail=f"Change={change}, required magnitude={magnitude}, direction={rule.direction.value}",
            value=change,
            threshold=magnitude,
        )


# ---------------------------------------------------------------------------
# Helper: extract scalar condition from a rule
# ---------------------------------------------------------------------------

def _extract_scalar_condition(
    rule: Rule,
    briefing: BriefingPacket,
) -> tuple[Optional[str], Optional[str], Optional[float]]:
    """Extract (field_id, comparator_name, threshold) from a scalar rule.

    Used by persistence and other rules that wrap a scalar condition.
    Returns (None, None, None) if the rule is not a scalar comparison.
    """
    if rule.rule_type == "scalar_comparison":
        return (
            rule.field.field_id,
            rule.comparator.value,
            rule.threshold.value,
        )
    return None, None, None
