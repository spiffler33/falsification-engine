# regime.py — Pass 1.5: Regime flag computation and channel-regime alignment scoring.
# Depends on: engine/regime_config.py (REGIME_FLAGS, REGIME_ALIGNMENT_MULTIPLIERS)
# Depended on by: engine/conviction.py (Stage 2 discount), engine/prompt_builder.py (flag context)
#
# Two functions:
#   compute_regime_flags() — takes Pass 1 activation results, returns active flags
#   compute_regime_discount() — takes hypothesis channel + active flags, returns multiplier

from backend.engine.regime_config import REGIME_FLAGS, REGIME_ALIGNMENT_MULTIPLIERS


def compute_regime_flags(activation_results: dict) -> list[dict]:
    """
    Called AFTER all 8 theory modules have been scored in Pass 1.
    Reads activation_results, checks each flag's trigger condition,
    returns list of active regime flags.

    Input:  {"fiscal_dominance_liquidity": "Active", "valuation_mean_reversion": "Active", ...}
    Output: [{"flag_id": "fiscal_dominance_active", "affects": [...], "channel_context": {...}, "channel_alignment": {...}}]

    Only exact match on trigger condition fires the flag.
    Adjacent does NOT fire. Inactive does NOT fire.
    """
    active_flags = []
    for flag in REGIME_FLAGS["flags"]:
        module = flag["trigger"]["module"]
        required_status = flag["trigger"]["condition"]
        if activation_results.get(module) == required_status:
            active_flags.append({
                "flag_id": flag["flag_id"],
                "affects": flag["affects"],
                "channel_context": flag["channel_context"],
                "channel_alignment": flag["channel_alignment"],
            })
    return active_flags


def compute_regime_discount(hypothesis_channel: str, active_flags: list[dict]) -> float:
    """
    Compute the regime alignment discount (D_r) for a hypothesis.

    Looks up the hypothesis's resolution channel against each active flag's
    channel_alignment table. If channel not found, defaults to "neutral" (1.0).
    If multiple flags active, takes the MINIMUM multiplier (worst-case dominates).
    If no flags active, returns 1.0 (no discount).

    Returns a float between 0.0 and 1.0 to multiply into Stage 2 of conviction.
    """
    if not active_flags:
        return 1.0

    multipliers = []
    for flag in active_flags:
        alignment = flag["channel_alignment"].get(hypothesis_channel, "neutral")
        multipliers.append(REGIME_ALIGNMENT_MULTIPLIERS[alignment])

    return min(multipliers)
