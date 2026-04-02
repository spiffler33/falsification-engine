# validation_agent.py — Phase 4: Data validation for briefing packets.
# Depends on: schemas/briefing.py
# Depended on by: engine/data_agent.py, scripts/run_data.py
#
# Runs 6 check types against a BriefingPacket:
#   completeness, range, consistency, cross_source, staleness, anomaly
# Produces a ValidationReport stored in briefing.data_quality.
# Pure Python — no LLM calls.
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel

from backend.schemas.briefing import BriefingPacket

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

class ValidationCheck(BaseModel):
    """A single validation check result."""
    field: str
    check_type: str   # completeness, range, consistency, cross_source, staleness, anomaly
    severity: str     # error, warning, info
    message: str
    details: dict[str, Any] = {}


class ValidationReport(BaseModel):
    """Aggregate validation report for a briefing packet."""
    checks: list[ValidationCheck]
    errors: int
    warnings: int
    overall_quality: str  # "good", "degraded", "poor"


# ---------------------------------------------------------------------------
# Field registries
# ---------------------------------------------------------------------------

# Fields critical for activation scoring (weight >= 0.15 across theories).
# Missing critical fields -> error severity. Non-critical -> warning.
CRITICAL_FIELDS: set[str] = {
    # Growth
    "growth.real_gdp", "growth.unemployment", "growth.ism_proxy",
    # Inflation
    "inflation.cpi_yoy", "inflation.core_pce", "inflation.breakeven_5y",
    # Rates
    "rates.fed_funds", "rates.treasury_2y", "rates.treasury_10y",
    "rates.treasury_3m", "rates.curve_2s10s", "rates.curve_3m10y",
    # Liquidity
    "liquidity.fed_balance_sheet", "liquidity.tga", "liquidity.reverse_repo",
    # Credit
    "credit.hy_spread", "credit.ig_spread",
}

# Critical computed fields — missing these is an error.
CRITICAL_COMPUTED: set[str] = {"net_liquidity", "equity_risk_premium"}

# Range bounds: (min, max). Values outside are flagged.
# Bounds are generous — designed to catch bad data, not normal extremes.
RANGE_BOUNDS: dict[str, tuple[float, float]] = {
    # Growth
    "growth.gdp_latest": (10_000, 45_000),
    "growth.real_gdp": (-35, 35),
    "growth.unemployment": (0, 25),
    "growth.initial_claims": (100_000, 7_000_000),
    "growth.ism_proxy": (25, 80),
    "growth.nonfarm_payrolls": (-25_000, 5_000),
    # Inflation
    "inflation.cpi_yoy": (-5, 20),
    "inflation.core_pce": (-3, 15),
    "inflation.breakeven_5y": (-3, 10),
    "inflation.breakeven_10y": (-3, 8),
    # Rates
    "rates.fed_funds": (0, 22),
    "rates.treasury_2y": (0, 20),
    "rates.treasury_10y": (0, 18),
    "rates.treasury_30y": (0, 18),
    "rates.treasury_3m": (0, 20),
    # Liquidity (millions)
    "liquidity.fed_balance_sheet": (500_000, 15_000_000),
    "liquidity.tga": (0, 2_000_000),
    "liquidity.reverse_repo": (0, 3_000_000),
    "liquidity.m2": (5_000, 30_000),
    # Credit
    "credit.hy_spread": (100, 3_000),
    "credit.ig_spread": (20, 1_000),
    "credit.sloos_tightening_ci": (-100, 100),
    # Sentiment
    "sentiment.consumer_sentiment": (30, 120),
    # Computed
    "net_liquidity": (-1_000_000, 12_000_000),
    "equity_risk_premium": (-10, 15),
    "vix_vs_realized": (-100, 100),
    "spy_drawdown_from_52w_high": (-80, 1),
    "qqq_iwm_ratio": (0.5, 8),
    "federal_debt_to_gdp": (0, 300),
    "interest_receipts_ratio": (0, 100),
    "buffett_indicator": (0.2, 5),
    # Web-sourced
    "ism_pmi": (25, 75),
    "shiller_cape": (5, 80),
    "finra_margin_debt": (50, 3_000),
    "total_debt_to_gdp": (50, 500),
    "top10_wealth_share": (30, 95),
    "deficit_pct_gdp": (-5, 25),
    "china_credit_impulse": (-15, 25),
    "weighted_avg_interest_rate": (0, 15),
    "usdcny": (4, 10),
    "insider_sell_buy_ratio": (0, 20),
    "consumer_confidence": (70, 110),
    "passive_fund_share": (10, 90),
    "cb_gold_purchases": (0, 3_000),
    "rmb_swift_share": (0, 15),
    "sp500_net_margin": (0, 25),
    "em_dm_pe_gap": (-20, 40),
    # Market data (key tickers)
    "^VIX": (5, 90),
}

# Staleness thresholds for web-sourced data (days since fetch).
STALENESS_DAYS: dict[str, int] = {
    "ism_pmi": 35,
    "shiller_cape": 60,
    "finra_margin_debt": 60,
    "total_debt_to_gdp": 90,
    "top10_wealth_share": 90,
    "deficit_pct_gdp": 45,
    "china_credit_impulse": 90,
    "weighted_avg_interest_rate": 60,
    "usdcny": 7,
    "insider_sell_buy_ratio": 14,
    "consumer_confidence": 45,
    "passive_fund_share": 180,
    "cb_gold_purchases": 180,
    "rmb_swift_share": 90,
    "sp500_net_margin": 90,
    "em_dm_pe_gap": 60,
}

# Max reasonable absolute change between consecutive briefings.
ANOMALY_THRESHOLDS: dict[str, float] = {
    "growth.unemployment": 2.0,
    "growth.ism_proxy": 10,
    "inflation.cpi_yoy": 2.0,
    "inflation.core_pce": 1.5,
    "rates.fed_funds": 1.0,
    "rates.treasury_10y": 1.5,
    "credit.hy_spread": 300,
    "credit.ig_spread": 100,
    "sentiment.consumer_sentiment": 20,
    # Web-sourced
    "ism_pmi": 8,
    "shiller_cape": 10,
    "usdcny": 0.5,
}


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------

def _check_completeness(briefing: BriefingPacket) -> list[ValidationCheck]:
    """Check that expected fields exist and are non-null."""
    checks: list[ValidationCheck] = []

    sections = {
        "growth": briefing.growth,
        "inflation": briefing.inflation,
        "rates": briefing.rates,
        "liquidity": briefing.liquidity,
        "credit": briefing.credit,
        "sentiment": briefing.sentiment,
    }

    # 1. Check that all critical section fields exist AND are non-null.
    checked: set[str] = set()
    for full_path in sorted(CRITICAL_FIELDS):
        if "." not in full_path:
            continue
        section_name, field_name = full_path.split(".", 1)
        section = sections.get(section_name, {})
        value = section.get(field_name)
        checked.add(full_path)
        if value is None:
            checks.append(ValidationCheck(
                field=full_path,
                check_type="completeness",
                severity="error",
                message=f"Missing critical field: {full_path}",
            ))

    # 2. Check non-critical existing fields that are null.
    for section_name, section_data in sections.items():
        for field_name, value in section_data.items():
            full_path = f"{section_name}.{field_name}"
            if full_path in checked or value is not None:
                continue
            checks.append(ValidationCheck(
                field=full_path,
                check_type="completeness",
                severity="warning",
                message=f"Missing field: {full_path}",
            ))

    # 3. Critical computed fields.
    for field_name in sorted(CRITICAL_COMPUTED):
        if briefing.computed.get(field_name) is None:
            checks.append(ValidationCheck(
                field=field_name,
                check_type="completeness",
                severity="error",
                message=f"Missing critical computed field: {field_name}",
            ))

    return checks


def _check_ranges(briefing: BriefingPacket) -> list[ValidationCheck]:
    """Check that values fall within reasonable bounds."""
    checks: list[ValidationCheck] = []

    # Section fields
    sections = {
        "growth": briefing.growth,
        "inflation": briefing.inflation,
        "rates": briefing.rates,
        "liquidity": briefing.liquidity,
        "credit": briefing.credit,
        "sentiment": briefing.sentiment,
    }

    for section_name, section_data in sections.items():
        for field_name, value in section_data.items():
            if value is None:
                continue
            full_path = f"{section_name}.{field_name}"
            bounds = RANGE_BOUNDS.get(full_path)
            if bounds and (value < bounds[0] or value > bounds[1]):
                checks.append(ValidationCheck(
                    field=full_path,
                    check_type="range",
                    severity="warning",
                    message=f"{full_path} = {value} outside [{bounds[0]}, {bounds[1]}]",
                    details={"value": value, "min": bounds[0], "max": bounds[1]},
                ))

    # Computed fields
    for field_name, value in briefing.computed.items():
        if value is None:
            continue
        bounds = RANGE_BOUNDS.get(field_name)
        if bounds and (value < bounds[0] or value > bounds[1]):
            checks.append(ValidationCheck(
                field=field_name,
                check_type="range",
                severity="warning",
                message=f"{field_name} = {value} outside [{bounds[0]}, {bounds[1]}]",
                details={"value": value, "min": bounds[0], "max": bounds[1]},
            ))

    # Web-sourced fields
    for field_name, ws in briefing.web_sourced.items():
        bounds = RANGE_BOUNDS.get(field_name)
        if bounds and (ws.value < bounds[0] or ws.value > bounds[1]):
            checks.append(ValidationCheck(
                field=field_name,
                check_type="range",
                severity="warning",
                message=f"web:{field_name} = {ws.value} outside [{bounds[0]}, {bounds[1]}]",
                details={"value": ws.value, "min": bounds[0], "max": bounds[1]},
            ))

    # VIX (from market data, not sections)
    vix_md = briefing.markets.get("^VIX")
    vix_bounds = RANGE_BOUNDS.get("^VIX")
    if vix_md and vix_md.price is not None and vix_bounds:
        if vix_md.price < vix_bounds[0] or vix_md.price > vix_bounds[1]:
            checks.append(ValidationCheck(
                field="^VIX",
                check_type="range",
                severity="warning",
                message=f"VIX = {vix_md.price} outside [{vix_bounds[0]}, {vix_bounds[1]}]",
                details={"value": vix_md.price, "min": vix_bounds[0], "max": vix_bounds[1]},
            ))

    return checks


def _check_consistency(briefing: BriefingPacket) -> list[ValidationCheck]:
    """Check cross-field invariants."""
    checks: list[ValidationCheck] = []

    # IG spread must be < HY spread
    ig = briefing.credit.get("ig_spread")
    hy = briefing.credit.get("hy_spread")
    if ig is not None and hy is not None and ig >= hy:
        checks.append(ValidationCheck(
            field="credit.ig_spread / credit.hy_spread",
            check_type="consistency",
            severity="error",
            message=f"IG spread ({ig}) >= HY spread ({hy}) -- IG must be lower",
            details={"ig_spread": ig, "hy_spread": hy},
        ))

    # 3M rate tracks fed funds (within 75bps)
    t3m = briefing.rates.get("treasury_3m")
    ff = briefing.rates.get("fed_funds")
    if t3m is not None and ff is not None:
        delta = abs(t3m - ff)
        if delta > 0.75:
            checks.append(ValidationCheck(
                field="rates.treasury_3m / rates.fed_funds",
                check_type="consistency",
                severity="warning",
                message=f"3M rate ({t3m}) differs from fed funds ({ff}) by {delta:.2f}pp",
                details={"treasury_3m": t3m, "fed_funds": ff, "delta": round(delta, 2)},
            ))

    # Net liquidity = BS - TGA - RRP (within 1% tolerance)
    net_liq = briefing.computed.get("net_liquidity")
    bs = briefing.liquidity.get("fed_balance_sheet")
    tga = briefing.liquidity.get("tga")
    rrp = briefing.liquidity.get("reverse_repo")
    if all(v is not None for v in (net_liq, bs, tga, rrp)):
        expected = bs - tga - rrp
        if expected != 0:
            pct_diff = abs(net_liq - expected) / abs(expected) * 100
            if pct_diff > 1:
                checks.append(ValidationCheck(
                    field="net_liquidity",
                    check_type="consistency",
                    severity="error",
                    message=f"Net liquidity ({net_liq:,.0f}) != BS-TGA-RRP ({expected:,.0f}), diff {pct_diff:.1f}%",
                    details={"net_liq": net_liq, "expected": expected, "pct_diff": round(pct_diff, 1)},
                ))

    # 5Y breakeven > 10Y breakeven by >1pp is unusual
    be5y = briefing.inflation.get("breakeven_5y")
    be10y = briefing.inflation.get("breakeven_10y")
    if be5y is not None and be10y is not None and be5y > be10y + 1.0:
        checks.append(ValidationCheck(
            field="inflation.breakeven_5y / inflation.breakeven_10y",
            check_type="consistency",
            severity="info",
            message=f"5Y breakeven ({be5y}) exceeds 10Y ({be10y}) by >{1.0}pp -- unusual",
            details={"breakeven_5y": be5y, "breakeven_10y": be10y},
        ))

    # Deficit consistency: computed pace vs web-sourced % of GDP
    deficit_pace = briefing.computed.get("deficit_pace_annualized")
    deficit_ws = briefing.web_sourced.get("deficit_pct_gdp")
    gdp = briefing.growth.get("gdp_latest")
    if deficit_pace is not None and deficit_ws is not None and gdp is not None and gdp > 0:
        implied_B = (deficit_ws.value / 100) * gdp
        if implied_B > 0 and deficit_pace > 0:
            ratio = max(deficit_pace, implied_B) / min(deficit_pace, implied_B)
            if ratio > 2.0:
                checks.append(ValidationCheck(
                    field="deficit_pace / deficit_pct_gdp",
                    check_type="consistency",
                    severity="warning",
                    message=(
                        f"FRED deficit pace (${deficit_pace:.0f}B/yr) vs "
                        f"web deficit ({deficit_ws.value:.1f}% of GDP = ${implied_B:.0f}B/yr) -- "
                        f"ratio {ratio:.1f}x"
                    ),
                    details={
                        "fred_deficit_B": deficit_pace,
                        "web_deficit_pct": deficit_ws.value,
                        "implied_B": round(implied_B, 0),
                    },
                ))

    return checks


def _check_cross_source(briefing: BriefingPacket) -> list[ValidationCheck]:
    """Check agreement between overlapping data sources."""
    checks: list[ValidationCheck] = []

    # ISM proxy (MANEMP-derived) vs actual ISM (web-sourced).
    # This is the critical check — ISM proxy disagreeing on expansion/contraction
    # was the bug that triggered the entire data enrichment effort.
    ism_proxy = briefing.growth.get("ism_proxy")
    ism_actual = briefing.web_sourced.get("ism_pmi")
    if ism_proxy is not None and ism_actual is not None:
        proxy_expanding = ism_proxy > 50
        actual_expanding = ism_actual.value > 50
        if proxy_expanding != actual_expanding:
            checks.append(ValidationCheck(
                field="growth.ism_proxy / web:ism_pmi",
                check_type="cross_source",
                severity="error",
                message=(
                    f"ISM proxy ({ism_proxy:.1f}, "
                    f"{'expansion' if proxy_expanding else 'contraction'}) disagrees with "
                    f"actual ISM ({ism_actual.value:.1f}, "
                    f"{'expansion' if actual_expanding else 'contraction'}) "
                    f"on expansion/contraction divide"
                ),
                details={
                    "ism_proxy": ism_proxy,
                    "ism_actual": ism_actual.value,
                    "proxy_signal": "expansion" if proxy_expanding else "contraction",
                    "actual_signal": "expansion" if actual_expanding else "contraction",
                },
            ))
        else:
            delta = abs(ism_proxy - ism_actual.value)
            if delta > 5:
                checks.append(ValidationCheck(
                    field="growth.ism_proxy / web:ism_pmi",
                    check_type="cross_source",
                    severity="info",
                    message=(
                        f"ISM proxy ({ism_proxy:.1f}) and actual ({ism_actual.value:.1f}) "
                        f"agree on direction but differ by {delta:.1f} points"
                    ),
                    details={"ism_proxy": ism_proxy, "ism_actual": ism_actual.value, "delta": round(delta, 1)},
                ))

    # UMich sentiment vs OECD consumer confidence — different indices,
    # flag if they diverge on consumer outlook relative to neutral.
    umich = briefing.sentiment.get("consumer_sentiment")
    oecd = briefing.web_sourced.get("consumer_confidence")
    if umich is not None and oecd is not None:
        umich_positive = umich > 70
        oecd_positive = oecd.value > 99
        if umich_positive != oecd_positive:
            checks.append(ValidationCheck(
                field="sentiment / web:consumer_confidence",
                check_type="cross_source",
                severity="info",
                message=(
                    f"UMich ({umich:.1f}) and OECD ({oecd.value:.1f}) "
                    f"diverge on consumer outlook"
                ),
                details={"umich": umich, "oecd": oecd.value},
            ))

    return checks


def _check_staleness(briefing: BriefingPacket) -> list[ValidationCheck]:
    """Check web-sourced data age against per-field thresholds."""
    checks: list[ValidationCheck] = []
    now = datetime.now(timezone.utc)

    for field_name, ws in briefing.web_sourced.items():
        max_days = STALENESS_DAYS.get(field_name)
        if max_days is None:
            continue

        if not ws.fetched_at:
            checks.append(ValidationCheck(
                field=field_name,
                check_type="staleness",
                severity="warning",
                message=f"web:{field_name} has no fetched_at timestamp",
            ))
            continue

        try:
            fetched = datetime.fromisoformat(ws.fetched_at)
            if fetched.tzinfo is None:
                fetched = fetched.replace(tzinfo=timezone.utc)
            age_days = (now - fetched).total_seconds() / 86400
            if age_days > max_days:
                checks.append(ValidationCheck(
                    field=field_name,
                    check_type="staleness",
                    severity="warning",
                    message=f"web:{field_name} is {age_days:.0f}d old (threshold: {max_days}d)",
                    details={
                        "age_days": round(age_days, 1),
                        "threshold_days": max_days,
                        "fetched_at": ws.fetched_at,
                    },
                ))
        except (ValueError, TypeError):
            checks.append(ValidationCheck(
                field=field_name,
                check_type="staleness",
                severity="warning",
                message=f"web:{field_name} has unparseable fetched_at: {ws.fetched_at}",
            ))

    return checks


def _check_anomalies(
    briefing: BriefingPacket, previous: BriefingPacket,
) -> list[ValidationCheck]:
    """Flag values that jumped unreasonably vs the previous briefing."""
    checks: list[ValidationCheck] = []

    # Section fields
    for section_name in ("growth", "inflation", "rates", "liquidity", "credit", "sentiment"):
        current_section = getattr(briefing, section_name, {})
        previous_section = getattr(previous, section_name, {})

        for field_name in current_section:
            full_path = f"{section_name}.{field_name}"
            threshold = ANOMALY_THRESHOLDS.get(full_path)
            if threshold is None:
                continue

            curr = current_section.get(field_name)
            prev = previous_section.get(field_name)
            if curr is None or prev is None:
                continue

            delta = abs(curr - prev)
            if delta > threshold:
                checks.append(ValidationCheck(
                    field=full_path,
                    check_type="anomaly",
                    severity="warning",
                    message=(
                        f"{full_path} jumped {delta:.2f} "
                        f"(prev={prev:.2f}, curr={curr:.2f}, threshold={threshold})"
                    ),
                    details={
                        "previous": prev, "current": curr,
                        "delta": round(delta, 2), "threshold": threshold,
                    },
                ))

    # Web-sourced fields
    for field_name in briefing.web_sourced:
        threshold = ANOMALY_THRESHOLDS.get(field_name)
        if threshold is None:
            continue

        curr_ws = briefing.web_sourced.get(field_name)
        prev_ws = previous.web_sourced.get(field_name)
        if curr_ws is None or prev_ws is None:
            continue

        delta = abs(curr_ws.value - prev_ws.value)
        if delta > threshold:
            checks.append(ValidationCheck(
                field=field_name,
                check_type="anomaly",
                severity="warning",
                message=(
                    f"web:{field_name} jumped {delta:.2f} "
                    f"(prev={prev_ws.value:.2f}, curr={curr_ws.value:.2f}, "
                    f"threshold={threshold})"
                ),
                details={
                    "previous": prev_ws.value, "current": curr_ws.value,
                    "delta": round(delta, 2), "threshold": threshold,
                },
            ))

    return checks


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def validate_briefing(
    briefing: BriefingPacket,
    previous_briefing: Optional[BriefingPacket] = None,
) -> ValidationReport:
    """Run all validation checks on a briefing packet.

    Args:
        briefing: The current briefing to validate.
        previous_briefing: Optional previous briefing for anomaly detection.

    Returns:
        ValidationReport with all check results.
    """
    checks: list[ValidationCheck] = []

    checks.extend(_check_completeness(briefing))
    checks.extend(_check_ranges(briefing))
    checks.extend(_check_consistency(briefing))
    checks.extend(_check_cross_source(briefing))
    checks.extend(_check_staleness(briefing))

    if previous_briefing is not None:
        checks.extend(_check_anomalies(briefing, previous_briefing))

    errors = sum(1 for c in checks if c.severity == "error")
    warnings = sum(1 for c in checks if c.severity == "warning")

    if errors >= 3:
        quality = "poor"
    elif errors > 0 or warnings > 5:
        quality = "degraded"
    else:
        quality = "good"

    report = ValidationReport(
        checks=checks,
        errors=errors,
        warnings=warnings,
        overall_quality=quality,
    )

    logger.info(
        "Validation: %s (%d errors, %d warnings, %d checks)",
        quality, errors, warnings, len(checks),
    )

    return report
