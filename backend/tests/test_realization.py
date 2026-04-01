# test_realization.py — Tests for expression-level realization pure functions (v6 Phase 1).
import pytest

from backend.realization import (
    compute_expression_return,
    compute_realization_ratios,
    compute_time_elapsed_pct,
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
