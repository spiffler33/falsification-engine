"""Tests for regime.py — Pass 1.5 regime flag computation and channel-regime alignment scoring."""

from backend.engine.regime import compute_regime_flags, compute_regime_discount


# --- compute_regime_flags tests ---

def test_no_flags_active_when_all_inactive():
    """No flags fire when all modules are Inactive."""
    activation_results = {
        "fiscal_dominance_liquidity": "Inactive",
        "valuation_mean_reversion": "Active",
        "structural_fragility": "Active",
    }
    assert compute_regime_flags(activation_results) == []


def test_no_flags_active_when_trigger_module_adjacent():
    """Adjacent does NOT fire the flag — only exact 'Active' match."""
    activation_results = {
        "fiscal_dominance_liquidity": "Adjacent",
        "valuation_mean_reversion": "Active",
    }
    assert compute_regime_flags(activation_results) == []


def test_no_flags_active_when_trigger_module_missing():
    """Missing module key does not fire any flag."""
    activation_results = {
        "valuation_mean_reversion": "Active",
    }
    assert compute_regime_flags(activation_results) == []


def test_fiscal_dominance_flag_fires_when_active():
    """fiscal_dominance_active fires when fiscal_dominance_liquidity is Active."""
    activation_results = {
        "fiscal_dominance_liquidity": "Active",
        "valuation_mean_reversion": "Active",
        "structural_fragility": "Adjacent",
        "debt_cycle_short": "Inactive",
    }
    flags = compute_regime_flags(activation_results)
    assert len(flags) == 1
    assert flags[0]["flag_id"] == "fiscal_dominance_active"
    assert "valuation_mean_reversion" in flags[0]["affects"]
    assert "structural_fragility" in flags[0]["affects"]
    assert "debt_cycle_short" in flags[0]["affects"]
    assert "nominal_price_decline" in flags[0]["channel_alignment"]
    assert "valuation_mean_reversion" in flags[0]["channel_context"]


def test_flag_output_has_required_keys():
    """Each active flag dict has exactly the four expected keys."""
    activation_results = {"fiscal_dominance_liquidity": "Active"}
    flags = compute_regime_flags(activation_results)
    assert len(flags) == 1
    expected_keys = {"flag_id", "affects", "channel_context", "channel_alignment"}
    assert set(flags[0].keys()) == expected_keys


# --- compute_regime_discount tests ---

def test_discount_no_flags_active():
    """No active flags → discount is 1.0 (no effect)."""
    assert compute_regime_discount("nominal_price_decline", []) == 1.0


def test_discount_mismatch_channel():
    """Mismatch channel returns 0.75 when fiscal_dominance_active flag is active."""
    activation_results = {"fiscal_dominance_liquidity": "Active"}
    flags = compute_regime_flags(activation_results)
    assert compute_regime_discount("nominal_price_decline", flags) == 0.75
    assert compute_regime_discount("broad_credit_contraction", flags) == 0.75


def test_discount_aligned_channel():
    """Aligned channel returns 1.0 — alignment is expected, not rewarded."""
    activation_results = {"fiscal_dominance_liquidity": "Active"}
    flags = compute_regime_flags(activation_results)
    assert compute_regime_discount("inflationary_grind", flags) == 1.0
    assert compute_regime_discount("real_asset_outperformance", flags) == 1.0


def test_discount_neutral_channel():
    """Neutral channel returns 1.0."""
    activation_results = {"fiscal_dominance_liquidity": "Active"}
    flags = compute_regime_flags(activation_results)
    assert compute_regime_discount("sector_rotation", flags) == 1.0
    assert compute_regime_discount("sector_credit_stress", flags) == 1.0


def test_discount_unknown_channel():
    """Unknown channel defaults to neutral → 1.0."""
    activation_results = {"fiscal_dominance_liquidity": "Active"}
    flags = compute_regime_flags(activation_results)
    assert compute_regime_discount("completely_made_up_channel", flags) == 1.0


def test_discount_multiple_flags_takes_minimum():
    """When multiple flags active, worst-case mismatch dominates (min multiplier)."""
    # Simulate two flags: one says mismatch (0.75), one says aligned (1.0)
    fake_flags = [
        {
            "flag_id": "flag_a",
            "channel_alignment": {"test_channel": "aligned"},
        },
        {
            "flag_id": "flag_b",
            "channel_alignment": {"test_channel": "mismatch"},
        },
    ]
    assert compute_regime_discount("test_channel", fake_flags) == 0.75


def test_discount_multiple_flags_all_aligned():
    """Multiple flags all aligned → 1.0."""
    fake_flags = [
        {"flag_id": "a", "channel_alignment": {"ch": "aligned"}},
        {"flag_id": "b", "channel_alignment": {"ch": "aligned"}},
    ]
    assert compute_regime_discount("ch", fake_flags) == 1.0
