# test_realization.py — Tests for expression-level realization pure functions (v6).
# Phase 1: compute_expression_return, compute_realization_ratios, compute_time_elapsed_pct
# Phase 2: validate_payoff_band
# Phase 4: compute_freshness_label, compute_realization_cap
import pytest

from backend.realization import (
    compute_expression_return,
    compute_freshness_label,
    compute_realization_cap,
    compute_realization_ratios,
    compute_time_elapsed_pct,
    validate_payoff_band,
    REALIZATION_CAPS,
    TIME_THRESHOLD,
)


# --- compute_expression_return ---

def test_single_leg_long():
    """LONG entry 100, current 115 -> 0.15"""
    result = compute_expression_return(
        predicted_assets=["SPY"],
        asset_direction={"SPY": "LONG"},
        entry_prices={"SPY": 100.0},
        current_prices={"SPY": 115.0},
    )
    assert result == pytest.approx(0.15)


def test_single_leg_short():
    """SHORT entry 100, current 85 -> 0.15 (direction-adjusted)"""
    result = compute_expression_return(
        predicted_assets=["SPY"],
        asset_direction={"SPY": "SHORT"},
        entry_prices={"SPY": 100.0},
        current_prices={"SPY": 85.0},
    )
    assert result == pytest.approx(0.15)


def test_long_short_pair():
    """LONG entry 100->120 (0.20), SHORT entry 200->180 (0.10) -> mean = 0.15"""
    result = compute_expression_return(
        predicted_assets=["DBC", "QQQ"],
        asset_direction={"DBC": "LONG", "QQQ": "SHORT"},
        entry_prices={"DBC": 100.0, "QQQ": 200.0},
        current_prices={"DBC": 120.0, "QQQ": 180.0},
    )
    assert result == pytest.approx(0.15)


def test_missing_ticker_returns_none():
    """Missing ticker in current_prices -> None"""
    result = compute_expression_return(
        predicted_assets=["SPY", "GLD"],
        asset_direction={"SPY": "LONG", "GLD": "SHORT"},
        entry_prices={"SPY": 100.0, "GLD": 150.0},
        current_prices={"SPY": 110.0},  # GLD missing
    )
    assert result is None


def test_empty_assets_returns_none():
    result = compute_expression_return(
        predicted_assets=[],
        asset_direction={},
        entry_prices={},
        current_prices={},
    )
    assert result is None


def test_zero_entry_price_returns_none():
    result = compute_expression_return(
        predicted_assets=["SPY"],
        asset_direction={"SPY": "LONG"},
        entry_prices={"SPY": 0.0},
        current_prices={"SPY": 100.0},
    )
    assert result is None


def test_default_direction_is_long():
    """If ticker not in asset_direction, defaults to LONG."""
    result = compute_expression_return(
        predicted_assets=["SPY"],
        asset_direction={},  # no direction specified
        entry_prices={"SPY": 100.0},
        current_prices={"SPY": 110.0},
    )
    assert result == pytest.approx(0.10)


# --- compute_realization_ratios ---

def test_realization_vs_lower():
    """expression_return 0.25, lower 0.15 -> 1.667"""
    ratios = compute_realization_ratios(0.25, 0.15, 0.30)
    assert ratios["realization_vs_lower"] == pytest.approx(1.6667, rel=1e-3)


def test_realization_vs_upper():
    """expression_return 0.25, upper 0.30 -> 0.833"""
    ratios = compute_realization_ratios(0.25, 0.15, 0.30)
    assert ratios["realization_vs_upper"] == pytest.approx(0.8333, rel=1e-3)


def test_realization_zero_lower():
    """Zero lower bound -> None for that ratio."""
    ratios = compute_realization_ratios(0.25, 0.0, 0.30)
    assert ratios["realization_vs_lower"] is None
    assert ratios["realization_vs_upper"] == pytest.approx(0.8333, rel=1e-3)


def test_realization_negative_bounds():
    """Negative bounds -> None."""
    ratios = compute_realization_ratios(0.10, -0.05, -0.10)
    assert ratios["realization_vs_lower"] is None
    assert ratios["realization_vs_upper"] is None


# --- compute_time_elapsed_pct ---

def test_time_at_entry():
    """At entry date -> 0.0"""
    result = compute_time_elapsed_pct("2026-01-01", "2026-07-01", "2026-01-01")
    assert result == pytest.approx(0.0)


def test_time_at_end():
    """At end date -> 1.0"""
    result = compute_time_elapsed_pct("2026-01-01", "2026-07-01", "2026-07-01")
    assert result == pytest.approx(1.0)


def test_time_at_midpoint():
    """At midpoint of a 100-day window -> 0.5"""
    result = compute_time_elapsed_pct("2026-01-01", "2026-04-11", "2026-02-19")
    # Jan 1 to Apr 11 = 100 days. Jan 1 to Feb 19 = 49 days. 49/100 = 0.49
    # Let me pick exact midpoint: 50 days in = Feb 20
    result = compute_time_elapsed_pct("2026-01-01", "2026-04-11", "2026-02-20")
    assert result == pytest.approx(0.5)


def test_time_after_end_clamped():
    """After end date -> 1.0 (clamped)"""
    result = compute_time_elapsed_pct("2026-01-01", "2026-07-01", "2026-12-31")
    assert result == pytest.approx(1.0)


def test_time_before_entry_clamped():
    """Before entry date -> 0.0 (clamped)"""
    result = compute_time_elapsed_pct("2026-03-01", "2026-07-01", "2026-01-01")
    assert result == pytest.approx(0.0)


def test_time_zero_window():
    """Entry == end -> 1.0 (degenerate window)."""
    result = compute_time_elapsed_pct("2026-01-01", "2026-01-01", "2026-01-01")
    assert result == pytest.approx(1.0)


# --- validate_payoff_band ---

def test_valid_payoff_band():
    """A well-formed payoff band produces no errors."""
    errors = validate_payoff_band(0.10, 0.25, "2026-09-30", as_of_date="2026-04-01")
    assert errors == []


def test_lower_equals_upper_rejected():
    """Lower == upper means the band has zero width -> rejected."""
    errors = validate_payoff_band(0.15, 0.15, "2026-09-30", as_of_date="2026-04-01")
    assert any("less than" in e for e in errors)


def test_lower_exceeds_upper_rejected():
    """Lower > upper is malformed -> rejected."""
    errors = validate_payoff_band(0.30, 0.15, "2026-09-30", as_of_date="2026-04-01")
    assert any("less than" in e for e in errors)


def test_upper_exceeds_ceiling_rejected():
    """Upper > 1.0 (predicting more than a double) -> rejected."""
    errors = validate_payoff_band(0.10, 1.50, "2026-09-30", as_of_date="2026-04-01")
    assert any("1.0" in e for e in errors)


def test_past_date_rejected():
    """End date in the past -> rejected."""
    errors = validate_payoff_band(0.10, 0.25, "2025-01-01", as_of_date="2026-04-01")
    assert any("future" in e for e in errors)


def test_date_too_far_rejected():
    """End date more than 12 months out -> rejected."""
    errors = validate_payoff_band(0.10, 0.25, "2027-06-01", as_of_date="2026-04-01")
    assert any("12 months" in e for e in errors)


def test_invalid_date_format_rejected():
    """Non-ISO date string -> rejected."""
    errors = validate_payoff_band(0.10, 0.25, "not-a-date", as_of_date="2026-04-01")
    assert any("valid ISO date" in e for e in errors)


def test_negative_lower_rejected():
    """Negative lower bound -> rejected."""
    errors = validate_payoff_band(-0.05, 0.25, "2026-09-30", as_of_date="2026-04-01")
    assert any("positive" in e for e in errors)


def test_zero_lower_rejected():
    """Zero lower bound -> rejected (must be positive, not zero)."""
    errors = validate_payoff_band(0.0, 0.25, "2026-09-30", as_of_date="2026-04-01")
    assert any("positive" in e for e in errors)


def test_multiple_errors_reported():
    """A truly malformed band should report all errors, not just the first."""
    errors = validate_payoff_band(-0.1, 1.5, "2020-01-01", as_of_date="2026-04-01")
    # Should have: negative lower, upper > 1.0, lower >= upper, past date
    assert len(errors) >= 3


# --- compute_freshness_label (Phase 4) ---
# The 2x3 matrix: magnitude (below lower / within band / above upper) x time (early / late)

def test_freshness_fresh():
    """Below lower bound + early window = FRESH."""
    label = compute_freshness_label(
        realization_vs_lower=0.50,   # below lower (< 1.0)
        realization_vs_upper=0.25,   # below upper (< 1.0)
        time_elapsed_pct=0.20,       # early (< 0.50)
    )
    assert label == "FRESH"


def test_freshness_underperforming():
    """Below lower bound + late window = UNDERPERFORMING."""
    label = compute_freshness_label(
        realization_vs_lower=0.50,
        realization_vs_upper=0.25,
        time_elapsed_pct=0.70,       # late (>= 0.50)
    )
    assert label == "UNDERPERFORMING"


def test_freshness_working():
    """Within band (at or above lower, below upper) + early window = WORKING."""
    label = compute_freshness_label(
        realization_vs_lower=1.20,   # at/above lower (>= 1.0)
        realization_vs_upper=0.60,   # below upper (< 1.0)
        time_elapsed_pct=0.30,       # early
    )
    assert label == "WORKING"


def test_freshness_mature():
    """Within band + late window = MATURE."""
    label = compute_freshness_label(
        realization_vs_lower=1.20,
        realization_vs_upper=0.60,
        time_elapsed_pct=0.80,       # late
    )
    assert label == "MATURE"


def test_freshness_accelerating():
    """Above upper bound + early window = ACCELERATING."""
    label = compute_freshness_label(
        realization_vs_lower=2.00,   # well above lower
        realization_vs_upper=1.50,   # above upper (>= 1.0)
        time_elapsed_pct=0.25,       # early
    )
    assert label == "ACCELERATING"


def test_freshness_expressed():
    """Above upper bound + late window = EXPRESSED."""
    label = compute_freshness_label(
        realization_vs_lower=2.00,
        realization_vs_upper=1.50,
        time_elapsed_pct=0.75,       # late
    )
    assert label == "EXPRESSED"


def test_freshness_indeterminate_none_lower():
    """Missing lower ratio -> INDETERMINATE."""
    label = compute_freshness_label(None, 0.50, 0.30)
    assert label == "INDETERMINATE"


def test_freshness_indeterminate_none_upper():
    """Missing upper ratio -> INDETERMINATE."""
    label = compute_freshness_label(0.50, None, 0.30)
    assert label == "INDETERMINATE"


def test_freshness_indeterminate_both_none():
    """Both ratios None -> INDETERMINATE."""
    label = compute_freshness_label(None, None, 0.50)
    assert label == "INDETERMINATE"


def test_freshness_at_time_threshold_boundary():
    """Exactly at TIME_THRESHOLD is 'late' (>= comparison)."""
    # Below lower + exactly at threshold = UNDERPERFORMING (late)
    label = compute_freshness_label(0.50, 0.25, TIME_THRESHOLD)
    assert label == "UNDERPERFORMING"


def test_freshness_at_lower_boundary():
    """realization_vs_lower exactly 1.0 = 'within band' (>= 1.0 check)."""
    label = compute_freshness_label(
        realization_vs_lower=1.0,    # exactly at lower bound
        realization_vs_upper=0.50,   # below upper
        time_elapsed_pct=0.20,       # early
    )
    assert label == "WORKING"


def test_freshness_at_upper_boundary():
    """realization_vs_upper exactly 1.0 = 'above upper' (>= 1.0 check)."""
    label = compute_freshness_label(
        realization_vs_lower=2.0,
        realization_vs_upper=1.0,    # exactly at upper bound
        time_elapsed_pct=0.20,       # early
    )
    assert label == "ACCELERATING"


# --- compute_realization_cap (Phase 4) ---

def test_cap_fresh_is_none():
    assert compute_realization_cap("FRESH") is None


def test_cap_working_is_none():
    assert compute_realization_cap("WORKING") is None


def test_cap_accelerating_is_none():
    assert compute_realization_cap("ACCELERATING") is None


def test_cap_underperforming_is_none():
    assert compute_realization_cap("UNDERPERFORMING") is None


def test_cap_mature_is_7():
    assert compute_realization_cap("MATURE") == 7.0


def test_cap_expressed_is_5():
    assert compute_realization_cap("EXPRESSED") == 5.0


def test_cap_indeterminate_is_none():
    assert compute_realization_cap("INDETERMINATE") is None


def test_cap_unknown_label_is_none():
    """Unknown label falls back to None (graceful degradation)."""
    assert compute_realization_cap("BOGUS") is None


# --- Realization cap integration with conviction scoring (Phase 4) ---

def test_conviction_realization_cap_expressed():
    """EXPRESSED freshness label should cap conviction at 5.0."""
    from backend.schemas.scoring import ConvictionInput
    from backend.engine.conviction import score_conviction

    inp = ConvictionInput(
        hypothesis_id="test-expressed",
        support_strength=0.90,
        evidence_quality=0.90,
        convergence=0.80,
        falsifier_clarity=0.80,
        horizon_alignment=0.80,     # no horizon cap
        expression_efficiency=0.60, # no expression cap
        freshness_label="EXPRESSED",
    )
    result = score_conviction(inp)
    assert result.stage3.realization_cap == 5.0
    assert result.stage3.final <= 5.0


def test_conviction_realization_cap_mature():
    """MATURE freshness label should cap conviction at 7.0."""
    from backend.schemas.scoring import ConvictionInput
    from backend.engine.conviction import score_conviction

    inp = ConvictionInput(
        hypothesis_id="test-mature",
        support_strength=0.90,
        evidence_quality=0.90,
        convergence=0.80,
        falsifier_clarity=0.80,
        horizon_alignment=0.80,
        expression_efficiency=0.60,
        freshness_label="MATURE",
    )
    result = score_conviction(inp)
    assert result.stage3.realization_cap == 7.0
    assert result.stage3.final <= 7.0


def test_conviction_no_cap_for_fresh():
    """FRESH label should not impose any realization cap."""
    from backend.schemas.scoring import ConvictionInput
    from backend.engine.conviction import score_conviction

    inp = ConvictionInput(
        hypothesis_id="test-fresh",
        support_strength=0.90,
        evidence_quality=0.90,
        convergence=0.80,
        falsifier_clarity=0.80,
        horizon_alignment=0.80,
        expression_efficiency=0.60,
        freshness_label="FRESH",
    )
    result = score_conviction(inp)
    assert result.stage3.realization_cap is None
    # Score should not be capped by realization
    assert result.stage3.final >= 7.0


def test_conviction_no_label_no_cap():
    """Empty freshness label (pre-v6 hypotheses) should not impose a cap."""
    from backend.schemas.scoring import ConvictionInput
    from backend.engine.conviction import score_conviction

    inp = ConvictionInput(
        hypothesis_id="test-legacy",
        support_strength=0.90,
        evidence_quality=0.90,
        convergence=0.80,
        falsifier_clarity=0.80,
        horizon_alignment=0.80,
        expression_efficiency=0.60,
        freshness_label="",
    )
    result = score_conviction(inp)
    assert result.stage3.realization_cap is None


def test_conviction_realization_cap_most_restrictive():
    """When realization cap is more restrictive than horizon/expression, it wins."""
    from backend.schemas.scoring import ConvictionInput
    from backend.engine.conviction import score_conviction

    inp = ConvictionInput(
        hypothesis_id="test-min-cap",
        support_strength=0.90,
        evidence_quality=0.90,
        convergence=0.80,
        falsifier_clarity=0.80,
        horizon_alignment=0.80,      # no horizon cap
        expression_efficiency=0.60,  # no expression cap
        freshness_label="EXPRESSED", # realization cap = 5.0
    )
    result = score_conviction(inp)
    # Realization cap at 5.0 should be the binding constraint
    assert result.stage3.final == 5.0
    assert result.stage3.freshness_label == "EXPRESSED"


def test_conviction_horizon_cap_wins_over_realization():
    """When horizon cap is more restrictive than realization cap, horizon wins."""
    from backend.schemas.scoring import ConvictionInput
    from backend.engine.conviction import score_conviction

    inp = ConvictionInput(
        hypothesis_id="test-horizon-wins",
        support_strength=0.90,
        evidence_quality=0.90,
        convergence=0.80,
        falsifier_clarity=0.80,
        horizon_alignment=0.05,      # H < 0.10 → horizon cap = 1
        expression_efficiency=0.60,
        freshness_label="MATURE",    # realization cap = 7.0
    )
    result = score_conviction(inp)
    # Horizon cap at 1 is most restrictive
    assert result.stage3.horizon_cap == 1
    assert result.stage3.realization_cap == 7.0
    assert result.stage3.final <= 1.0
