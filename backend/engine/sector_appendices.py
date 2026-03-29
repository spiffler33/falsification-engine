# sector_appendices.py — Sector falsifier appendix constants for v4.
# Depends on: nothing (pure data)
# Depended on by: engine/prompt_builder.py (Pass 3 injection),
#                  engine/conviction.py (D_f sector discount compounding)
#
# Three sector appendices: tech_ai, energy, financials.
# These are evaluator weapons — they enter the pipeline at Pass 3 to attack
# hypotheses with sector-specific falsifiers. They do NOT enter Pass 2.
# The generator's job is theory-driven; sector data shapes what survives.

# Severity discount constants — same values as SEVERITY_WEIGHTS in conviction.py.
# Defined here for sector-level code that needs them without importing the scorer.
SEVERITY_DISCOUNTS = {
    "minor": 0.10,
    "medium": 0.25,
    "major": 0.45,
}


TECH_AI_APPENDIX = {
    "sector_id": "tech_ai",
    "display_name": "Technology / AI Concentration",
    "version": 1,
    "last_updated": "2026-03-29",
    "update_cadence": "quarterly (post-earnings for Mag 7 and TSMC) + event-driven (major AI policy, chip export controls)",
    "ticker_triggers": ["QQQ", "SMH", "XLK", "SOXX"],

    "mechanical_falsifiers": [
        {
            "falsifier_id": "tech_sf_01",
            "condition": (
                "Semiconductor inventory-to-sales ratio indicates cyclical "
                "overshoot in AI infrastructure buildout"
            ),
            "metric": "SIA or WSTS semiconductor inventory-to-sales ratio",
            "threshold": 1.5,
            "direction": "above",
            "severity": "medium",
            "data_source": "web_search",
        },
        {
            "falsifier_id": "tech_sf_02",
            "condition": (
                "Mag 7 collective earnings growth re-accelerates, justifying "
                "concentration by fundamentals rather than passive flows"
            ),
            "metric": "Mag 7 aggregate YoY earnings growth (latest quarter)",
            "threshold": 0.25,
            "direction": "above",
            "severity": "major",
            "data_source": "web_search",
        },
        {
            "falsifier_id": "tech_sf_03",
            "condition": (
                "Hyperscaler capex-to-identifiable-AI-revenue ratio shows "
                "spending is justified, not speculative"
            ),
            "metric": (
                "Combined capex of MSFT+GOOGL+AMZN+META vs. identifiable "
                "AI revenue outside hyperscalers"
            ),
            "threshold": 5.0,
            "direction": "below",
            "severity": "major",
            "data_source": "web_search",
        },
        {
            "falsifier_id": "tech_sf_04",
            "condition": (
                "AI revenue outside hyperscalers reaches critical mass, "
                "resolving the capex/revenue mismatch fragility"
            ),
            "metric": (
                "Annualized AI-related revenue outside hyperscalers "
                "(enterprise SaaS AI, AI infrastructure companies "
                "ex-hyperscalers)"
            ),
            "threshold": 150_000_000_000,
            "direction": "above",
            "severity": "major",
            "data_source": "web_search",
        },
        {
            "falsifier_id": "tech_sf_05",
            "condition": (
                "TSMC monthly revenue growth decelerates, indicating "
                "semiconductor demand peak"
            ),
            "metric": "TSMC monthly revenue YoY growth (3-month trailing average)",
            "threshold": 0.10,
            "direction": "below",
            "severity": "minor",
            "data_source": "web_search",
        },
    ],

    "evaluator_attack_vectors": [
        {
            "vector_id": "tech_av_01",
            "question": (
                "Is Mag 7 earnings growth driven by revenue growth or by "
                "cost-cutting and buybacks? If the latter, concentration "
                "justification is fragile."
            ),
            "what_to_search": (
                "Latest quarterly earnings for Mag 7 -- revenue growth vs. "
                "EPS growth, buyback programs, cost restructuring"
            ),
            "kill_condition": (
                "If 4+ of Mag 7 show EPS growth exceeding revenue growth "
                "by 10%+ and buyback yield above 3%, earnings quality "
                "concern is material -- flag WOUNDED"
            ),
        },
        {
            "vector_id": "tech_av_02",
            "question": (
                "Are chip export restrictions escalating in ways that compress "
                "semiconductor demand outside China while benefiting domestic "
                "substitution?"
            ),
            "what_to_search": (
                "Latest US-China chip export controls, TSMC/Samsung/Intel "
                "capacity allocation, China domestic chip production data"
            ),
            "kill_condition": (
                "If new export restrictions materially reduce TAM for "
                "leading-edge chips, the semiconductor demand thesis "
                "shifts -- assess impact on SMH-specific hypotheses"
            ),
        },
        {
            "vector_id": "tech_av_03",
            "question": (
                "Is the QQQ/IWM ratio compressing or expanding? Direction "
                "matters for breadth rotation hypotheses."
            ),
            "what_to_search": (
                "QQQ vs IWM relative performance over 1M, 3M, 6M; "
                "RSP vs SPY relative performance"
            ),
            "kill_condition": (
                "If QQQ/IWM ratio is expanding (large-cap outperformance "
                "accelerating), breadth rotation hypotheses are swimming "
                "upstream -- flag WOUNDED"
            ),
        },
    ],

    "metadata": {
        "parent_theories": [
            "structural_fragility",
            "valuation_mean_reversion",
        ],
        "notes": (
            "This appendix targets hypotheses about tech concentration, "
            "AI infrastructure buildout, and narrow market breadth. "
            "It is most relevant when structural_fragility Phase A is "
            "Active and the hypothesis expression involves QQQ, SMH, or XLK."
        ),
    },
}


ENERGY_APPENDIX = {
    "sector_id": "energy",
    "display_name": "Energy",
    "version": 1,
    "last_updated": "2026-03-29",
    "update_cadence": "monthly (EIA data, rig counts) + quarterly (earnings) + event-driven (OPEC+ decisions, geopolitical)",
    "ticker_triggers": ["XLE", "XOP", "OIH", "USO", "DBC"],

    "mechanical_falsifiers": [
        {
            "falsifier_id": "energy_sf_01",
            "condition": (
                "US crude oil inventories build significantly above seasonal "
                "norms, indicating demand weakness or oversupply"
            ),
            "metric": "EIA weekly crude oil inventory vs. 5-year seasonal average",
            "threshold": 0.20,
            "direction": "above",
            "severity": "medium",
            "data_source": "web_search",
        },
        {
            "falsifier_id": "energy_sf_02",
            "condition": (
                "US oil rig count rises sharply, indicating capex discipline "
                "is breaking and supply response is underway"
            ),
            "metric": "Baker Hughes US oil rig count",
            "threshold": 600,
            "direction": "above",
            "severity": "medium",
            "data_source": "web_search",
        },
        {
            "falsifier_id": "energy_sf_03",
            "condition": (
                "Energy sector capex/cash flow ratio rises, indicating the "
                "capex discipline thesis (bullish for energy equities) is "
                "weakening"
            ),
            "metric": (
                "Aggregate capex-to-operating-cash-flow ratio for top 10 "
                "US E&P companies"
            ),
            "threshold": 0.60,
            "direction": "above",
            "severity": "medium",
            "data_source": "web_search",
        },
        {
            "falsifier_id": "energy_sf_04",
            "condition": (
                "Crack spreads collapse, indicating refining margin "
                "compression that weakens integrated energy equity earnings"
            ),
            "metric": "3-2-1 crack spread (RBOB gasoline + ULSD minus 3x WTI)",
            "threshold": 15.0,
            "direction": "below",
            "severity": "minor",
            "data_source": "web_search",
        },
        {
            "falsifier_id": "energy_sf_05",
            "condition": (
                "WTI crude falls to a level that challenges the economics "
                "of marginal US production"
            ),
            "metric": "WTI crude oil spot price",
            "threshold": 50.0,
            "direction": "below",
            "severity": "major",
            "data_source": "web_search",
        },
    ],

    "evaluator_attack_vectors": [
        {
            "vector_id": "energy_av_01",
            "question": (
                "Is OPEC+ cohesion holding or are members cheating on "
                "quotas? Quota violations above 500K bpd indicate the "
                "cartel's pricing power is eroding."
            ),
            "what_to_search": (
                "Latest OPEC+ production data vs. agreed quotas, compliance "
                "rates by member, any scheduled meeting outcomes"
            ),
            "kill_condition": (
                "If aggregate overproduction exceeds 500K bpd for 2+ months, "
                "supply discipline thesis is wounded"
            ),
        },
        {
            "vector_id": "energy_av_02",
            "question": (
                "Is US strategic petroleum reserve being refilled or drained? "
                "SPR policy affects both supply/demand balance and government "
                "fiscal position."
            ),
            "what_to_search": (
                "SPR inventory levels, announced purchase/sale plans, "
                "current fill rate"
            ),
            "kill_condition": (
                "SPR drawdowns of 10M+ barrels in a quarter shift near-term "
                "supply dynamics"
            ),
        },
        {
            "vector_id": "energy_av_03",
            "question": (
                "Is natural gas pricing divergence (US HH vs. international "
                "LNG) creating or destroying value for US LNG exporters?"
            ),
            "what_to_search": (
                "Henry Hub spot vs. JKM/TTF LNG pricing, US LNG export "
                "capacity utilization"
            ),
            "kill_condition": (
                "Sustained HH-international convergence weakens the US "
                "energy export advantage thesis"
            ),
        },
    ],

    "metadata": {
        "parent_theories": [
            "fiscal_dominance_liquidity",
            "capital_flows",
        ],
        "notes": (
            "This appendix targets hypotheses about energy equity "
            "performance, commodity supply/demand dynamics, and capex "
            "discipline. Most relevant when capital_flows or "
            "fiscal_dominance_liquidity is Active and the hypothesis "
            "expression involves XLE, XOP, or USO."
        ),
    },
}


FINANCIALS_APPENDIX = {
    "sector_id": "financials",
    "display_name": "Financials",
    "version": 1,
    "last_updated": "2026-03-29",
    "update_cadence": "quarterly (bank earnings, FDIC data, SLOOS) + event-driven (regulatory changes, bank failures)",
    "ticker_triggers": ["XLF", "KRE", "KBE"],

    "mechanical_falsifiers": [
        {
            "falsifier_id": "financials_sf_01",
            "condition": (
                "CRE delinquency rate rises to levels indicating systemic "
                "stress in regional bank portfolios"
            ),
            "metric": "FDIC quarterly CRE delinquency rate (all commercial banks)",
            "threshold": 0.06,
            "direction": "above",
            "severity": "major",
            "data_source": "web_search",
        },
        {
            "falsifier_id": "financials_sf_02",
            "condition": (
                "Net interest margins compress to levels that challenge "
                "bank profitability across the sector"
            ),
            "metric": "FDIC aggregate net interest margin (all FDIC-insured institutions)",
            "threshold": 0.025,
            "direction": "below",
            "severity": "medium",
            "data_source": "web_search",
        },
        {
            "falsifier_id": "financials_sf_03",
            "condition": (
                "Major bank loan loss provisions surge, indicating expected "
                "credit deterioration"
            ),
            "metric": (
                "Aggregate quarterly loan loss provisions for top 6 US "
                "banks (JPM, BAC, WFC, C, GS, MS)"
            ),
            "threshold": 0.50,
            "direction": "above",
            "severity": "medium",
            "data_source": "web_search",
        },
        {
            "falsifier_id": "financials_sf_04",
            "condition": (
                "Regional bank deposit outflows accelerate, indicating "
                "renewed flight-to-quality or structural deposit migration"
            ),
            "metric": "KRE constituent aggregate deposit change (quarterly)",
            "threshold": -0.03,
            "direction": "below",
            "severity": "major",
            "data_source": "web_search",
        },
        {
            "falsifier_id": "financials_sf_05",
            "condition": (
                "Bank P/TBV for money-center banks rises above historical "
                "average, removing the valuation discount thesis"
            ),
            "metric": "Aggregate P/TBV for top 6 US banks",
            "threshold": 1.3,
            "direction": "above",
            "severity": "major",
            "data_source": "web_search",
        },
    ],

    "evaluator_attack_vectors": [
        {
            "vector_id": "financials_av_01",
            "question": (
                "Is the divergence between money-center and regional banks "
                "widening or narrowing? This determines whether financial "
                "sector hypotheses should be expressed via XLF (broad) or "
                "KRE/KBE (targeted)."
            ),
            "what_to_search": (
                "JPM/BAC stock performance vs. KRE index, earnings "
                "divergence, deposit flow divergence"
            ),
            "kill_condition": (
                "If money-center banks are outperforming regionals by 15%+ "
                "over 3 months, a broad XLF hypothesis is masking a split "
                "sector -- flag for expression refinement"
            ),
        },
        {
            "vector_id": "financials_av_02",
            "question": (
                "Are SLOOS lending standards tightening or easing? Direction "
                "matters more than level for credit cycle positioning."
            ),
            "what_to_search": (
                "Latest Fed Senior Loan Officer Survey results across all "
                "loan categories"
            ),
            "kill_condition": (
                "If SLOOS shows tightening across 3+ categories for 2+ "
                "consecutive quarters, credit contraction is underway -- "
                "assess whether hypothesis accounts for this"
            ),
        },
        {
            "vector_id": "financials_av_03",
            "question": (
                "Are unrealized losses on bank bond portfolios (HTM and AFS) "
                "improving or deteriorating? This is the latent risk that "
                "drove SVB."
            ),
            "what_to_search": (
                "FDIC quarterly data on unrealized losses in bank "
                "securities portfolios"
            ),
            "kill_condition": (
                "If unrealized losses exceed $500B and are concentrated in "
                "regional banks with <$100B assets, the KRE-specific risk "
                "is elevated regardless of headline NIM data"
            ),
        },
    ],

    "metadata": {
        "parent_theories": [
            "debt_cycle_short",
            "structural_fragility",
            "valuation_mean_reversion",
        ],
        "notes": (
            "This appendix targets hypotheses about bank equity "
            "performance, credit cycle positioning, and financial sector "
            "rotation. Most relevant when debt_cycle_short or "
            "structural_fragility is Active and the hypothesis expression "
            "involves XLF, KRE, or KBE."
        ),
    },
}


# Top-level registry — the injection logic iterates this list.
SECTOR_APPENDICES = [TECH_AI_APPENDIX, ENERGY_APPENDIX, FINANCIALS_APPENDIX]


# ---------------------------------------------------------------------------
# Appendix injection logic (v4 Component 2)
# ---------------------------------------------------------------------------

import re
from typing import List, Optional, Set

# Matches uppercase words of 1-5 letters bounded by word boundaries or slashes.
# Intentionally broad — false positives like "AI" or "GDP" are harmless because
# select_sector_appendices() intersects against the closed ticker_triggers sets.
_TICKER_RE = re.compile(r"(?<![A-Za-z])([A-Z]{1,5})(?![A-Za-z])")


def _get(obj: object, key: str, default=None):
    """Read a field from a dict or an object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def extract_tickers(hypothesis) -> Set[str]:
    """Pull every plausible ETF ticker from a hypothesis.

    Works with both raw generation dicts (Pass 2 output) and Pydantic
    Hypothesis model instances.

    Sources checked (in order of reliability):
      1. predicted_assets  — list[str], definitive
      2. asset_direction   — dict keys, definitive
      3. prediction        — prose text (raw generation dicts only)
      4. short_name        — prose text
      5. full_statement    — prose text
      6. mechanism         — prose text (raw generation dicts only)
    """
    tickers: Set[str] = set()

    # --- Structured fields (definitive) ---
    predicted_assets = _get(hypothesis, "predicted_assets", [])
    if predicted_assets:
        tickers.update(predicted_assets)

    asset_direction = _get(hypothesis, "asset_direction", {})
    if asset_direction:
        tickers.update(asset_direction.keys())

    # --- Text fields (scan for uppercase ticker-shaped words) ---
    for field in ("prediction", "short_name", "full_statement", "mechanism"):
        text = _get(hypothesis, field, "")
        if text:
            tickers.update(_TICKER_RE.findall(text))

    return tickers


def select_sector_appendices(
    hypotheses: List[dict],
    appendices: Optional[List[dict]] = None,
) -> List[dict]:
    """Scan generated hypotheses for ETF tickers that match sector appendix
    triggers.  Return only the appendices whose tickers appear in the
    hypothesis set.

    Args:
        hypotheses: List of hypothesis dicts from Pass 2 generation output.
        appendices: Sector appendix registry.  Defaults to SECTOR_APPENDICES.

    Returns:
        List of appendix dicts to inject into the Pass 3 elimination prompt.
        Empty list if no tickers match any appendix trigger list.
    """
    if appendices is None:
        appendices = SECTOR_APPENDICES

    # Collect all tickers mentioned across all hypotheses.
    mentioned_tickers: Set[str] = set()
    for h in hypotheses:
        mentioned_tickers.update(extract_tickers(h))

    # Match against each appendix's closed trigger list.
    selected: List[dict] = []
    for appendix in appendices:
        if mentioned_tickers & set(appendix["ticker_triggers"]):
            selected.append(appendix)

    return selected
