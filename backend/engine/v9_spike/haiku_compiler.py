"""Haiku semantic compiler — compiles English activation rows into deterministic rule objects.

This is the core of the v9 spike. Haiku reads the English indicator descriptions
and produces structured JSON rule objects. It runs at COMPILE TIME only, never in
the live scoring loop.

The compiler prompt is designed to:
1. Decompose English into primitive rule types (scalar, field comparison, trend, etc.)
2. Surface ambiguity explicitly rather than guessing through it
3. Resolve field references to briefing packet paths
4. Declare units so the evaluator can validate
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

import anthropic

from backend.schemas.v9_spike.compiled_activation import (
    AmbiguityLevel,
    CompiledIndicator,
    CompiledPhase,
    CompiledRule,
    CompiledTheoryActivation,
    CompoundOp,
    CompoundRule,
    FieldComparisonRule,
    LookbackExtremeRule,
    Operator,
    PersistenceRule,
    ScalarComparisonRule,
    TrendDirection,
    TrendRule,
    TimeUnit,
    ValueUnit,
)

# Known briefing packet fields — the compiler uses this to validate field refs
KNOWN_FIELDS = [
    "growth.gdp_latest", "growth.real_gdp", "growth.unemployment",
    "growth.initial_claims", "growth.ism_proxy", "growth.nonfarm_payrolls",
    "inflation.cpi_yoy", "inflation.core_pce", "inflation.breakeven_5y",
    "inflation.breakeven_10y",
    "rates.fed_funds", "rates.treasury_2y", "rates.treasury_10y",
    "rates.treasury_30y", "rates.treasury_3m", "rates.curve_2s10s",
    "rates.curve_3m10y",
    "liquidity.fed_balance_sheet", "liquidity.tga", "liquidity.reverse_repo",
    "liquidity.m2",
    "credit.hy_spread", "credit.ig_spread",
    "sentiment.consumer_sentiment",
    # Computed fields
    "equity_risk_premium", "cash_exceeds_equity_yield", "real_fed_funds_rate",
    "net_liquidity", "gold_oil_ratio", "dxy_index", "qqq_iwm_ratio",
    "vix_vs_realized", "spy_drawdown_from_52w_high", "top_10_sp500_weight",
    "fed_bs_gdp_ratio", "federal_debt_to_gdp", "deficit_pace_annualized",
    "sloos_net_tightening", "interest_receipts_ratio", "interest_exceeds_defense",
    "corporate_profits_gdp_ratio", "real_fed_funds",
    "eem_spy_3y_relative", "eem_spy_3m_relative",
    "hard_vs_nominal_12m", "commodity_index_3m_change",
    "foreign_treasury_holdings_pct",
    # Web-sourced fields
    "shiller_cape", "buffett_indicator", "sp500_net_margin",
    "insider_sell_buy_ratio", "consumer_confidence",
    "total_debt_to_gdp", "top10_wealth_share",
    "finra_margin_debt", "passive_fund_share",
    "china_credit_impulse", "em_dm_pe_gap", "usdcny",
    "rmb_swift_share", "cb_gold_purchases",
    "weighted_avg_interest_rate",
]

COMPILER_SYSTEM_PROMPT = """\
You are a semantic compiler. Your job is to translate English activation indicator \
descriptions into deterministic machine-readable rule objects.

You are NOT reasoning about markets or economics. You are doing precise \
English-to-structured-data translation.

## Rule types you can emit

1. **scalar_comparison**: Compare a field's current value against a fixed number.
   Fields: field (string), operator (gt/gte/lt/lte/eq/between), value (number), unit (string)

2. **field_comparison**: Compare two briefing packet fields.
   Fields: field_a (string), field_b (string), operator (gt/gte/lt/lte), offset (number, default 0), unit (string)

3. **trend**: Check directional trend over a time window. REQUIRES TIME SERIES DATA.
   Fields: field (string), direction (rising/falling/stable), window_value (int), window_unit (days/weeks/months/quarters/years), unit (string)

4. **persistence**: n-of-last-k pattern. REQUIRES TIME SERIES DATA.
   Fields: field (string), condition_operator (gt/lt/etc), condition_value (number), n (int), k (int), period_unit (string)

5. **lookback_extreme**: Compare against historical high/low. REQUIRES TIME SERIES DATA.
   Fields: field (string), extreme_type (high/low), lookback_value (int), lookback_unit (string), operator (gt/lt)

6. **compound**: Boolean combination of sub-rules.
   Fields: operator (all/any), rules (array of rule objects)

## Available briefing packet fields

{known_fields}

## Output format

For each indicator, return a JSON object with:
```json
{{
  "indicator_name": "exact name from input",
  "rule_type": "one of the 6 types above, or 'compound' for combinations",
  "rule": {{ ... rule-type-specific fields ... }},
  "field_refs": ["list", "of", "field.paths", "used"],
  "unit": "percent|basis_points|ratio|index_points|thousands|millions|billions|trillions|dollars|dimensionless|unknown",
  "requires_time_series": true/false,
  "ambiguity": "none|low|medium|high",
  "ambiguity_notes": "explain what was ambiguous, empty if none",
  "warnings": ["list of compiler warnings"]
}}
```

## Rules for compilation

1. NEVER GUESS. If the English is ambiguous, set ambiguity to medium/high and explain.
2. When a threshold contains BOTH a scalar AND a temporal condition (e.g., "Below 450bp AND not widening for 3+ months"), emit a compound rule with both sub-rules.
3. When the English says "X vs Y" or "X minus Y" or "X below Y", that is a field_comparison, not a scalar_comparison.
4. Map field references to the known fields list. If no match, set the field to "UNRESOLVED:<original text>" and add a warning.
5. Units must be explicit. "300bp" = basis_points, "1.0%" = percent, "1.5x" = ratio, "$500B" = billions/dollars, "250K" = thousands.
6. For compound thresholds with AND, use compound.all. For OR, use compound.any.
7. Temporal conditions (trend, persistence, lookback) ALWAYS set requires_time_series=true.
8. When a metric_source references a computed field like `equity_risk_premium`, use that exact field name.
9. When a metric_source says "web search: X", map to the closest known field name.

Return a JSON array of compiled indicator objects. No markdown, no explanation, just the JSON array.
"""


def _build_indicator_text(row: dict) -> str:
    """Format a single indicator row for the compiler prompt."""
    return (
        f"Indicator: {row['indicator_name']}\n"
        f"Metric Source: {row['metric_source']}\n"
        f"Threshold: {row['threshold']}\n"
        f"Direction: {row['direction']}\n"
        f"Weight: {row['weight']}\n"
        f"Data Ownership: {row.get('data_ownership', 'unknown')}"
    )


def _map_operator(op_str: str) -> Operator:
    """Map a string operator to the Operator enum."""
    mapping = {
        "gt": Operator.GT, ">": Operator.GT,
        "gte": Operator.GTE, ">=": Operator.GTE,
        "lt": Operator.LT, "<": Operator.LT,
        "lte": Operator.LTE, "<=": Operator.LTE,
        "eq": Operator.EQ, "==": Operator.EQ,
        "between": Operator.BETWEEN,
    }
    return mapping.get(op_str.lower(), Operator.GT)


def _map_trend_direction(d: str) -> TrendDirection:
    mapping = {
        "rising": TrendDirection.RISING,
        "falling": TrendDirection.FALLING,
        "stable": TrendDirection.STABLE,
    }
    return mapping.get(d.lower(), TrendDirection.RISING)


def _map_time_unit(u: str) -> TimeUnit:
    mapping = {
        "days": TimeUnit.DAYS, "day": TimeUnit.DAYS,
        "weeks": TimeUnit.WEEKS, "week": TimeUnit.WEEKS,
        "months": TimeUnit.MONTHS, "month": TimeUnit.MONTHS,
        "quarters": TimeUnit.QUARTERS, "quarter": TimeUnit.QUARTERS,
        "years": TimeUnit.YEARS, "year": TimeUnit.YEARS,
    }
    return mapping.get(u.lower(), TimeUnit.MONTHS)


def _map_unit(u: str) -> ValueUnit:
    mapping = {
        "percent": ValueUnit.PERCENT, "%": ValueUnit.PERCENT,
        "basis_points": ValueUnit.BASIS_POINTS, "bp": ValueUnit.BASIS_POINTS,
        "ratio": ValueUnit.RATIO, "x": ValueUnit.RATIO,
        "index_points": ValueUnit.INDEX_POINTS,
        "thousands": ValueUnit.THOUSANDS,
        "millions": ValueUnit.MILLIONS,
        "billions": ValueUnit.BILLIONS,
        "trillions": ValueUnit.TRILLIONS,
        "dollars": ValueUnit.DOLLARS,
        "dimensionless": ValueUnit.DIMENSIONLESS,
        "unknown": ValueUnit.UNKNOWN,
    }
    return mapping.get(u.lower(), ValueUnit.DIMENSIONLESS)


def _map_ambiguity(a: str) -> AmbiguityLevel:
    mapping = {
        "none": AmbiguityLevel.NONE,
        "low": AmbiguityLevel.LOW,
        "medium": AmbiguityLevel.MEDIUM,
        "high": AmbiguityLevel.HIGH,
    }
    return mapping.get(a.lower(), AmbiguityLevel.NONE)


def _parse_rule_json(rule_data: dict, rule_type: str) -> CompiledRule:
    """Parse a rule JSON object from Haiku output into a CompiledRule."""
    if rule_type == "scalar_comparison":
        return CompiledRule(scalar_comparison=ScalarComparisonRule(
            field=rule_data.get("field", "UNRESOLVED"),
            operator=_map_operator(rule_data.get("operator", "gt")),
            value=float(rule_data.get("value", 0)),
            unit=_map_unit(rule_data.get("unit", "dimensionless")),
        ))
    elif rule_type == "field_comparison":
        return CompiledRule(field_comparison=FieldComparisonRule(
            field_a=rule_data.get("field_a", "UNRESOLVED"),
            field_b=rule_data.get("field_b", "UNRESOLVED"),
            operator=_map_operator(rule_data.get("operator", "lt")),
            offset=float(rule_data.get("offset", 0)),
            unit=_map_unit(rule_data.get("unit", "dimensionless")),
        ))
    elif rule_type == "trend":
        return CompiledRule(trend=TrendRule(
            field=rule_data.get("field", "UNRESOLVED"),
            direction=_map_trend_direction(rule_data.get("direction", "rising")),
            window_value=int(rule_data.get("window_value", 3)),
            window_unit=_map_time_unit(rule_data.get("window_unit", "months")),
            unit=_map_unit(rule_data.get("unit", "dimensionless")),
        ))
    elif rule_type == "persistence":
        return CompiledRule(persistence=PersistenceRule(
            field=rule_data.get("field", "UNRESOLVED"),
            condition_operator=_map_operator(rule_data.get("condition_operator", "gt")),
            condition_value=float(rule_data.get("condition_value", 0)),
            n=int(rule_data.get("n", 1)),
            k=int(rule_data.get("k", 1)),
            period_unit=_map_time_unit(rule_data.get("period_unit", "months")),
        ))
    elif rule_type == "lookback_extreme":
        return CompiledRule(lookback_extreme=LookbackExtremeRule(
            field=rule_data.get("field", "UNRESOLVED"),
            extreme_type=rule_data.get("extreme_type", "high"),
            lookback_value=int(rule_data.get("lookback_value", 1)),
            lookback_unit=_map_time_unit(rule_data.get("lookback_unit", "years")),
            operator=_map_operator(rule_data.get("operator", "gt")),
        ))
    elif rule_type == "compound":
        sub_rules = []
        for sub in rule_data.get("rules", []):
            sub_type = sub.get("rule_type", "scalar_comparison")
            sub_rule_data = sub.get("rule", sub)
            sub_rules.append(_parse_rule_json(sub_rule_data, sub_type))
        return CompiledRule(compound=CompoundRule(
            operator=CompoundOp.ALL if rule_data.get("operator", "all") == "all" else CompoundOp.ANY,
            rules=sub_rules,
        ))
    else:
        # Unknown rule type — wrap as scalar with warning
        return CompiledRule(scalar_comparison=ScalarComparisonRule(
            field="UNRESOLVED:" + rule_type,
            operator=Operator.GT,
            value=0,
            unit=ValueUnit.UNKNOWN,
        ))


def _haiku_output_to_indicator(item: dict, weight: float, direction: str) -> CompiledIndicator:
    """Convert a single Haiku JSON output item to a CompiledIndicator."""
    rule_type = item.get("rule_type", "scalar_comparison")
    rule_data = item.get("rule", {})
    rule = _parse_rule_json(rule_data, rule_type)

    return CompiledIndicator(
        indicator_name=item.get("indicator_name", "unknown"),
        source_text=f"threshold={item.get('threshold', '')}, direction={direction}",
        rule=rule,
        weight=weight,
        direction_label=direction,
        field_refs=item.get("field_refs", []),
        unit=_map_unit(item.get("unit", "dimensionless")),
        ambiguity=_map_ambiguity(item.get("ambiguity", "none")),
        ambiguity_notes=item.get("ambiguity_notes", ""),
        compiler_warnings=item.get("warnings", []),
        requires_time_series=item.get("requires_time_series", False),
    )


class HaikuCompiler:
    """Compiles English activation rows into deterministic rule artifacts using Haiku."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-haiku-4-5-20251001"
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
        self.call_latencies: list[float] = []

    def compile_indicators(
        self,
        indicators: list[dict],
        theory_id: str,
        phase_label: str = "",
    ) -> tuple[list[CompiledIndicator], dict]:
        """Compile a batch of indicator rows via Haiku.

        Returns (compiled_indicators, stats_dict).
        """
        # Build the user prompt with all indicators
        indicator_texts = []
        for row in indicators:
            indicator_texts.append(_build_indicator_text(row))

        user_prompt = (
            f"Theory: {theory_id}\n"
            f"Phase: {phase_label}\n\n"
            f"Compile these {len(indicators)} indicators into rule objects:\n\n"
            + "\n\n---\n\n".join(indicator_texts)
        )

        system_prompt = COMPILER_SYSTEM_PROMPT.format(
            known_fields="\n".join(f"- {f}" for f in KNOWN_FIELDS)
        )

        t0 = time.time()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        latency = time.time() - t0

        # Track stats
        self.call_count += 1
        self.call_latencies.append(latency)
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens

        # Parse response
        raw_text = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            # Remove first and last fence lines
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw_text = "\n".join(lines)

        try:
            compiled_items = json.loads(raw_text)
        except json.JSONDecodeError as e:
            return [], {
                "error": f"JSON parse failed: {e}",
                "raw_response": raw_text[:500],
                "latency_s": latency,
            }

        # Convert to CompiledIndicator objects
        compiled = []
        # Build lookup for weight/direction from input rows
        row_lookup = {r["indicator_name"]: r for r in indicators}

        for item in compiled_items:
            name = item.get("indicator_name", "")
            row = row_lookup.get(name, {})
            weight = row.get("weight", 0.0)
            direction = row.get("direction", "above")
            ci = _haiku_output_to_indicator(item, weight, direction)
            # Inject source_text from original threshold + direction
            ci.source_text = f'{row.get("threshold", "")} | direction={direction}'
            compiled.append(ci)

        stats = {
            "indicators_sent": len(indicators),
            "indicators_received": len(compiled),
            "latency_s": round(latency, 2),
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        return compiled, stats

    def compile_theory(
        self,
        theory_id: str,
        activation_entries: list[dict],
    ) -> CompiledTheoryActivation:
        """Compile a full theory's activation table into a CompiledTheoryActivation.

        activation_entries: list of dicts from parse_activation_table(), each with
        indicator_name, metric_source, threshold, direction, weight, phase, data_ownership.
        """
        from datetime import datetime, timezone

        phases_present = {e.get("phase", "") for e in activation_entries}
        is_two_phase = len(phases_present) >= 2

        compiled_phases = []
        all_stats = []

        if is_two_phase:
            phase_groups: dict[str, list[dict]] = {}
            for entry in activation_entries:
                phase_groups.setdefault(entry.get("phase", ""), []).append(entry)

            for phase_str in sorted(phase_groups):
                import re
                if re.search(r"Phase\s*A\b", phase_str, re.IGNORECASE):
                    phase_name = "phase_a"
                elif re.search(r"Phase\s*B\b", phase_str, re.IGNORECASE):
                    phase_name = "phase_b"
                else:
                    phase_name = phase_str

                label_match = re.search(r"Phase\s+[AB]:\s*(.+)", phase_str)
                phase_label = label_match.group(1).strip() if label_match else phase_str

                indicators, stats = self.compile_indicators(
                    phase_groups[phase_str], theory_id, phase_label,
                )
                all_stats.append(stats)
                compiled_phases.append(CompiledPhase(
                    phase_name=phase_name,
                    phase_label=phase_label,
                    indicators=indicators,
                ))
        else:
            indicators, stats = self.compile_indicators(
                activation_entries, theory_id, "Active",
            )
            all_stats.append(stats)
            compiled_phases.append(CompiledPhase(
                phase_name="single",
                phase_label="Active",
                indicators=indicators,
            ))

        # Compute summary stats
        total = sum(len(p.indicators) for p in compiled_phases)
        clean = sum(
            1 for p in compiled_phases for i in p.indicators
            if i.ambiguity == AmbiguityLevel.NONE and not i.compiler_warnings
        )
        warning = sum(
            1 for p in compiled_phases for i in p.indicators
            if i.ambiguity != AmbiguityLevel.NONE or i.compiler_warnings
        )
        blocked = sum(
            1 for p in compiled_phases for i in p.indicators
            if any("UNRESOLVED" in ref for ref in i.field_refs)
        )

        return CompiledTheoryActivation(
            theory_id=theory_id,
            is_two_phase=is_two_phase,
            phases=compiled_phases,
            compilation_model=self.model,
            compilation_timestamp=datetime.now(timezone.utc).isoformat(),
            total_indicators=total,
            clean_count=clean,
            warning_count=warning,
            blocked_count=blocked,
        )

    def get_cost_estimate(self) -> dict:
        """Return cost/latency summary for all calls made."""
        # Haiku pricing: $0.80/M input, $4.00/M output (as of 2025)
        input_cost = (self.total_input_tokens / 1_000_000) * 0.80
        output_cost = (self.total_output_tokens / 1_000_000) * 4.00
        total_cost = input_cost + output_cost
        avg_latency = (
            sum(self.call_latencies) / len(self.call_latencies)
            if self.call_latencies else 0
        )
        return {
            "total_calls": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "estimated_cost_usd": round(total_cost, 4),
            "avg_latency_s": round(avg_latency, 2),
            "total_latency_s": round(sum(self.call_latencies), 2),
        }
