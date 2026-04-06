"""Tests for sector appendix injection logic (v4 Component 2).

Covers:
  - extract_tickers() pulling tickers from both dict and Pydantic hypothesis shapes
  - select_sector_appendices() returning correct appendices based on ticker overlap
"""

from backend.engine.sector_appendices import (
    SECTOR_APPENDICES,
    TECH_AI_APPENDIX,
    ENERGY_APPENDIX,
    FINANCIALS_APPENDIX,
    extract_tickers,
    select_sector_appendices,
)


# ---------------------------------------------------------------------------
# Helpers — realistic hypothesis dicts matching the actual generation output
# ---------------------------------------------------------------------------

def _hyp(**overrides) -> dict:
    """Build a minimal hypothesis dict in the actual generation output shape."""
    base = {
        "theory_id": "valuation_mean_reversion",
        "source_theories": ["valuation_mean_reversion"],
        "short_name": "Test hypothesis",
        "full_statement": "Some statement.",
        "mechanism": "A -> B -> C",
        "prediction": "SPY declines 15%.",
        "predicted_assets": ["SPY"],
        "asset_direction": {"SPY": "SHORT"},
        "hard_falsifiers": [],
        "soft_falsifiers": [],
        "timeframe": "Through Q1 2027",
        "conviction_inputs": {},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# extract_tickers — structured fields
# ---------------------------------------------------------------------------

def test_extract_tickers_from_predicted_assets():
    h = _hyp(predicted_assets=["QQQ", "SPY"], asset_direction={})
    assert "QQQ" in extract_tickers(h)
    assert "SPY" in extract_tickers(h)


def test_extract_tickers_from_asset_direction_keys():
    h = _hyp(predicted_assets=[], asset_direction={"XLE": "LONG", "TLT": "SHORT"})
    tickers = extract_tickers(h)
    assert "XLE" in tickers
    assert "TLT" in tickers


def test_extract_tickers_merges_both_structured_fields():
    """predicted_assets and asset_direction may mention different tickers."""
    h = _hyp(
        predicted_assets=["GLD", "TLT"],
        asset_direction={"GLD": "LONG", "TLT": "SHORT", "GLDM": "LONG"},
    )
    tickers = extract_tickers(h)
    assert tickers >= {"GLD", "TLT", "GLDM"}


# ---------------------------------------------------------------------------
# extract_tickers — text fields
# ---------------------------------------------------------------------------

def test_extract_tickers_from_prediction_text():
    h = _hyp(
        predicted_assets=[],
        asset_direction={},
        prediction="SMH declines 20% as semiconductor cycle peaks",
    )
    assert "SMH" in extract_tickers(h)


def test_extract_tickers_from_short_name():
    h = _hyp(
        predicted_assets=[],
        asset_direction={},
        short_name="Large-cap to small-cap rotation as QQQ/IWM ratio mean-reverts",
        prediction="",
    )
    tickers = extract_tickers(h)
    assert "QQQ" in tickers
    assert "IWM" in tickers


def test_extract_tickers_from_full_statement():
    h = _hyp(
        predicted_assets=[],
        asset_direction={},
        full_statement="XLF underperforms as credit tightens across regional banks.",
        prediction="",
    )
    assert "XLF" in extract_tickers(h)


def test_extract_tickers_from_mechanism():
    h = _hyp(
        predicted_assets=[],
        asset_direction={},
        mechanism="SOXX concentration -> supply chain risk -> drawdown",
        prediction="",
    )
    assert "SOXX" in extract_tickers(h)


def test_extract_tickers_no_false_positive_from_lowercase():
    """Lowercase words like 'the' or 'above' are not extracted as tickers."""
    h = _hyp(
        predicted_assets=[],
        asset_direction={},
        prediction="the spread is above average",
        short_name="something happens",
    )
    tickers = extract_tickers(h)
    # Only structured fields and uppercase words should appear
    assert "the" not in tickers
    assert "above" not in tickers


def test_extract_tickers_handles_pydantic_model():
    """extract_tickers works with attribute access (Pydantic-style objects)."""
    class FakeHypothesis:
        predicted_assets = ["KRE"]
        asset_direction = {"KRE": "SHORT"}
        short_name = "Regionals decline"
        full_statement = "KBE tracks alongside KRE."
        # No prediction or mechanism attrs — extract_tickers should handle missing
    tickers = extract_tickers(FakeHypothesis())
    assert "KRE" in tickers
    assert "KBE" in tickers


def test_extract_tickers_actual_generation_output_shape():
    """Test against the exact shape from mock_data/generation_output.json."""
    h = {
        "theory_id": "valuation_mean_reversion",
        "source_theories": ["valuation_mean_reversion"],
        "short_name": "Large-cap to small-cap rotation as QQQ/IWM ratio mean-reverts",
        "full_statement": (
            "QQQ/IWM ratio at 2.32 represents extreme concentration premium. "
            "Historical mean-reversion of this ratio occurs through small-cap "
            "outperformance during late-cycle phases."
        ),
        "mechanism": (
            "Extreme concentration premium -> diminishing marginal returns from "
            "mega-cap -> rotation capital seeks smaller-cap value -> IWM outperforms "
            "as QQQ/IWM ratio mean-reverts"
        ),
        "prediction": "IWM outperforms QQQ by 10-20% over next 6-12 months",
        "predicted_assets": ["IWM", "QQQ"],
        "asset_direction": {"IWM": "LONG", "QQQ": "SHORT"},
        "hard_falsifiers": [],
        "soft_falsifiers": [],
        "timeframe": "Through Q3 2026",
        "conviction_inputs": {},
    }
    tickers = extract_tickers(h)
    assert "QQQ" in tickers
    assert "IWM" in tickers


# ---------------------------------------------------------------------------
# select_sector_appendices — no match
# ---------------------------------------------------------------------------

def test_select_returns_empty_when_no_sector_tickers():
    """Hypotheses with only broad-market ETFs (SPY, TLT, GLD) match no appendix."""
    hypotheses = [
        _hyp(predicted_assets=["SPY", "TLT", "GLD"],
             asset_direction={"SPY": "SHORT", "TLT": "LONG", "GLD": "LONG"},
             prediction="SPY declines, TLT rallies, GLD rallies."),
    ]
    result = select_sector_appendices(hypotheses, SECTOR_APPENDICES)
    assert result == []


def test_select_returns_empty_for_empty_hypothesis_list():
    assert select_sector_appendices([], SECTOR_APPENDICES) == []


# ---------------------------------------------------------------------------
# select_sector_appendices — single appendix match
# ---------------------------------------------------------------------------

def test_select_returns_tech_when_qqq_mentioned():
    """QQQ triggers the tech_ai appendix."""
    hypotheses = [
        _hyp(predicted_assets=["QQQ", "SPY"],
             asset_direction={"QQQ": "SHORT", "SPY": "LONG"},
             prediction="QQQ underperforms SPY."),
    ]
    result = select_sector_appendices(hypotheses, SECTOR_APPENDICES)
    assert len(result) == 1
    assert result[0]["sector_id"] == "tech_ai"


def test_select_returns_energy_when_xle_mentioned():
    hypotheses = [
        _hyp(predicted_assets=["XLE"],
             asset_direction={"XLE": "LONG"},
             prediction="XLE rallies."),
    ]
    result = select_sector_appendices(hypotheses, SECTOR_APPENDICES)
    assert len(result) == 1
    assert result[0]["sector_id"] == "energy"


def test_select_returns_financials_when_kre_mentioned():
    hypotheses = [
        _hyp(predicted_assets=["KRE"],
             asset_direction={"KRE": "SHORT"},
             prediction="KRE declines."),
    ]
    result = select_sector_appendices(hypotheses, SECTOR_APPENDICES)
    assert len(result) == 1
    assert result[0]["sector_id"] == "financials"


# ---------------------------------------------------------------------------
# select_sector_appendices — multiple appendix matches
# ---------------------------------------------------------------------------

def test_select_returns_tech_and_energy_for_smh_xle():
    """SMH triggers tech_ai, XLE triggers energy."""
    hypotheses = [
        _hyp(predicted_assets=["SMH"],
             asset_direction={"SMH": "SHORT"},
             prediction="SMH declines."),
        _hyp(predicted_assets=["XLE"],
             asset_direction={"XLE": "LONG"},
             prediction="XLE rallies."),
    ]
    result = select_sector_appendices(hypotheses, SECTOR_APPENDICES)
    sector_ids = {a["sector_id"] for a in result}
    assert sector_ids == {"tech_ai", "energy"}


def test_select_returns_all_three_for_qqq_xle_kre():
    """QQQ -> tech_ai, XLE -> energy, KRE -> financials."""
    hypotheses = [
        _hyp(predicted_assets=["QQQ"],
             asset_direction={"QQQ": "SHORT"}),
        _hyp(predicted_assets=["XLE"],
             asset_direction={"XLE": "LONG"}),
        _hyp(predicted_assets=["KRE"],
             asset_direction={"KRE": "SHORT"}),
    ]
    result = select_sector_appendices(hypotheses, SECTOR_APPENDICES)
    sector_ids = {a["sector_id"] for a in result}
    assert sector_ids == {"tech_ai", "energy", "financials"}


# ---------------------------------------------------------------------------
# select_sector_appendices — text-only ticker mention
# ---------------------------------------------------------------------------

def test_select_matches_ticker_mentioned_only_in_text():
    """A ticker found only in prediction text (not in structured fields) still
    triggers the appendix."""
    hypotheses = [
        _hyp(predicted_assets=["SPY"],
             asset_direction={"SPY": "SHORT"},
             prediction="Rotation from QQQ into value names drives SPY lower."),
    ]
    result = select_sector_appendices(hypotheses, SECTOR_APPENDICES)
    sector_ids = {a["sector_id"] for a in result}
    assert "tech_ai" in sector_ids


# ---------------------------------------------------------------------------
# select_sector_appendices — no duplicate appendices
# ---------------------------------------------------------------------------

def test_select_no_duplicate_appendices():
    """Multiple hypotheses mentioning the same sector tickers yield only one
    copy of that appendix."""
    hypotheses = [
        _hyp(predicted_assets=["QQQ"], asset_direction={"QQQ": "SHORT"}),
        _hyp(predicted_assets=["SMH"], asset_direction={"SMH": "SHORT"}),
        _hyp(predicted_assets=["XLK"], asset_direction={"XLK": "LONG"}),
    ]
    result = select_sector_appendices(hypotheses, SECTOR_APPENDICES)
    sector_ids = [a["sector_id"] for a in result]
    assert sector_ids.count("tech_ai") == 1


# ---------------------------------------------------------------------------
# select_sector_appendices — defaults to global registry
# ---------------------------------------------------------------------------

def test_select_defaults_to_sector_appendices_registry():
    """When appendices arg is None, uses SECTOR_APPENDICES."""
    hypotheses = [
        _hyp(predicted_assets=["QQQ"], asset_direction={"QQQ": "SHORT"}),
    ]
    result = select_sector_appendices(hypotheses)
    assert len(result) == 1
    assert result[0]["sector_id"] == "tech_ai"


# ===========================================================================
# Prompt injection tests (v4 Component 3 — evaluator prompt update)
# ===========================================================================

from backend.engine.prompt_builder import build_elimination_prompt_v8
from backend.schemas.theory import (
    ActivationResult,
    ActivationTier,
    TheoryPackage,
)


def _stub_packages():
    """Minimal TheoryPackage list sufficient for build_elimination_prompt_v8."""
    return [
        TheoryPackage(
            theory_id="valuation_mean_reversion",
            core="# Valuation Mean Reversion",
            activation="",
            tactical="",
            playbook="",
            context_flags=[],
            falsifier_registry=[],
        ),
    ]


def _stub_activation_results():
    return [
        ActivationResult(
            theory_id="valuation_mean_reversion",
            score=0.72,
            tier=ActivationTier.ACTIVE,
        ),
    ]


def _stub_briefing():
    return {"rates": {"fed_funds": 5.25}, "markets": {"spy_price": 520.0}}


def _stub_hypotheses():
    """One hypothesis mentioning QQQ — triggers tech_ai appendix."""
    return [
        _hyp(
            predicted_assets=["QQQ", "SPY"],
            asset_direction={"QQQ": "SHORT", "SPY": "LONG"},
            prediction="QQQ underperforms SPY by 15% as breadth rotation continues.",
        ),
    ]


# ---------------------------------------------------------------------------
# No appendices — prompt unchanged from v3
# ---------------------------------------------------------------------------

def test_prompt_without_appendices_matches_v3():
    """When sector_appendices is None or empty, the prompt has no sector section."""
    prompt_none = build_elimination_prompt_v8(
        hypotheses=_stub_hypotheses(),
        packages=_stub_packages(),
        activation_results=_stub_activation_results(),
        briefing=_stub_briefing(),
        sector_appendices=None,
    )
    prompt_empty = build_elimination_prompt_v8(
        hypotheses=_stub_hypotheses(),
        packages=_stub_packages(),
        activation_results=_stub_activation_results(),
        briefing=_stub_briefing(),
        sector_appendices=[],
    )
    # Neither prompt should contain the sector section markers
    assert "SECTOR FALSIFIER APPENDICES" not in prompt_none
    assert "SECTOR FALSIFIER APPENDICES" not in prompt_empty
    assert "SECTOR FALSIFIER AUDIT" not in prompt_none
    assert "SECTOR FALSIFIER AUDIT" not in prompt_empty
    assert "sector_falsifier_audit" not in prompt_none
    assert "sector_falsifier_audit" not in prompt_empty
    # The two prompts should be identical (None and [] are equivalent)
    assert prompt_none == prompt_empty


# ---------------------------------------------------------------------------
# Single appendix — tech_ai
# ---------------------------------------------------------------------------

def test_prompt_with_tech_appendix_includes_sector_section():
    """Injecting the tech_ai appendix adds the full sector block."""
    prompt = build_elimination_prompt_v8(
        hypotheses=_stub_hypotheses(),
        packages=_stub_packages(),
        activation_results=_stub_activation_results(),
        briefing=_stub_briefing(),
        sector_appendices=[TECH_AI_APPENDIX],
    )
    # Header and footer markers
    assert "--- SECTOR FALSIFIER APPENDICES ---" in prompt
    assert "--- END SECTOR APPENDICES ---" in prompt
    # Sector name and triggers
    assert "SECTOR: Technology / AI Concentration" in prompt
    assert "QQQ" in prompt
    assert "SMH" in prompt
    # All five tech mechanical falsifiers
    assert "[tech_sf_01]" in prompt
    assert "[tech_sf_02]" in prompt
    assert "[tech_sf_03]" in prompt
    assert "[tech_sf_04]" in prompt
    assert "[tech_sf_05]" in prompt
    # All three attack vectors
    assert "[tech_av_01]" in prompt
    assert "[tech_av_02]" in prompt
    assert "[tech_av_03]" in prompt
    # Structured audit output template
    assert "SECTOR FALSIFIER AUDIT: {hypothesis_id}" in prompt
    assert "Metric value found:" in prompt
    assert "Triggered: YES | NO" in prompt
    assert "Relevant to this hypothesis: YES | NO | N/A" in prompt
    assert "Severity applied:" in prompt
    # Definition of relevance
    assert "DEFINITION OF RELEVANCE:" in prompt
    assert "load-bearing mechanism" in prompt
    # JSON output schema includes sector fields
    assert "sector_falsifier_audit" in prompt
    assert "attack_vector_findings" in prompt


def test_prompt_tech_falsifier_details():
    """Verify specific falsifier content is rendered correctly."""
    prompt = build_elimination_prompt_v8(
        hypotheses=_stub_hypotheses(),
        packages=_stub_packages(),
        activation_results=_stub_activation_results(),
        briefing=_stub_briefing(),
        sector_appendices=[TECH_AI_APPENDIX],
    )
    # tech_sf_01 details
    assert "SIA or WSTS semiconductor inventory-to-sales ratio" in prompt
    assert "1.5" in prompt
    assert "(above)" in prompt
    assert "Severity if triggered AND relevant: medium" in prompt
    # tech_sf_02 — major severity
    assert "Severity if triggered AND relevant: major" in prompt


# ---------------------------------------------------------------------------
# All three appendices
# ---------------------------------------------------------------------------

def test_prompt_with_all_three_appendices():
    """All three sectors appear when all three appendices are injected."""
    prompt = build_elimination_prompt_v8(
        hypotheses=_stub_hypotheses(),
        packages=_stub_packages(),
        activation_results=_stub_activation_results(),
        briefing=_stub_briefing(),
        sector_appendices=[TECH_AI_APPENDIX, ENERGY_APPENDIX, FINANCIALS_APPENDIX],
    )
    assert "SECTOR: Technology / AI Concentration" in prompt
    assert "SECTOR: Energy" in prompt
    assert "SECTOR: Financials" in prompt
    # Sample falsifiers from each sector
    assert "[tech_sf_01]" in prompt
    assert "[energy_sf_01]" in prompt
    assert "[financials_sf_01]" in prompt
    # Sample attack vectors from each sector
    assert "[tech_av_01]" in prompt
    assert "[energy_av_01]" in prompt
    assert "[financials_av_01]" in prompt
    # Still only one header/footer pair
    assert prompt.count("--- SECTOR FALSIFIER APPENDICES ---") == 1
    assert prompt.count("--- END SECTOR APPENDICES ---") == 1
    # Only one definition of relevance block
    assert prompt.count("DEFINITION OF RELEVANCE:") == 1


# ---------------------------------------------------------------------------
# Structured output format presence
# ---------------------------------------------------------------------------

def test_prompt_output_schema_includes_sector_fields_when_appendices():
    """The JSON output schema includes sector_falsifier_audit and
    attack_vector_findings only when appendices are present."""
    prompt_with = build_elimination_prompt_v8(
        hypotheses=_stub_hypotheses(),
        packages=_stub_packages(),
        activation_results=_stub_activation_results(),
        briefing=_stub_briefing(),
        sector_appendices=[TECH_AI_APPENDIX],
    )
    prompt_without = build_elimination_prompt_v8(
        hypotheses=_stub_hypotheses(),
        packages=_stub_packages(),
        activation_results=_stub_activation_results(),
        briefing=_stub_briefing(),
        sector_appendices=None,
    )
    # With appendices — schema has sector fields
    assert '"sector_falsifier_audit"' in prompt_with
    assert '"attack_vector_findings"' in prompt_with
    assert '"severity_applied"' in prompt_with
    # Without appendices — schema does NOT have sector fields
    assert '"sector_falsifier_audit"' not in prompt_without
    assert '"attack_vector_findings"' not in prompt_without


# ---------------------------------------------------------------------------
# Channel verification + sector appendices coexist
# ---------------------------------------------------------------------------

def test_prompt_with_channels_and_appendices():
    """Both channel verification and sector appendices can be present."""
    prompt = build_elimination_prompt_v8(
        hypotheses=_stub_hypotheses(),
        packages=_stub_packages(),
        activation_results=_stub_activation_results(),
        briefing=_stub_briefing(),
        has_channel_tags=True,
        sector_appendices=[TECH_AI_APPENDIX],
    )
    # Channel verification section
    assert "CHANNEL VERIFICATION" in prompt
    assert '"channel_verification"' in prompt
    # Sector appendices section
    assert "--- SECTOR FALSIFIER APPENDICES ---" in prompt
    assert '"sector_falsifier_audit"' in prompt


# ---------------------------------------------------------------------------
# Instructions match plan_v4.md Component 2 spec
# ---------------------------------------------------------------------------

def test_prompt_instructions_match_spec():
    """The five-step instruction list from plan_v4.md Component 2."""
    prompt = build_elimination_prompt_v8(
        hypotheses=_stub_hypotheses(),
        packages=_stub_packages(),
        activation_results=_stub_activation_results(),
        briefing=_stub_briefing(),
        sector_appendices=[TECH_AI_APPENDIX],
    )
    assert "1. Look up the current value of each mechanical falsifier's metric" in prompt
    assert "2. Determine if the threshold is breached (TRIGGERED or NOT TRIGGERED)" in prompt
    assert "3. If TRIGGERED: determine if the falsifier is RELEVANT" in prompt
    assert "4. State your reasoning for the relevance determination" in prompt
    assert "5. Report the result in the structured format specified below" in prompt


# ===========================================================================
# Sector falsifier audit PARSER tests (v4 Component 3 — output parsing)
# ===========================================================================

from backend.engine.output_parser import (
    parse_sector_falsifier_audits,
    parse_attack_vector_findings,
)


# ---------------------------------------------------------------------------
# Helpers — realistic evaluator output samples
# ---------------------------------------------------------------------------

WELL_FORMED_TEXT_BLOCK = """\
SECTOR FALSIFIER AUDIT: H-20260329-01
Sector: tech_ai

  [tech_sf_01]
  Metric value found: 1.2x (SIA Q4 2025 data)
  Triggered: NO
  Relevant to this hypothesis: N/A
  Reasoning: Below threshold of 1.5x; no overshoot detected.
  Severity applied: NONE

  [tech_sf_02]
  Metric value found: 28% YoY (Q4 2025 aggregate)
  Triggered: YES
  Relevant to this hypothesis: YES
  Reasoning: Mag 7 earnings re-acceleration directly undermines the hypothesis that concentration is driven by passive flows rather than fundamentals.
  Severity applied: major

  [tech_sf_03]
  Metric value found: 6.2x capex/AI-revenue ratio
  Triggered: YES
  Relevant to this hypothesis: NO
  Reasoning: The hypothesis is about breadth rotation via QQQ/IWM, not about AI capex mismatch. The capex ratio does not attack the rotation mechanism.
  Severity applied: NONE

ATTACK VECTOR FINDINGS: H-20260329-01
  [tech_av_01] Mag 7 EPS growth exceeds revenue growth by 8% on average, with buyback yield at 2.1%. Below the 10%/3% threshold for material concern.
  Impact on hypothesis: No impact on status determination.
  [tech_av_03] QQQ/IWM ratio has compressed 4% over trailing 3 months. Breadth rotation is directionally supported.
  Impact on hypothesis: Supports SURVIVED status; rotation thesis has near-term momentum.
"""


MULTI_HYPOTHESIS_TEXT = """\
SECTOR FALSIFIER AUDIT: H-20260329-01
Sector: tech_ai

  [tech_sf_01]
  Metric value found: 1.2x
  Triggered: NO
  Relevant to this hypothesis: N/A
  Reasoning: Below threshold.
  Severity applied: NONE

SECTOR FALSIFIER AUDIT: H-20260329-03
Sector: energy

  [energy_sf_01]
  Metric value found: 18% above seasonal average
  Triggered: NO
  Relevant to this hypothesis: N/A
  Reasoning: Below 20% threshold.
  Severity applied: NONE

  [energy_sf_05]
  Metric value found: $62/bbl WTI spot
  Triggered: NO
  Relevant to this hypothesis: N/A
  Reasoning: Above $50 threshold.
  Severity applied: NONE
"""


MALFORMED_TEXT_BLOCK = """\
SECTOR FALSIFIER AUDIT: H-20260329-02
Sector: financials

  [financials_sf_01]
  Metric value found: 4.8% CRE delinquency
  Triggered: NO
  Relevant to this hypothesis: N/A
  Reasoning: Below 6% threshold.
  Severity applied: NONE

  [financials_sf_02]
  This entry is garbled and missing the expected fields.
  The evaluator deviated from the format entirely here.

  [financials_sf_03]
  Metric value found: Provisions up 35% QoQ
  Triggered: NO
  Relevant to this hypothesis: N/A
  Reasoning: Below 50% QoQ threshold.
  Severity applied: NONE
"""


# ---------------------------------------------------------------------------
# JSON-format test data
# ---------------------------------------------------------------------------

def _json_items_with_audit():
    """Elimination items with sector_falsifier_audit JSON fields."""
    return [
        {
            "hypothesis_id": "H-20260329-01",
            "status": "WOUNDED",
            "sector_falsifier_audit": [
                {
                    "sector_id": "tech_ai",
                    "falsifier_id": "tech_sf_02",
                    "metric_value_found": "28% YoY",
                    "triggered": "YES",
                    "relevant": "YES",
                    "reasoning": "Earnings re-acceleration undermines passive-flow thesis.",
                    "severity_applied": "major",
                },
                {
                    "sector_id": "tech_ai",
                    "falsifier_id": "tech_sf_03",
                    "metric_value_found": "6.2x",
                    "triggered": "YES",
                    "relevant": "NO",
                    "reasoning": "Does not attack rotation mechanism.",
                    "severity_applied": "NONE",
                },
            ],
            "attack_vector_findings": [
                {
                    "vector_id": "tech_av_01",
                    "finding": "EPS growth exceeds revenue growth by 8%.",
                    "impact": "Below material concern threshold.",
                },
            ],
        },
    ]


# ---------------------------------------------------------------------------
# parse_sector_falsifier_audits — well-formed text block
# ---------------------------------------------------------------------------

def test_parse_text_well_formed_three_falsifiers():
    """Parse a well-formed audit block with 3 falsifiers:
    one triggered+relevant, one triggered+not-relevant, one not-triggered."""
    results = parse_sector_falsifier_audits(raw=WELL_FORMED_TEXT_BLOCK)

    assert len(results) == 3

    # All entries belong to the same hypothesis
    assert all(r["hypothesis_id"] == "H-20260329-01" for r in results)
    assert all(r["sector_id"] == "tech_ai" for r in results)

    by_id = {r["falsifier_id"]: r for r in results}

    # tech_sf_01: NOT triggered
    sf01 = by_id["tech_sf_01"]
    assert sf01["triggered"] == "NO"
    assert sf01["relevant"] == "N/A"
    assert sf01["severity_applied"] == "NONE"
    assert "1.2x" in sf01["metric_value_found"]

    # tech_sf_02: triggered AND relevant
    sf02 = by_id["tech_sf_02"]
    assert sf02["triggered"] == "YES"
    assert sf02["relevant"] == "YES"
    assert sf02["severity_applied"] == "major"
    assert "28%" in sf02["metric_value_found"]

    # tech_sf_03: triggered but NOT relevant
    sf03 = by_id["tech_sf_03"]
    assert sf03["triggered"] == "YES"
    assert sf03["relevant"] == "NO"
    assert sf03["severity_applied"] == "NONE"
    assert "6.2x" in sf03["metric_value_found"]


# ---------------------------------------------------------------------------
# parse_sector_falsifier_audits — no audit blocks
# ---------------------------------------------------------------------------

def test_parse_empty_string_returns_empty():
    """No audit blocks in the response — return empty list, don't crash."""
    assert parse_sector_falsifier_audits(raw="") == []


def test_parse_no_audit_markers_returns_empty():
    """Response has content but no SECTOR FALSIFIER AUDIT markers."""
    response = (
        "All hypotheses evaluated. No sector appendices were applicable. "
        "Status determinations are based on theory-level falsifiers only."
    )
    assert parse_sector_falsifier_audits(raw=response) == []


def test_parse_none_items_returns_empty():
    """Both paths produce nothing when given no input."""
    assert parse_sector_falsifier_audits(raw="", elimination_items=None) == []


# ---------------------------------------------------------------------------
# parse_sector_falsifier_audits — malformed entry recovery
# ---------------------------------------------------------------------------

def test_parse_malformed_entry_skips_bad_keeps_good():
    """A malformed entry (financials_sf_02) is skipped; the two good entries
    (financials_sf_01, financials_sf_03) are still extracted."""
    results = parse_sector_falsifier_audits(raw=MALFORMED_TEXT_BLOCK)

    # financials_sf_02 is garbled — should be skipped
    ids = [r["falsifier_id"] for r in results]
    assert "financials_sf_01" in ids
    assert "financials_sf_03" in ids
    assert "financials_sf_02" not in ids
    assert len(results) == 2


# ---------------------------------------------------------------------------
# parse_sector_falsifier_audits — multiple hypotheses
# ---------------------------------------------------------------------------

def test_parse_multiple_hypothesis_blocks():
    """Audit blocks for two different hypotheses are parsed with correct
    hypothesis_id assignment."""
    results = parse_sector_falsifier_audits(raw=MULTI_HYPOTHESIS_TEXT)

    h01 = [r for r in results if r["hypothesis_id"] == "H-20260329-01"]
    h03 = [r for r in results if r["hypothesis_id"] == "H-20260329-03"]

    assert len(h01) == 1
    assert h01[0]["falsifier_id"] == "tech_sf_01"
    assert h01[0]["sector_id"] == "tech_ai"

    assert len(h03) == 2
    ids_h03 = {r["falsifier_id"] for r in h03}
    assert ids_h03 == {"energy_sf_01", "energy_sf_05"}
    assert all(r["sector_id"] == "energy" for r in h03)


# ---------------------------------------------------------------------------
# parse_sector_falsifier_audits — JSON path
# ---------------------------------------------------------------------------

def test_parse_json_items_extracts_audit():
    """Extract sector audit entries from JSON elimination items."""
    items = _json_items_with_audit()
    results = parse_sector_falsifier_audits(elimination_items=items)

    assert len(results) == 2
    by_id = {r["falsifier_id"]: r for r in results}

    assert by_id["tech_sf_02"]["triggered"] == "YES"
    assert by_id["tech_sf_02"]["relevant"] == "YES"
    assert by_id["tech_sf_02"]["severity_applied"] == "major"

    assert by_id["tech_sf_03"]["triggered"] == "YES"
    assert by_id["tech_sf_03"]["relevant"] == "NO"
    assert by_id["tech_sf_03"]["severity_applied"] == "NONE"


def test_parse_json_items_without_audit_field():
    """Elimination items with no sector_falsifier_audit field return empty."""
    items = [{"hypothesis_id": "H-01", "status": "SURVIVED"}]
    assert parse_sector_falsifier_audits(elimination_items=items) == []


def test_parse_json_skips_malformed_entries():
    """JSON entries missing required fields (falsifier_id, triggered) are skipped."""
    items = [
        {
            "hypothesis_id": "H-01",
            "sector_falsifier_audit": [
                {"falsifier_id": "tech_sf_01", "triggered": "YES", "relevant": "NO",
                 "metric_value_found": "1.8x", "reasoning": "ok", "severity_applied": "NONE"},
                {"falsifier_id": "", "triggered": "YES"},  # missing falsifier_id
                {"falsifier_id": "tech_sf_03", "triggered": "MAYBE"},  # invalid triggered
                {"falsifier_id": "tech_sf_04"},  # missing triggered entirely
            ],
        },
    ]
    results = parse_sector_falsifier_audits(elimination_items=items)
    assert len(results) == 1
    assert results[0]["falsifier_id"] == "tech_sf_01"


# ---------------------------------------------------------------------------
# parse_sector_falsifier_audits — JSON + text merge
# ---------------------------------------------------------------------------

def test_json_and_text_merge_without_duplicates():
    """When both JSON and text provide data, JSON takes precedence for
    overlapping (hypothesis_id, falsifier_id) pairs."""
    items = [
        {
            "hypothesis_id": "H-20260329-01",
            "sector_falsifier_audit": [
                {
                    "sector_id": "tech_ai",
                    "falsifier_id": "tech_sf_02",
                    "metric_value_found": "28% (JSON)",
                    "triggered": "YES",
                    "relevant": "YES",
                    "reasoning": "From JSON.",
                    "severity_applied": "major",
                },
            ],
        },
    ]
    results = parse_sector_falsifier_audits(
        raw=WELL_FORMED_TEXT_BLOCK,
        elimination_items=items,
    )

    # tech_sf_02 should come from JSON (has "JSON" in metric), not text
    sf02 = [r for r in results if r["falsifier_id"] == "tech_sf_02"]
    assert len(sf02) == 1
    assert "JSON" in sf02[0]["metric_value_found"]

    # tech_sf_01 and tech_sf_03 should come from text (not in JSON)
    ids = {r["falsifier_id"] for r in results}
    assert ids == {"tech_sf_01", "tech_sf_02", "tech_sf_03"}


# ---------------------------------------------------------------------------
# parse_attack_vector_findings — text path
# ---------------------------------------------------------------------------

def test_parse_attack_vectors_from_text():
    """Extract attack vector findings from text blocks."""
    results = parse_attack_vector_findings(raw=WELL_FORMED_TEXT_BLOCK)

    assert len(results) == 2
    assert all(r["hypothesis_id"] == "H-20260329-01" for r in results)

    by_id = {r["vector_id"]: r for r in results}
    assert "tech_av_01" in by_id
    assert "tech_av_03" in by_id

    # Check content extraction
    assert "buyback yield" in by_id["tech_av_01"]["finding"].lower() or \
           "EPS" in by_id["tech_av_01"]["finding"]
    assert by_id["tech_av_03"]["impact"] != ""


def test_parse_attack_vectors_empty_when_none():
    """No ATTACK VECTOR FINDINGS blocks — return empty list."""
    assert parse_attack_vector_findings(raw="No vectors here.") == []
    assert parse_attack_vector_findings(raw="", elimination_items=None) == []


# ---------------------------------------------------------------------------
# parse_attack_vector_findings — JSON path
# ---------------------------------------------------------------------------

def test_parse_attack_vectors_from_json():
    """Extract attack vector findings from JSON elimination items."""
    items = _json_items_with_audit()
    results = parse_attack_vector_findings(elimination_items=items)

    assert len(results) == 1
    assert results[0]["vector_id"] == "tech_av_01"
    assert results[0]["hypothesis_id"] == "H-20260329-01"
    assert "EPS" in results[0]["finding"]


# ---------------------------------------------------------------------------
# Edge cases — severity normalization
# ---------------------------------------------------------------------------

def test_severity_normalization():
    """Various severity strings are normalized correctly."""
    from backend.engine.output_parser import _normalize_severity_applied

    assert _normalize_severity_applied("major") == "major"
    assert _normalize_severity_applied("MAJOR") == "major"
    assert _normalize_severity_applied("Major.") == "major"
    assert _normalize_severity_applied("medium,") == "medium"
    assert _normalize_severity_applied("minor") == "minor"
    assert _normalize_severity_applied("NONE") == "NONE"
    assert _normalize_severity_applied("none") == "NONE"
    assert _normalize_severity_applied(None) == "NONE"
    assert _normalize_severity_applied("") == "NONE"
    assert _normalize_severity_applied("unknown") == "NONE"


# ---------------------------------------------------------------------------
# Edge case — reasoning spans multiple lines
# ---------------------------------------------------------------------------

def test_multiline_reasoning_extracted():
    """Reasoning that wraps across lines is captured in full."""
    block = """\
SECTOR FALSIFIER AUDIT: H-99
Sector: tech_ai

  [tech_sf_02]
  Metric value found: 30% YoY
  Triggered: YES
  Relevant to this hypothesis: YES
  Reasoning: Earnings re-acceleration is strong. This directly undermines
    the passive-flows thesis because fundamentals now justify the
    concentration premium.
  Severity applied: major
"""
    results = parse_sector_falsifier_audits(raw=block)
    assert len(results) == 1
    assert "passive-flows" in results[0]["reasoning"]
    assert "fundamentals" in results[0]["reasoning"]
