# conviction.py — Pass 4: Three-stage mechanical conviction scoring pipeline.
# Depends on: schemas/scoring.py
# Depended on by: api/pipeline.py, api/hypotheses.py
#
# Pure math. No LLM. No narrative.
# Stage 1: Raw conviction from epistemic quality (weighted sum)
# Stage 2: Multiplicative discounts (soft falsifier health + overlap penalty + regime alignment)
# Stage 3: Hard caps (horizon alignment + expression efficiency gates)
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Any, Optional

from backend.engine.regime import compute_regime_discount
from backend.schemas.scoring import (
    ConvictionInput,
    ConvictionMath,
    MechanicalConvictionInputs,
    Stage1Raw,
    Stage2Discounts,
    Stage3Gates,
)

# Stage 1 weights from CLAUDE.md
WEIGHT_SUPPORT = 0.30
WEIGHT_QUALITY = 0.30
WEIGHT_CONVERGENCE = 0.25
WEIGHT_FALSIFIER_CLARITY = 0.15

# Stage 2 severity discount weights from interface contract
SEVERITY_WEIGHTS = {
    "minor": 0.10,
    "medium": 0.25,
    "major": 0.45,
}

# UNTESTABLE discount weights — reduced penalty for epistemic uncertainty
UNTESTABLE_WEIGHTS = {
    "minor": 0.05,
    "medium": 0.10,
    "major": 0.15,
}

# Stage 3 gate caps from CLAUDE.md
HORIZON_CAPS = [
    (0.10, 1),   # H < 0.10 → capped at 1/10
    (0.25, 2),   # H < 0.25 → capped at 2/10
    (0.40, 4),   # H < 0.40 → capped at 4/10
]

EXPRESSION_CAPS = [
    (0.15, 1),   # E < 0.15 → capped at 1/10
    (0.30, 3),   # E < 0.30 → capped at 3/10
]

# ETF liquidity tiers for expression efficiency
TIER_1 = {"SPY", "QQQ", "GLD", "TLT", "SHY", "IEF", "HYG", "LQD",
           "EEM", "VWO", "DBC", "XLE", "XLF", "IWM", "TIP", "UUP"}
TIER_2 = {"RSP", "XLU", "XLP", "XLY", "XLK", "EWZ", "EWY", "FXI",
           "STIP", "XOP", "MDY", "JETS", "ITB", "VEA"}

# Full ETF universe (imported from data_agent at module level would create circular dep)
from backend.engine.data_agent import ETF_UNIVERSE as _ETF_LIST
_ETF_SET = set(_ETF_LIST)

# Horizon alignment ideal window (days)
IDEAL_MIN_DAYS = 30
IDEAL_MAX_DAYS = 90

# Month name lookup
_MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# Quarter end months
_QUARTER_END = {"q1": 3, "q2": 6, "q3": 9, "q4": 12}


def _parse_timeframe_to_days(timeframe: str, today: date | None = None) -> int | None:
    """Parse a hypothesis timeframe string to approximate calendar days from today.

    Handles patterns like:
      "Through Q3 2026", "Next 6-8 weeks", "1-3 months", "By June 2026",
      "Within 30 days", "3-6 months", "Q2 2026", "Through mid-2026"
    """
    if not timeframe:
        return None
    today = today or date.today()
    s = timeframe.strip().lower()

    # "within N days" / "next N days"
    m = re.search(r'(\d+)\s*days?', s)
    if m:
        return int(m.group(1))

    # "N-M weeks" / "next N weeks" / "N weeks"
    m = re.search(r'(\d+)\s*[-–to]+\s*(\d+)\s*weeks?', s)
    if m:
        avg_weeks = (int(m.group(1)) + int(m.group(2))) / 2
        return int(avg_weeks * 7)
    m = re.search(r'(\d+)\s*weeks?', s)
    if m:
        return int(m.group(1)) * 7

    # "N-M months" / "N months"
    m = re.search(r'(\d+)\s*[-–to]+\s*(\d+)\s*months?', s)
    if m:
        avg_months = (int(m.group(1)) + int(m.group(2))) / 2
        return int(avg_months * 30)
    m = re.search(r'(\d+)\s*months?', s)
    if m:
        return int(m.group(1)) * 30

    # "through Q3 2026" / "Q2 2026" / "by Q1 2027"
    m = re.search(r'(q[1-4])\s*(\d{4})', s)
    if m:
        qtr = m.group(1)
        year = int(m.group(2))
        end_month = _QUARTER_END[qtr]
        # End of quarter month
        if end_month == 12:
            end_date = date(year, 12, 31)
        else:
            end_date = date(year, end_month + 1, 1) - timedelta(days=1)
        return max(1, (end_date - today).days)

    # "by June 2026" / "through March 2027" / "June 2026"
    for month_name, month_num in _MONTH_MAP.items():
        if month_name in s:
            m_year = re.search(r'(\d{4})', s)
            if m_year:
                year = int(m_year.group(1))
                # Use mid-month as approximation
                try:
                    end_date = date(year, month_num, 15)
                except ValueError:
                    end_date = date(year, month_num, 1)
                return max(1, (end_date - today).days)

    # "mid-2026" / "through mid 2026"
    m = re.search(r'mid[-\s]*(\d{4})', s)
    if m:
        year = int(m.group(1))
        end_date = date(year, 7, 1)
        return max(1, (end_date - today).days)

    # "end of 2026" / "late 2026"
    m = re.search(r'(?:end|late)[-\s]*(?:of\s+)?(\d{4})', s)
    if m:
        year = int(m.group(1))
        end_date = date(year, 12, 31)
        return max(1, (end_date - today).days)

    # "early 2026"
    m = re.search(r'early[-\s]*(\d{4})', s)
    if m:
        year = int(m.group(1))
        end_date = date(year, 3, 1)
        return max(1, (end_date - today).days)

    return None


def compute_horizon_alignment(timeframe: str, today: date | None = None) -> float:
    """Mechanical horizon alignment: overlap with 30-90 day ideal window.

    Returns 0.0-1.0. If timeframe can't be parsed, returns 0.50 (neutral).
    """
    days = _parse_timeframe_to_days(timeframe, today)
    if days is None:
        return 0.50  # unparseable — neutral default

    if IDEAL_MIN_DAYS <= days <= IDEAL_MAX_DAYS:
        return 1.0
    elif days < IDEAL_MIN_DAYS:
        return days / IDEAL_MIN_DAYS
    else:
        return (IDEAL_MAX_DAYS / days) ** 0.5


def compute_expression_efficiency(predicted_assets: list[str]) -> float:
    """Mechanical expression efficiency from ETF universe coverage + liquidity tiers.

    predicted_assets: list of ticker strings (e.g., ["GLD", "SPY"])
    Returns 0.0-1.0.
    """
    if not predicted_assets:
        return 0.0

    tickers = [t.upper().strip() for t in predicted_assets if t]
    n = len(tickers)
    if n == 0:
        return 0.0

    # Coverage: fraction of tickers in our ETF universe
    in_universe = sum(1 for t in tickers if t in _ETF_SET)
    coverage = in_universe / n

    # Liquidity weighting by tier
    tier_scores = []
    for t in tickers:
        if t in TIER_1:
            tier_scores.append(1.0)
        elif t in TIER_2:
            tier_scores.append(0.75)
        elif t in _ETF_SET:
            tier_scores.append(0.50)
        else:
            tier_scores.append(0.0)
    liquidity = sum(tier_scores) / n

    # Directness: 1/sqrt(n) — fewer assets = cleaner expression
    directness = 1.0 / (n ** 0.5)

    return coverage * 0.30 + liquidity * 0.40 + directness * 0.30


def score_conviction(inp: ConvictionInput) -> ConvictionMath:
    """Run the full three-stage conviction scoring pipeline.

    Returns a ConvictionMath object with full transparency into each stage.
    """
    s1 = _stage1_raw(inp)
    s2 = _stage2_discounts(inp, s1.raw)
    s3 = _stage3_gates(inp, s2.adjusted)

    return ConvictionMath(stage1=s1, stage2=s2, stage3=s3)


def score_batch(inputs: list[ConvictionInput]) -> list[ConvictionMath]:
    """Score a batch of hypotheses. Overlap counts should be pre-computed."""
    return [score_conviction(inp) for inp in inputs]


# ---------------------------------------------------------------------------
# Stage 1: Raw conviction
# ---------------------------------------------------------------------------

def _stage1_raw(inp: ConvictionInput) -> Stage1Raw:
    """Compute raw conviction from epistemic quality dimensions.

    RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)
    Range: 0.0 to 1.0, then scaled to 0-10.
    """
    raw_01 = (
        inp.support_strength * WEIGHT_SUPPORT
        + inp.evidence_quality * WEIGHT_QUALITY
        + inp.convergence * WEIGHT_CONVERGENCE
        + inp.falsifier_clarity * WEIGHT_FALSIFIER_CLARITY
    )
    # Clamp to [0, 1]
    raw_01 = max(0.0, min(1.0, raw_01))
    raw_10 = raw_01 * 10.0

    return Stage1Raw(
        support_strength=inp.support_strength,
        evidence_quality=inp.evidence_quality,
        convergence=inp.convergence,
        falsifier_clarity=inp.falsifier_clarity,
        raw=raw_10,
    )


# ---------------------------------------------------------------------------
# Stage 2: Discounts
# ---------------------------------------------------------------------------

def _stage2_discounts(inp: ConvictionInput, raw_score: float) -> Stage2Discounts:
    """Apply multiplicative soft falsifier discount and additive overlap adjustment.

    D_f: multiplicative compounding — each triggered falsifier independently
    reduces the surviving fraction: d_f = product((1 - weight_i)).
    Overlap: same-theory penalizes (-0.50 each), cross-theory gives small
    convergence bonus (+0.10 each, capped at +0.20).
    """
    # Soft falsifier health discount — multiplicative compounding
    d_f = 1.0
    for f in inp.triggered_soft_falsifiers:
        weight = SEVERITY_WEIGHTS.get(f.get("severity", "minor"), 0.10)
        d_f *= (1.0 - weight)
    d_f = max(0.05, d_f)

    # UNTESTABLE discount — reduced penalty for epistemic uncertainty
    d_u = 1.0
    for f in inp.untestable_soft_falsifiers:
        weight = UNTESTABLE_WEIGHTS.get(f.get("severity", "minor"), 0.05)
        d_u *= (1.0 - weight)
    d_u = max(0.05, d_u)

    # Regime alignment discount (D_r)
    d_r = compute_regime_discount(inp.resolution_channel, inp.active_regime_flags)

    # Theory-aware overlap adjustment (additive)
    overlap_adj = (inp.same_theory_overlap * -0.50) + min(inp.diff_theory_overlap * 0.10, 0.20)

    adjusted = max(0.0, (raw_score * d_f * d_u * d_r) + overlap_adj)

    return Stage2Discounts(
        soft_falsifier_discount=d_f,
        triggered_soft_falsifiers=inp.triggered_soft_falsifiers,
        untestable_discount=d_u,
        untestable_soft_falsifiers=inp.untestable_soft_falsifiers,
        regime_discount=d_r,
        overlap_same_theory=inp.same_theory_overlap,
        overlap_diff_theory=inp.diff_theory_overlap,
        overlap_adjustment=overlap_adj,
        adjusted=adjusted,
    )


# ---------------------------------------------------------------------------
# Stage 3: Gates
# ---------------------------------------------------------------------------

def _stage3_gates(inp: ConvictionInput, adjusted_score: float) -> Stage3Gates:
    """Apply hard caps from horizon alignment and expression efficiency.

    FINAL = min(SCORE, horizon_cap, expression_cap)
    Round to nearest integer. Output: 0-10.
    """
    # Horizon cap
    horizon_cap = None
    for threshold, cap in HORIZON_CAPS:
        if inp.horizon_alignment < threshold:
            horizon_cap = cap
            break

    # Expression cap
    expression_cap = None
    for threshold, cap in EXPRESSION_CAPS:
        if inp.expression_efficiency < threshold:
            expression_cap = cap
            break

    # Apply caps
    final = adjusted_score
    if horizon_cap is not None:
        final = min(final, horizon_cap)
    if expression_cap is not None:
        final = min(final, expression_cap)

    # Round to nearest integer
    final = round(final)
    # Clamp to 0-10
    final = max(0, min(10, final))

    # Conviction floor: scores below 5 are mechanically killed
    floor_killed = final < 5.0 and final > 0.0
    kill_reason = f"Below conviction floor (scored {final}/10)" if floor_killed else ""

    return Stage3Gates(
        horizon_score=inp.horizon_alignment,
        horizon_cap=horizon_cap,
        expression_score=inp.expression_efficiency,
        expression_cap=expression_cap,
        final=float(final),
        floor_killed=floor_killed,
        kill_reason=kill_reason,
    )


# ---------------------------------------------------------------------------
# Mechanical conviction input computation
# ---------------------------------------------------------------------------

def compute_mechanical_conviction_inputs(
    hypothesis: dict[str, Any],
    activation_results: list[dict[str, Any]],
    briefing: dict[str, Any],
    elimination_result: Optional[dict[str, Any]] = None,
) -> MechanicalConvictionInputs:
    """Compute Stage 1 conviction inputs from pipeline data only. No LLM.

    Dimensions:
      support_strength  = theory activation score
      evidence_quality  = data coverage ratio (indicators with data / total)
      convergence       = fraction of directional predictions aligned with 30d price
      falsifier_clarity = fraction of falsifiers that are CLEAR or TRIGGERED (not UNTESTABLE)
    """
    source_theory = hypothesis.get("source_theory", "")
    source_theories_raw = hypothesis.get("source_theories", "[]")
    if isinstance(source_theories_raw, str):
        try:
            source_theories = json.loads(source_theories_raw)
        except (json.JSONDecodeError, TypeError):
            source_theories = [source_theory] if source_theory else []
    else:
        source_theories = source_theories_raw or []
    if not source_theories and source_theory:
        source_theories = [source_theory]

    # Build activation lookup
    act_map: dict[str, dict] = {}
    for ar in activation_results:
        act_map[ar.get("theory_id", "")] = ar

    # --- DIMENSION 1: support_strength = activation score ---
    support = _compute_support_strength(source_theories, act_map)

    # --- DIMENSION 2: evidence_quality = data coverage ratio ---
    evidence = _compute_evidence_quality(source_theories, act_map)

    # --- DIMENSION 3: convergence = directional price alignment ---
    convergence = _compute_convergence(hypothesis, briefing)

    # --- DIMENSION 4: falsifier_clarity = verification ratio ---
    clarity = _compute_falsifier_clarity(hypothesis, elimination_result)

    return MechanicalConvictionInputs(
        support_strength=support,
        evidence_quality=evidence,
        convergence=convergence,
        falsifier_clarity=clarity,
    )


def _compute_support_strength(
    source_theories: list[str],
    act_map: dict[str, dict],
) -> float:
    """support_strength = activation score of source theory (avg for composites)."""
    scores = []
    for tid in source_theories:
        ar = act_map.get(tid)
        if not ar:
            continue
        if ar.get("is_two_phase"):
            # Use effective phase score
            phase = ar.get("effective_phase")
            phase_scores = ar.get("phase_scores", {})
            if phase and phase in phase_scores:
                scores.append(phase_scores[phase])
            else:
                # Fallback: max of phase scores
                vals = [v for v in phase_scores.values() if v is not None]
                if vals:
                    scores.append(max(vals))
        else:
            s = ar.get("score")
            if s is not None:
                scores.append(s)

    if not scores:
        return 0.30  # hard floor for inactive/missing theories

    return sum(scores) / len(scores)


def _compute_evidence_quality(
    source_theories: list[str],
    act_map: dict[str, dict],
) -> float:
    """evidence_quality = indicators with data / mechanical indicators only.

    Skipped indicators (qualitative, web-search-required) are excluded from
    the denominator — they are structurally unfillable by the mechanical
    pipeline and would uniformly deflate every theory's score.
    """
    mechanical_indicators = 0
    indicators_with_data = 0

    for tid in source_theories:
        ar = act_map.get(tid)
        if not ar:
            continue

        ir = ar.get("indicator_results", {})

        # Only count mechanical indicators (those in indicator_results)
        for result in ir.values():
            mechanical_indicators += 1
            if result.get("value") is not None:
                indicators_with_data += 1

    if mechanical_indicators == 0:
        return 0.20  # hard floor

    ratio = indicators_with_data / mechanical_indicators
    return max(0.20, ratio)


def _compute_convergence(
    hypothesis: dict[str, Any],
    briefing: dict[str, Any],
) -> float:
    """convergence = fraction of directional predictions aligned with 30d price."""
    directions_raw = hypothesis.get("asset_direction", "{}")
    if isinstance(directions_raw, str):
        try:
            directions = json.loads(directions_raw)
        except (json.JSONDecodeError, TypeError):
            directions = {}
    else:
        directions = directions_raw or {}

    if not directions:
        return 0.0

    markets = briefing.get("markets", {})
    checked = 0
    aligned = 0

    for ticker, direction in directions.items():
        md = markets.get(ticker)
        if not md:
            continue

        return_1m = md.get("return_1m")
        if return_1m is None:
            continue

        checked += 1
        dir_upper = str(direction).upper()
        if dir_upper == "LONG" and return_1m > 0:
            aligned += 1
        elif dir_upper == "SHORT" and return_1m < 0:
            aligned += 1

    if checked == 0:
        return 0.0

    return aligned / checked


def _compute_falsifier_clarity(
    hypothesis: dict[str, Any],
    elimination_result: Optional[dict[str, Any]] = None,
) -> float:
    """falsifier_clarity = (CLEAR + TRIGGERED) / total falsifiers."""
    total = 0
    verified = 0  # CLEAR or TRIGGERED

    # Hard falsifiers
    hf_raw = hypothesis.get("hard_falsifiers", "[]")
    if isinstance(hf_raw, str):
        try:
            hard_f = json.loads(hf_raw)
        except (json.JSONDecodeError, TypeError):
            hard_f = []
    else:
        hard_f = hf_raw or []

    # Soft falsifiers
    sf_raw = hypothesis.get("soft_falsifiers", "[]")
    if isinstance(sf_raw, str):
        try:
            soft_f = json.loads(sf_raw)
        except (json.JSONDecodeError, TypeError):
            soft_f = []
    else:
        soft_f = sf_raw or []

    # Count hard falsifiers — from elimination check
    if elimination_result:
        hf_check = elimination_result.get("hard_falsifier_check", {})
        # Hard falsifiers are always checked with data → count as verified
        # unless the elimination didn't produce a check
        hf_details = hf_check.get("details", "")
        if hf_details:
            # Count hard falsifiers from hypothesis definition
            total += len(hard_f)
            # If elimination provided a hard falsifier check, count all as verified
            # (hard falsifiers are always checked mechanically)
            verified += len(hard_f)
        else:
            total += len(hard_f)
    else:
        total += len(hard_f)
        # Without elimination data, assume hard falsifiers are verified
        verified += len(hard_f)

    # Count soft falsifiers by status
    for sf in soft_f:
        total += 1
        status = sf.get("status", "clear").upper()
        if status in ("CLEAR", "TRIGGERED"):
            verified += 1
        # UNTESTABLE does not count as verified

    if total == 0:
        return 0.50  # neutral default

    return verified / total
