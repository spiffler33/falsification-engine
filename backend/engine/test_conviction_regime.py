"""Tests for regime discount (D_r) integration in the conviction pipeline."""

from backend.engine.conviction import score_conviction
from backend.schemas.scoring import ConvictionInput


# A reusable active flag fixture (fiscal_dominance_active)
FISCAL_FLAG = {
    "flag_id": "fiscal_dominance_active",
    "affects": ["valuation_mean_reversion", "structural_fragility", "debt_cycle_short"],
    "channel_alignment": {
        "nominal_price_decline":     "mismatch",
        "inflationary_grind":        "aligned",
        "real_asset_outperformance": "aligned",
        "sector_rotation":           "neutral",
        "broad_credit_contraction":  "mismatch",
        "sector_credit_stress":      "neutral",
    },
}


def _base_input(**overrides) -> ConvictionInput:
    """Strong baseline hypothesis: RAW ~0.80 on 0-1 scale = 8.0 on 0-10."""
    defaults = dict(
        hypothesis_id="test-h1",
        support_strength=0.80,
        evidence_quality=0.80,
        convergence=0.80,
        falsifier_clarity=0.80,
        triggered_soft_falsifiers=[],
        untestable_soft_falsifiers=[],
        same_theory_overlap=0,
        diff_theory_overlap=0,
        resolution_channel="",
        active_regime_flags=[],
        horizon_alignment=0.60,
        expression_efficiency=0.50,
    )
    defaults.update(overrides)
    return ConvictionInput(**defaults)


def test_no_regime_flags_dr_is_1():
    """Without regime flags, D_r = 1.0 and has no effect."""
    inp = _base_input()
    result = score_conviction(inp)
    assert result.stage2.regime_discount == 1.0


def test_aligned_channel_dr_is_1():
    """Aligned channel under active flag -> D_r = 1.0, no penalty."""
    inp = _base_input(
        resolution_channel="inflationary_grind",
        active_regime_flags=[FISCAL_FLAG],
    )
    result = score_conviction(inp)
    assert result.stage2.regime_discount == 1.0


def test_mismatch_channel_dr_is_075():
    """Mismatched channel under active flag -> D_r = 0.75."""
    inp = _base_input(
        resolution_channel="nominal_price_decline",
        active_regime_flags=[FISCAL_FLAG],
    )
    result = score_conviction(inp)
    assert result.stage2.regime_discount == 0.75


def test_neutral_channel_dr_is_1():
    """Neutral channel under active flag -> D_r = 1.0."""
    inp = _base_input(
        resolution_channel="sector_rotation",
        active_regime_flags=[FISCAL_FLAG],
    )
    result = score_conviction(inp)
    assert result.stage2.regime_discount == 1.0


def test_mismatch_lowers_final_score():
    """Mismatch discount should produce a lower final score than aligned."""
    aligned_inp = _base_input(
        resolution_channel="inflationary_grind",
        active_regime_flags=[FISCAL_FLAG],
    )
    mismatch_inp = _base_input(
        resolution_channel="nominal_price_decline",
        active_regime_flags=[FISCAL_FLAG],
    )
    aligned_result = score_conviction(aligned_inp)
    mismatch_result = score_conviction(mismatch_inp)

    assert mismatch_result.stage3.final < aligned_result.stage3.final


def test_mismatch_score_math():
    """Verify the exact math: RAW_10 * D_f * D_u * D_r + overlap_adj.

    With all inputs at 0.80:
      RAW_01 = 0.80*0.30 + 0.80*0.30 + 0.80*0.25 + 0.80*0.15 = 0.80
      RAW_10 = 8.0
      D_f = 1.0 (no triggered soft falsifiers)
      D_u = 1.0 (no untestable falsifiers)
      D_r = 0.75 (mismatch)
      overlap_adj = 0.0
      adjusted = 8.0 * 1.0 * 1.0 * 0.75 + 0.0 = 6.0
      No gate caps active (H=0.60 >= 0.40, E=0.50 >= 0.30)
      FINAL = round(6.0) = 6
    """
    inp = _base_input(
        resolution_channel="nominal_price_decline",
        active_regime_flags=[FISCAL_FLAG],
    )
    result = score_conviction(inp)

    assert abs(result.stage1.raw - 8.0) < 0.001
    assert result.stage2.regime_discount == 0.75
    assert abs(result.stage2.adjusted - 6.0) < 0.001
    assert result.stage3.final == 6.0


def test_unknown_channel_defaults_to_neutral():
    """An unrecognized channel tag defaults to neutral (D_r = 1.0)."""
    inp = _base_input(
        resolution_channel="some_future_channel",
        active_regime_flags=[FISCAL_FLAG],
    )
    result = score_conviction(inp)
    assert result.stage2.regime_discount == 1.0


def test_empty_channel_defaults_to_neutral():
    """Empty channel string with active flags -> neutral (D_r = 1.0)."""
    inp = _base_input(
        resolution_channel="",
        active_regime_flags=[FISCAL_FLAG],
    )
    result = score_conviction(inp)
    assert result.stage2.regime_discount == 1.0
