"""Deterministic series primitives for v9 compiled evaluation.

These primitives are the ONLY operations the evaluator can perform.
No prose interpretation. No LLM calls. Just math on data.

For the spike, most primitives operate on the latest snapshot value
since the frozen briefing packet is a single point-in-time snapshot.
Trend/persistence/lookback primitives require time-series data and are
marked as NOT_EVALUABLE when only a snapshot is available.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from backend.schemas.briefing import BriefingPacket
from backend.schemas.v9_spike.compiled_activation import (
    CompoundOp,
    CompoundRule,
    CompiledRule,
    FieldComparisonRule,
    LookbackExtremeRule,
    Operator,
    PersistenceRule,
    ScalarComparisonRule,
    TrendRule,
)


class EvalResult(str, Enum):
    """Result of evaluating a single rule."""
    TRUE = "true"
    FALSE = "false"
    NOT_EVALUABLE = "not_evaluable"  # requires time-series data we don't have


def resolve_field(briefing: BriefingPacket, field_path: str) -> Optional[float]:
    """Resolve a field reference from the briefing packet.

    Handles:
    - Dotted paths (growth.unemployment)
    - Computed fields (equity_risk_premium)
    - Web-sourced fields (shiller_cape)
    - Ticker references (^VIX)
    - UNRESOLVED: prefixed fields (returns None)
    """
    if field_path.startswith("UNRESOLVED:"):
        return None
    return briefing.get_field(field_path)


def compare_values(actual: float, operator: Operator, threshold: float) -> bool:
    """Apply a comparison operator."""
    if operator == Operator.GT:
        return actual > threshold
    elif operator == Operator.GTE:
        return actual >= threshold
    elif operator == Operator.LT:
        return actual < threshold
    elif operator == Operator.LTE:
        return actual <= threshold
    elif operator == Operator.EQ:
        return abs(actual - threshold) < 1e-9
    elif operator == Operator.BETWEEN:
        # For BETWEEN, threshold is the lower bound; we need upper bound from context.
        # This is handled at the compound rule level.
        return False
    return False


def eval_scalar_comparison(
    rule: ScalarComparisonRule, briefing: BriefingPacket,
) -> tuple[EvalResult, dict]:
    """Evaluate a scalar comparison rule."""
    value = resolve_field(briefing, rule.field)
    if value is None:
        return EvalResult.NOT_EVALUABLE, {"field": rule.field, "reason": "field_not_found"}

    triggered = compare_values(value, rule.operator, rule.value)
    return (
        EvalResult.TRUE if triggered else EvalResult.FALSE,
        {"field": rule.field, "value": value, "threshold": rule.value,
         "operator": rule.operator.value},
    )


def eval_field_comparison(
    rule: FieldComparisonRule, briefing: BriefingPacket,
) -> tuple[EvalResult, dict]:
    """Evaluate a field-to-field comparison rule."""
    val_a = resolve_field(briefing, rule.field_a)
    val_b = resolve_field(briefing, rule.field_b)

    if val_a is None:
        return EvalResult.NOT_EVALUABLE, {"reason": f"field_a not found: {rule.field_a}"}
    if val_b is None:
        return EvalResult.NOT_EVALUABLE, {"reason": f"field_b not found: {rule.field_b}"}

    # Compare: field_a <op> (field_b + offset)
    effective_b = val_b + rule.offset
    triggered = compare_values(val_a, rule.operator, effective_b)
    return (
        EvalResult.TRUE if triggered else EvalResult.FALSE,
        {"field_a": rule.field_a, "value_a": val_a,
         "field_b": rule.field_b, "value_b": val_b,
         "offset": rule.offset, "operator": rule.operator.value},
    )


def eval_trend(
    rule: TrendRule, briefing: BriefingPacket,
    time_series: dict[str, list[float]] | None = None,
) -> tuple[EvalResult, dict]:
    """Evaluate a trend rule.

    Requires time-series data. With only a snapshot, returns NOT_EVALUABLE.
    """
    if time_series and rule.field in time_series:
        series = time_series[rule.field]
        if len(series) < 2:
            return EvalResult.NOT_EVALUABLE, {"reason": "series too short"}

        # Simple directional check: is the series monotonically trending?
        diffs = [series[i+1] - series[i] for i in range(len(series) - 1)]
        if rule.direction.value == "rising":
            triggered = all(d > 0 for d in diffs)
        elif rule.direction.value == "falling":
            triggered = all(d < 0 for d in diffs)
        else:
            triggered = all(abs(d) < 0.01 for d in diffs)

        return (
            EvalResult.TRUE if triggered else EvalResult.FALSE,
            {"field": rule.field, "series_len": len(series),
             "direction": rule.direction.value},
        )

    return EvalResult.NOT_EVALUABLE, {
        "field": rule.field,
        "reason": "requires_time_series",
        "window": f"{rule.window_value} {rule.window_unit.value}",
    }


def eval_persistence(
    rule: PersistenceRule, briefing: BriefingPacket,
    time_series: dict[str, list[float]] | None = None,
) -> tuple[EvalResult, dict]:
    """Evaluate a persistence (n-of-last-k) rule. Requires time-series data."""
    if time_series and rule.field in time_series:
        series = time_series[rule.field]
        if len(series) < rule.k:
            return EvalResult.NOT_EVALUABLE, {
                "reason": f"series too short: need {rule.k}, have {len(series)}",
            }

        recent = series[-rule.k:]
        matching = sum(
            1 for v in recent
            if compare_values(v, rule.condition_operator, rule.condition_value)
        )
        triggered = matching >= rule.n
        return (
            EvalResult.TRUE if triggered else EvalResult.FALSE,
            {"field": rule.field, "matching": matching,
             "n": rule.n, "k": rule.k},
        )

    return EvalResult.NOT_EVALUABLE, {
        "field": rule.field,
        "reason": "requires_time_series",
        "n_of_k": f"{rule.n}/{rule.k} {rule.period_unit.value}",
    }


def eval_lookback_extreme(
    rule: LookbackExtremeRule, briefing: BriefingPacket,
    time_series: dict[str, list[float]] | None = None,
) -> tuple[EvalResult, dict]:
    """Evaluate a lookback extreme rule. Requires time-series data."""
    if time_series and rule.field in time_series:
        series = time_series[rule.field]
        if not series:
            return EvalResult.NOT_EVALUABLE, {"reason": "empty series"}

        extreme = max(series) if rule.extreme_type == "high" else min(series)
        current = resolve_field(briefing, rule.field)
        if current is None:
            return EvalResult.NOT_EVALUABLE, {"reason": "current value not found"}

        triggered = compare_values(current, rule.operator, extreme)
        return (
            EvalResult.TRUE if triggered else EvalResult.FALSE,
            {"field": rule.field, "current": current,
             "extreme": extreme, "extreme_type": rule.extreme_type},
        )

    return EvalResult.NOT_EVALUABLE, {
        "field": rule.field,
        "reason": "requires_time_series",
        "lookback": f"{rule.lookback_value} {rule.lookback_unit.value}",
    }


def eval_compound(
    rule: CompoundRule, briefing: BriefingPacket,
    time_series: dict[str, list[float]] | None = None,
) -> tuple[EvalResult, dict]:
    """Evaluate a compound (AND/OR) rule."""
    sub_results = []
    for sub_rule in rule.rules:
        result, detail = eval_rule(sub_rule, briefing, time_series)
        sub_results.append({"result": result, "detail": detail})

    evaluable = [r for r in sub_results if r["result"] != EvalResult.NOT_EVALUABLE]
    not_evaluable = [r for r in sub_results if r["result"] == EvalResult.NOT_EVALUABLE]

    if not evaluable:
        return EvalResult.NOT_EVALUABLE, {
            "reason": "all sub-rules not evaluable",
            "sub_results": sub_results,
        }

    if rule.operator == CompoundOp.ALL:
        # ALL: true only if all evaluable are true AND none are not_evaluable
        all_true = all(r["result"] == EvalResult.TRUE for r in evaluable)
        if not_evaluable:
            # Some sub-rules couldn't be evaluated — conservative: NOT_EVALUABLE
            if all_true:
                return EvalResult.NOT_EVALUABLE, {
                    "reason": "some sub-rules not evaluable (AND requires all)",
                    "evaluable_all_true": True,
                    "sub_results": sub_results,
                }
            else:
                return EvalResult.FALSE, {"sub_results": sub_results}
        triggered = all_true
    else:
        # ANY: true if any evaluable is true
        triggered = any(r["result"] == EvalResult.TRUE for r in evaluable)

    return (
        EvalResult.TRUE if triggered else EvalResult.FALSE,
        {"operator": rule.operator.value, "sub_results": sub_results},
    )


def eval_rule(
    rule: CompiledRule, briefing: BriefingPacket,
    time_series: dict[str, list[float]] | None = None,
) -> tuple[EvalResult, dict]:
    """Evaluate any compiled rule against a briefing packet.

    This is the main dispatch function.
    """
    active = rule.active_rule()
    if active is None:
        return EvalResult.NOT_EVALUABLE, {"reason": "empty rule"}

    if isinstance(active, ScalarComparisonRule):
        return eval_scalar_comparison(active, briefing)
    elif isinstance(active, FieldComparisonRule):
        return eval_field_comparison(active, briefing)
    elif isinstance(active, TrendRule):
        return eval_trend(active, briefing, time_series)
    elif isinstance(active, PersistenceRule):
        return eval_persistence(active, briefing, time_series)
    elif isinstance(active, LookbackExtremeRule):
        return eval_lookback_extreme(active, briefing, time_series)
    elif isinstance(active, CompoundRule):
        return eval_compound(active, briefing, time_series)
    else:
        return EvalResult.NOT_EVALUABLE, {"reason": f"unknown rule type: {type(active)}"}
