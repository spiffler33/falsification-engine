# regime_config.py — Regime flag schema, resolution channel enumeration, alignment multipliers.
# Depends on: nothing (pure data)
# Depended on by: engine/regime.py, engine/prompt_builder.py
#
# All regime-related constants in one place for easy recalibration.
# v3 ships with one regime flag. The schema supports N flags.

REGIME_FLAGS = {
    "schema_version": 1,
    "flags": [
        {
            "flag_id": "fiscal_dominance_active",

            # TRIGGER — mechanical, computed from Pass 1 activation results
            # Binary: the flag fires or it does not. Adjacent does NOT fire.
            "trigger": {
                "module": "fiscal_dominance_liquidity",
                "condition": "Active",
            },

            # SCOPE — which modules this flag annotates
            "affects": [
                "valuation_mean_reversion",
                "structural_fragility",
                "debt_cycle_short",
            ],

            # DIRECTION — enforces DAG constraint (one-directional, no cycles)
            "dependency_direction": "fiscal_dominance_liquidity -> affected modules",

            # CHANNEL CONTEXT — prose injected into Pass 2 generation prompt
            # These guide LLM hypothesis construction. NOT scoring inputs.
            "channel_context": {
                "valuation_mean_reversion": (
                    "Resolution channel shifts from nominal price decline toward "
                    "inflationary grind. ERP comparator (risk-free rate) is itself "
                    "being debased. Equity overvaluation resolves through real return "
                    "erosion rather than nominal crash. GLD outperforms SPY in real "
                    "terms even without nominal correction."
                ),
                "structural_fragility": (
                    "Fiscal liquidity extends the fragility-building phase. The bid "
                    "under risk assets delays the Minsky moment. Magnitude of eventual "
                    "break is unchanged or amplified -- the delay compounds the fragility, "
                    "it does not resolve it. Do not reduce severity estimates because of "
                    "the fiscal backdrop."
                ),
                "debt_cycle_short": (
                    "Fiscal spending offsets monetary tightening, delaying contraction. "
                    "Late-cycle indicators may fire without triggering recession because "
                    "the fiscal channel provides a floor. The cycle is extended, not "
                    "cancelled -- the eventual contraction arrives from a more leveraged "
                    "starting point."
                ),
            },

            # CHANNEL-REGIME ALIGNMENT TABLE — mechanical, used by Pass 4
            "channel_alignment": {
                "nominal_price_decline":     "mismatch",
                "inflationary_grind":        "aligned",
                "real_asset_outperformance": "aligned",
                "sector_rotation":           "neutral",
                "broad_credit_contraction":  "mismatch",
                "sector_credit_stress":      "neutral",
            },
        }
    ],
}


RESOLUTION_CHANNELS = {
    "nominal_price_decline": {
        "description": (
            "Asset prices fall in nominal terms. The hypothesis depends on a "
            "repricing event -- sellers overwhelm buyers, multiples compress, "
            "nominal prices drop 15%+."
        ),
        "example": "SPY declines 30% as CAPE reverts from 36 to 25",
    },

    "inflationary_grind": {
        "description": (
            "Nominal prices flat or slowly rising while inflation erodes real "
            "value. The hypothesis depends on purchasing power loss, not nominal "
            "loss. Forward real returns are poor even if nominal returns are "
            "slightly positive."
        ),
        "example": "SPY returns 2% nominal annualized for 5 years while CPI runs 4-5%",
    },

    "real_asset_outperformance": {
        "description": (
            "Hard assets (gold, commodities) outperform financial assets. The "
            "hypothesis depends on debasement, inflation expectations, or "
            "structural demand (central bank buying, collateral substitution) "
            "repricing the relative value of scarce vs. nominal claims."
        ),
        "example": "GLD outperforms SPY by 15%+ over 12 months",
    },

    "sector_rotation": {
        "description": (
            "Capital moves between sectors or geographies without a broad market "
            "decline. The hypothesis depends on relative value convergence, not "
            "absolute repricing."
        ),
        "example": "RSP outperforms SPY by 8% as breadth broadens; or EEM outperforms SPY by 12%",
    },

    "broad_credit_contraction": {
        "description": (
            "Generalized deleveraging across the credit system. The hypothesis "
            "depends on a self-reinforcing cycle: tightening lending standards, "
            "rising defaults, falling asset prices, further tightening."
        ),
        "example": "HY spreads widen to 700bp+, bank lending contracts YoY, unemployment rises 2%+",
    },

    "sector_credit_stress": {
        "description": (
            "Credit stress concentrated in a specific segment without broad "
            "contagion. The hypothesis depends on idiosyncratic distress in one "
            "pocket while the broader credit system functions."
        ),
        "example": "CRE delinquencies hit 8%, KRE falls 25%, but XLF ex-regionals is flat",
    },
}


# PROVISIONAL — recalibrate after 5+ pipeline runs with regime flags active.
# mismatch: hypothesis depends on a mechanism the regime works against
# aligned: no bonus — alignment is expected, not rewarded
# neutral: regime flag has no opinion on this channel
REGIME_ALIGNMENT_MULTIPLIERS = {
    "mismatch": 0.75,
    "aligned":  1.00,
    "neutral":  1.00,
}
