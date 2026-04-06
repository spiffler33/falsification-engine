# activation.py — Pass 1: Mechanical activation scoring.
# Depends on: schemas/theory.py, schemas/briefing.py
# Depended on by: api/theories.py, api/pipeline.py, engine/prompt_builder.py
#
# Takes parsed theory modules + a data briefing packet.
# For each theory, checks each indicator against the briefing.
# Computes weighted activation score. Returns Active/Adjacent/Inactive.
# Two-phase logic: check Phase B first; if Active, Phase A is Inactive.
from __future__ import annotations

import re

from backend.schemas.briefing import BriefingPacket
from backend.schemas.theory import (
    ActivationPhase,
    ActivationResult,
    ActivationTier,
    Direction,
    Indicator,
    TheoryModule,
    TheoryPackage,
)

# Tier thresholds from CLAUDE.md
ACTIVE_THRESHOLD = 0.60
ADJACENT_THRESHOLD = 0.30

# Maps distinctive substrings from web-search metric_source descriptions
# to briefing packet field names. Checked in order; first match wins.
# Fields resolve via BriefingPacket.get_field() which searches computed,
# web_sourced, and macro sections transparently.
WEB_FIELD_MAP: list[tuple[str, str]] = [
    # -- valuation_mean_reversion --
    ("shiller cape ratio", "shiller_cape"),
    ("total us market cap / gdp", "buffett_indicator"),
    ("s&p 500 net profit margin", "sp500_net_margin"),
    ("corporate profits / gdp", "corporate_profits_gdp_ratio"),
    ("insider transactions", "insider_sell_buy_ratio"),
    ("insider buy/sell ratio", "insider_sell_buy_ratio"),

    # -- debt_cycle_short --
    ("senior loan officer survey", "sloos_net_tightening"),
    ("conference board consumer confidence", "consumer_confidence"),
    ("ceo confidence survey", "consumer_confidence"),

    # -- debt_cycle_long --
    ("federal reserve z.1", "total_debt_to_gdp"),
    ("bis global credit", "total_debt_to_gdp"),
    ("fiscal multiplier", "deficit_pct_gdp"),
    ("deficit vs. gdp", "deficit_pct_gdp"),
    ("distributional financial accounts", "top10_wealth_share"),
    ("world inequality", "top10_wealth_share"),

    # -- structural_fragility --
    ("finra margin", "finra_margin_debt"),
    ("ici or morningstar", "passive_fund_share"),
    ("shiller cape", "shiller_cape"),

    # -- fiscal_dominance_liquidity --
    ("treasury monthly budget statement", "deficit_pace_annualized"),

    # -- fiscal_dominance_arithmetic --
    ("treasury monthly statement", "interest_receipts_ratio"),
    ("cbo projections", "interest_receipts_ratio"),
    ("cbo budget data", "interest_exceeds_defense"),
    ("treasury monthly budget statements + nber", "deficit_pace_annualized"),
    ("treasury refunding data", "weighted_avg_interest_rate"),
    ("weighted average interest rate", "weighted_avg_interest_rate"),
    ("world gold council", "cb_gold_purchases"),
    ("imf cofer", "cb_gold_purchases"),
    ("imf ifs data", "cb_gold_purchases"),

    # -- capital_flows --
    ("msci em pe", "em_dm_pe_gap"),
    ("eem pe vs. spy pe", "em_dm_pe_gap"),
    ("china credit impulse", "china_credit_impulse"),
    ("total social financing", "china_credit_impulse"),
    ("usd/cny", "usdcny"),
    ("cnh offshore", "usdcny"),

    # -- monetary_architecture --
    ("treasury international capital", "foreign_treasury_holdings_pct"),
    ("tic data", "foreign_treasury_holdings_pct"),
    ("fed custody holdings", "foreign_treasury_holdings_pct"),
    ("swift rmb share", "rmb_swift_share"),
    ("bilateral currency agreement", "rmb_swift_share"),
    ("energy trade settlement", "rmb_swift_share"),
]


def score_all_theories(
    theories: list[TheoryModule],
    briefing: BriefingPacket,
) -> list[ActivationResult]:
    """Score activation for all theory modules against a briefing packet."""
    return [score_theory(t, briefing) for t in theories]


def score_theory(theory: TheoryModule, briefing: BriefingPacket) -> ActivationResult:
    """Score activation for a single theory module."""
    if theory.is_two_phase:
        return _score_two_phase(theory, briefing)
    else:
        return _score_single_phase(theory, briefing)


def _score_single_phase(theory: TheoryModule, briefing: BriefingPacket) -> ActivationResult:
    """Score a single-phase theory."""
    if not theory.phases:
        return ActivationResult(theory_id=theory.theory_id, score=0.0, tier=ActivationTier.INACTIVE)

    phase = theory.phases[0]
    score, indicator_results, skipped = _score_phase(phase, briefing)
    tier = _score_to_tier(score)

    return ActivationResult(
        theory_id=theory.theory_id,
        is_two_phase=False,
        score=score,
        tier=tier,
        indicator_results=indicator_results,
        skipped_indicators=skipped,
    )


def _score_two_phase(theory: TheoryModule, briefing: BriefingPacket) -> ActivationResult:
    """Score a two-phase theory. Phase B checked first per spec."""
    phase_a = None
    phase_b = None
    for p in theory.phases:
        if p.phase_name == "phase_a":
            phase_a = p
        elif p.phase_name == "phase_b":
            phase_b = p

    phase_scores: dict[str, float] = {}
    phase_tiers: dict[str, ActivationTier] = {}
    all_indicator_results: dict[str, dict] = {}
    all_skipped: list[str] = []

    # Score Phase B first
    if phase_b:
        score_b, results_b, skipped_b = _score_phase(phase_b, briefing)
        phase_scores[phase_b.phase_label] = score_b
        phase_tiers[phase_b.phase_label] = _score_to_tier(score_b)
        all_indicator_results.update(results_b)
        all_skipped.extend(skipped_b)

    # Score Phase A
    if phase_a:
        score_a, results_a, skipped_a = _score_phase(phase_a, briefing)
        phase_scores[phase_a.phase_label] = score_a
        phase_tiers[phase_a.phase_label] = _score_to_tier(score_a)
        all_indicator_results.update(results_a)
        all_skipped.extend(skipped_a)

    # Determine effective tier: Phase B takes priority
    effective_tier = ActivationTier.INACTIVE
    effective_phase = None

    if phase_b and phase_tiers.get(phase_b.phase_label) == ActivationTier.ACTIVE:
        effective_tier = ActivationTier.ACTIVE
        effective_phase = phase_b.phase_label
        # Phase A is Inactive by definition when Phase B is Active
        if phase_a:
            phase_tiers[phase_a.phase_label] = ActivationTier.INACTIVE
    elif phase_b and phase_tiers.get(phase_b.phase_label) == ActivationTier.ADJACENT:
        effective_tier = ActivationTier.ADJACENT
        effective_phase = phase_b.phase_label
    elif phase_a:
        phase_a_tier = phase_tiers.get(phase_a.phase_label, ActivationTier.INACTIVE)
        effective_tier = phase_a_tier
        if phase_a_tier != ActivationTier.INACTIVE:
            effective_phase = phase_a.phase_label

    return ActivationResult(
        theory_id=theory.theory_id,
        is_two_phase=True,
        phase_scores=phase_scores,
        phase_tiers=phase_tiers,
        effective_tier=effective_tier,
        effective_phase=effective_phase,
        indicator_results=all_indicator_results,
        skipped_indicators=all_skipped,
    )


def _score_phase(
    phase: ActivationPhase,
    briefing: BriefingPacket,
) -> tuple[float, dict[str, dict], list[str]]:
    """Score a single activation phase against the briefing.

    Returns (score, indicator_results, skipped_indicators).
    Score is weighted sum of triggered mechanical indicators,
    normalized by total mechanical weight.
    """
    total_mechanical_weight = 0.0
    triggered_weight = 0.0
    indicator_results: dict[str, dict] = {}
    skipped: list[str] = []

    for ind in phase.indicators:
        # Skip qualitative indicators
        if ind.is_qualitative or ind.weight < 0:
            skipped.append(f"{ind.name} (qualitative)")
            continue

        # Resolve metric from briefing
        metric_field = _extract_metric_field(ind.metric_source)
        value = briefing.get_field(metric_field) if metric_field else None

        # Web-search indicators: include only when data is available.
        # When unavailable, skip entirely (don't count in total weight)
        # so scores match pre-enrichment behavior.
        if ind.requires_web_search and value is None:
            reason = "no field mapping" if metric_field is None else "web data not available"
            skipped.append(f"{ind.name} ({reason})")
            continue

        # --- Data-gap policy (post-v8 Task 2) ---
        # Indicators that cannot be mechanically scored under the current
        # architecture must not stay in the denominator as silent penalties.
        #
        # Two cases:
        #   A. Data unavailable: non-web indicator whose field resolves to
        #      None.  Unlike web-search skips (which are optional enrichment),
        #      these are computed-mechanical indicators with no data source.
        #   B. Threshold not evaluable: value exists, but the threshold is
        #      pure prose with no extractable number.  _check_threshold()
        #      would always return False, making the indicator dead weight.
        #
        # Both are excluded from the denominator and recorded in results
        # with an explicit reason so the distinction is visible downstream.

        if value is None:
            skipped.append(f"{ind.name} (data unavailable)")
            indicator_results[ind.name] = {
                "triggered": False,
                "value": None,
                "threshold": ind.threshold,
                "metric_field": metric_field,
                "weight": ind.weight,
                "reason": "data_unavailable",
            }
            continue

        threshold_num = _extract_number(ind.threshold) if ind.threshold else None
        if threshold_num is None:
            skipped.append(
                f"{ind.name} (threshold not mechanically evaluable)"
            )
            indicator_results[ind.name] = {
                "triggered": False,
                "value": value,
                "threshold": ind.threshold,
                "metric_field": metric_field,
                "weight": ind.weight,
                "reason": "threshold_not_evaluable",
            }
            continue

        total_mechanical_weight += ind.weight

        # Check threshold
        triggered = _check_threshold(value, ind)

        if triggered:
            triggered_weight += ind.weight

        indicator_results[ind.name] = {
            "triggered": triggered,
            "value": value,
            "threshold": ind.threshold,
            "direction": ind.direction.value,
            "weight": ind.weight,
            "metric_field": metric_field,
        }

    # Normalize score by total mechanical weight
    if total_mechanical_weight > 0:
        score = triggered_weight / total_mechanical_weight
    else:
        score = 0.0

    return score, indicator_results, skipped


def _extract_metric_field(metric_source: str) -> str | None:
    """Extract the briefing packet field name from a metric_source string.

    Examples:
        '`^VIX`' → '^VIX'
        '`credit.hy_spread`' → 'credit.hy_spread'
        'computed: `qqq_iwm_ratio`' → 'qqq_iwm_ratio'
        'computed: `VIX - 20d_realized_vol`' → 'vix_realized_gap'
        'web search: FINRA margin statistics' → 'finra_margin_debt'
        'web search: Shiller CAPE ratio' → 'shiller_cape'
        'web search required' → None (no distinctive description)
    """
    source = metric_source.strip()

    # Web-search sources: resolve via WEB_FIELD_MAP
    if "web search" in source.lower():
        return _resolve_web_field(source)

    # Extract backtick-wrapped field names
    backtick_match = re.findall(r"`([^`]+)`", source)
    if backtick_match:
        field = backtick_match[-1]  # take the last backtick match

        # Handle computed expressions like "VIX - 20d_realized_vol"
        if " - " in field or " + " in field or " / " in field:
            # These are computed metrics — map to a normalized field name
            return _normalize_computed_field(field)

        return field

    # No backtick field name and not a web-search source.
    # Do NOT fall through to returning the whole string — that produces
    # garbage field names that silently resolve to None downstream.
    # Callers must handle None explicitly.
    return None


def _resolve_web_field(metric_source: str) -> str | None:
    """Resolve a web-search metric_source to a briefing field name.

    Checks the WEB_FIELD_MAP for the first matching substring.
    Returns the mapped field name, or None if no match.
    """
    source_lower = metric_source.lower()
    for keyword, field_name in WEB_FIELD_MAP:
        if keyword in source_lower:
            return field_name
    return None


def _normalize_computed_field(expr: str) -> str | None:
    """Normalize a computed expression to a briefing field name.

    Returns None for unrecognized expressions instead of producing
    a generic garbage field name (BUG-04 fix).
    """
    expr_lower = expr.lower().strip()

    # Known computed field mappings
    if "vix" in expr_lower and "realized" in expr_lower:
        return "vix_vs_realized"
    if "qqq" in expr_lower and "iwm" in expr_lower:
        return "qqq_iwm_ratio"
    if "spy" in expr_lower and "52w" in expr_lower:
        return "spy_drawdown_from_52w_high"

    # No known mapping found.  Return None instead of a generic
    # underscore-munged string that silently produces invalid field names.
    return None


def _check_threshold(value: float, indicator: Indicator) -> bool:
    """Check if a value triggers an indicator's threshold condition."""
    threshold_str = indicator.threshold.strip()

    # Extract numeric threshold from the description
    threshold_num = _extract_number(threshold_str)

    if threshold_num is None:
        # Cannot mechanically check — descriptive threshold
        return False

    if indicator.direction == Direction.ABOVE:
        return value > threshold_num
    elif indicator.direction == Direction.BELOW:
        return value < threshold_num
    elif indicator.direction == Direction.RISING:
        # BUG-03 KNOWN LIMITATION: RISING/FALLING are treated as simple
        # threshold comparisons (value > threshold / value < threshold)
        # because the engine has no temporal trend data.  This is an
        # explicitly provisional proxy — the check answers "is the current
        # level above/below the threshold?" not "is the value trending
        # up/down?"  Indicators that truly need trend detection should use
        # computed fields with temporal logic in data_agent.py.
        return value > threshold_num
    elif indicator.direction == Direction.FALLING:
        # See RISING note above — same provisional proxy applies.
        return value < threshold_num
    elif indicator.direction == Direction.BETWEEN:
        # Try to extract a range
        numbers = re.findall(r"[-+]?\d*\.?\d+", threshold_str)
        if len(numbers) >= 2:
            low, high = float(numbers[0]), float(numbers[1])
            return low <= value <= high
        return False

    return False


def _extract_number(s: str) -> float | None:
    """Extract the first meaningful number from a threshold string.

    Handles: 'Below 14', 'Above 300bp', '-20%', '$1.5T', '0.5x', etc.

    Suffix scaling:
    - K/k (thousands): "250K" → 250000.  The only suffix that changes
      the extracted magnitude, because fields using K thresholds (e.g.
      initial_claims) store raw counts.
    - bp: stripped, no scaling.  The primary bp-compared field
      (credit.hy_spread) stores values in basis points.
    - %: stripped, no scaling.  Percentage fields store percentages.
    - $, T, B, M, x: stripped, no scaling.  Monetary field units vary
      (some $M, some $B) so context-free scaling would break aligned
      thresholds.  Task 1 already aligned critical $-denominated
      thresholds to their field units.  v9 structured thresholds will
      resolve this limitation.

    Does NOT interpret temporal phrases ("3+ months", "2-year high").
    Those remain deferred to v9.
    """
    # K/k suffix: multiply by 1000 (e.g., "250K" → 250000)
    k_match = re.search(r"([-+]?\d*\.?\d+)\s*[Kk]\b", s)
    if k_match:
        return float(k_match.group(1)) * 1000

    # Strip suffixes attached to numbers without scaling.
    # Uses targeted patterns instead of global character replacement
    # to avoid destroying letters in words like "Below", "Monthly".
    cleaned = re.sub(r"(\d)\s*bp\b", r"\1", s)         # 300bp → 300
    cleaned = re.sub(r"(\d)\s*%", r"\1", cleaned)       # 5.0% → 5.0
    cleaned = cleaned.replace("$", "")                   # $500 → 500
    cleaned = re.sub(r"(\d)\s*[TBM]\b", r"\1", cleaned) # 1.5T → 1.5
    cleaned = re.sub(r"(\d)\s*x\b", r"\1", cleaned)     # 1.5x → 1.5

    # Extract the first number from the cleaned string
    numbers = re.findall(r"[-+]?\d*\.?\d+", cleaned)
    if numbers:
        return float(numbers[0])

    return None


def _score_to_tier(score: float) -> ActivationTier:
    """Convert a numeric score to an activation tier."""
    if score >= ACTIVE_THRESHOLD:
        return ActivationTier.ACTIVE
    elif score >= ADJACENT_THRESHOLD:
        return ActivationTier.ADJACENT
    else:
        return ActivationTier.INACTIVE


# ---------------------------------------------------------------------------
# Package-native scoring: accept TheoryPackage directly, no adapter needed
# ---------------------------------------------------------------------------

_DIRECTION_KEYWORDS: dict[str, str] = {
    "above": "above",
    "below": "below",
    "rising": "rising",
    "falling": "falling",
    "between": "between",
}


def _parse_direction(raw: str) -> str:
    """Map a direction string to a Direction enum value.

    Handles compound directions (e.g. "above and rising") by matching the
    first canonical keyword.  Raises ValueError on unrecognized directions
    so that non-canonical strings are surfaced loudly rather than silently
    defaulting to "above" (BUG-02 fix).
    """
    low = raw.lower().strip()
    for keyword, value in _DIRECTION_KEYWORDS.items():
        if keyword in low:
            return value
    raise ValueError(
        f"Unrecognized direction '{raw}' — must contain one of: "
        f"{', '.join(_DIRECTION_KEYWORDS.keys())}"
    )


def _entry_to_indicator(entry: dict) -> Indicator:
    """Convert a parsed activation table dict to an Indicator object.

    Re-injects the ``web search:`` prefix for web-search indicators so the
    activation engine's ``_extract_metric_field`` resolves fields via
    WEB_FIELD_MAP correctly.
    """
    direction = Direction(_parse_direction(entry["direction"]))
    requires_web_search = entry.get("data_ownership") == "web-search"

    metric_source = entry["metric_source"]
    if requires_web_search and "web search" not in metric_source.lower():
        metric_source = f"web search: {metric_source}"

    return Indicator(
        name=entry["indicator_name"],
        metric_source=metric_source,
        threshold=entry["threshold"],
        direction=direction,
        weight=entry["weight"],
        rationale="",
        requires_web_search=requires_web_search,
        is_qualitative=False,
    )


def _build_phases_from_package(pkg: TheoryPackage) -> tuple[bool, list[ActivationPhase]]:
    """Parse ACTIVATION.md text into ActivationPhase objects.

    Returns (is_two_phase, phases).

    Two-phase validation (FRAGILITY-03, FRAGILITY-11):
    - Exactly 2 phase groups required
    - Each must map to ``phase_a`` or ``phase_b`` (no silent fallthrough)
    - No duplicate phase names
    """
    from backend.engine.theory_loader import parse_activation_table

    entries = parse_activation_table(pkg.activation)

    phases_present = {e["phase"] for e in entries if e["phase"]}
    is_two_phase = len(phases_present) >= 2

    if is_two_phase:
        phase_groups: dict[str, list[dict]] = {}
        for entry in entries:
            phase_groups.setdefault(entry["phase"], []).append(entry)

        # FRAGILITY-11: exactly 2 phase groups required.
        if len(phase_groups) != 2:
            raise ValueError(
                f"Two-phase theory has {len(phase_groups)} phase groups "
                f"(expected exactly 2): {sorted(phase_groups.keys())}"
            )

        phases: list[ActivationPhase] = []
        seen_names: set[str] = set()

        for phase_str in sorted(phase_groups):
            # FRAGILITY-03: phase string must contain 'Phase A' or 'Phase B'.
            # No silent fallthrough to phase_name = phase_str.
            if re.search(r"Phase\s*A\b", phase_str, re.IGNORECASE):
                phase_name = "phase_a"
            elif re.search(r"Phase\s*B\b", phase_str, re.IGNORECASE):
                phase_name = "phase_b"
            else:
                raise ValueError(
                    f"Phase string {phase_str!r} does not contain "
                    f"'Phase A' or 'Phase B'. Two-phase theories must "
                    f"use 'Phase A: <label>' and 'Phase B: <label>' format."
                )

            # FRAGILITY-11: no duplicate phase names.
            if phase_name in seen_names:
                raise ValueError(
                    f"Duplicate phase name {phase_name!r} — two different "
                    f"phase strings both mapped to the same internal name: "
                    f"{sorted(phase_groups.keys())}"
                )
            seen_names.add(phase_name)

            label_match = re.search(r"Phase\s+[AB]:\s*(.+)", phase_str)
            phase_label = label_match.group(1).strip() if label_match else phase_str

            indicators = [_entry_to_indicator(e) for e in phase_groups[phase_str]]
            phases.append(ActivationPhase(
                phase_name=phase_name,
                phase_label=phase_label,
                indicators=indicators,
            ))
    else:
        indicators = [_entry_to_indicator(e) for e in entries]
        phases = [ActivationPhase(
            phase_name="single",
            phase_label="Active",
            indicators=indicators,
        )]

    return is_two_phase, phases


def score_package(
    pkg: TheoryPackage,
    briefing: BriefingPacket,
    *,
    skip_validation: bool = False,
) -> ActivationResult:
    """Score activation for a v8 TheoryPackage against a briefing packet.

    Parses ACTIVATION.md internally — no adapter or TheoryModule needed.

    Runs ``validate_theory_package()`` as a pre-flight gate before scoring
    unless *skip_validation* is True.  Raises ``TheoryValidationError`` if
    the package has error-severity validation failures.

    *skip_validation* exists for batch scoring via ``score_all_packages()``,
    which validates all packages in one pass before scoring any of them.
    Individual callers should not set it.
    """
    if not skip_validation:
        from backend.engine.theory_loader import (
            TheoryValidationError,
            validate_theory_package,
        )
        report = validate_theory_package(pkg)
        if not report.passed:
            raise TheoryValidationError(report)

    is_two_phase, phases = _build_phases_from_package(pkg)
    module = TheoryModule(
        theory_id=pkg.theory_id,
        is_two_phase=is_two_phase,
        phases=phases,
    )
    return score_theory(module, briefing)


def score_all_packages(
    packages: list[TheoryPackage],
    briefing: BriefingPacket,
) -> list[ActivationResult]:
    """Score activation for all v8 TheoryPackages against a briefing packet.

    Validates all packages in a single pass first.  If any package has
    error-severity findings, raises ``TheoryValidationError`` with the
    full report before scoring any package.
    """
    from backend.engine.theory_loader import (
        TheoryValidationError,
        validate_all_packages,
    )
    report = validate_all_packages(packages)
    if not report.passed:
        raise TheoryValidationError(report)
    return [score_package(pkg, briefing, skip_validation=True) for pkg in packages]
