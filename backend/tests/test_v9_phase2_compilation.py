"""v9 Phase 2: Compilation, validation, comparison, and semantic diff tests.

Tests the Phase 2 layer:
  - Artifact compilation shape and coverage
  - Artifact file loading/parsing/serialization
  - Validator behavior on compiled artifacts
  - Parallel scoring comparison helpers
  - Semantic diff classification logic
  - Stable handling of blocked/warning indicators
  - Known mismatch inventory classification
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from backend.schemas.briefing import BriefingPacket
from backend.schemas.v9.compiled_activation import (
    ArtifactStatus,
    CompilationStatus,
    CompiledActivationArtifact,
    ExclusionPolicy,
    PhaseModel,
    ValidationStatus,
)
from backend.schemas.v9.rules import (
    CompoundRule,
    FieldComparisonRule,
    ScalarComparisonRule,
    TrendStateRule,
)
from backend.schemas.v9.units import ValueUnit

# Phase 2 modules
from backend.engine.v9.compile_all import (
    ALL_THEORY_BUILDERS,
    compile_all_theories,
)
from backend.engine.v9.compiler import (
    ARTIFACTS_DIR,
    load_all_artifacts,
    load_artifact,
    make_artifact,
    make_indicator,
    make_phase,
    save_artifact,
    scalar,
    compound_all,
    compound_any,
    field_cmp,
    trend,
    persistence,
)
from backend.engine.v9.registry_builder import build_full_registry
from backend.engine.v9.validator import ArtifactValidator
from backend.engine.v9.parallel_compare import (
    IndicatorComparison,
    ParallelComparisonEngine,
    TheoryComparison,
    run_parallel_comparison,
)
from backend.engine.v9.semantic_diff import (
    MismatchClass,
    SemanticDiffEntry,
    classify_comparison,
    generate_full_diff,
    render_diff_report,
    KNOWN_CLASSIFICATIONS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BRIEFING_PATH = Path(__file__).resolve().parents[2] / "mock_data" / "briefing_packet.json"


@pytest.fixture(scope="module")
def briefing():
    with open(BRIEFING_PATH) as f:
        return BriefingPacket(**json.load(f))


@pytest.fixture(scope="module")
def registry():
    return build_full_registry()


@pytest.fixture(scope="module")
def all_artifacts():
    return compile_all_theories()


@pytest.fixture(scope="module")
def validator(registry):
    return ArtifactValidator(registry)


# ---------------------------------------------------------------------------
# 1. Compilation shape tests
# ---------------------------------------------------------------------------

class TestCompilationShape:
    """Verify all 8 theories compile and have the right shape."""

    def test_all_8_theories_compiled(self, all_artifacts):
        assert len(all_artifacts) == 8
        expected = {
            "valuation_mean_reversion", "debt_cycle_short", "debt_cycle_long",
            "structural_fragility", "fiscal_dominance_arithmetic",
            "fiscal_dominance_liquidity", "capital_flows", "monetary_architecture",
        }
        assert set(all_artifacts.keys()) == expected

    def test_total_indicators_is_68(self, all_artifacts):
        total = sum(a.total_indicators for a in all_artifacts.values())
        assert total == 68

    def test_artifact_status_is_draft(self, all_artifacts):
        for art in all_artifacts.values():
            assert art.artifact_status == ArtifactStatus.DRAFT

    def test_schema_version_is_1(self, all_artifacts):
        for art in all_artifacts.values():
            assert art.schema_version == 1

    def test_two_phase_theories_correct(self, all_artifacts):
        two_phase = {"debt_cycle_short", "structural_fragility", "capital_flows"}
        single_phase = set(all_artifacts.keys()) - two_phase
        for tid in two_phase:
            assert all_artifacts[tid].phase_model == PhaseModel.TWO_PHASE
            assert len(all_artifacts[tid].phases) == 2
        for tid in single_phase:
            assert all_artifacts[tid].phase_model == PhaseModel.SINGLE_PHASE
            assert len(all_artifacts[tid].phases) == 1

    @pytest.mark.parametrize("theory_id,expected_count", [
        ("valuation_mean_reversion", 7),
        ("debt_cycle_short", 15),
        ("debt_cycle_long", 6),
        ("structural_fragility", 12),
        ("fiscal_dominance_arithmetic", 6),
        ("fiscal_dominance_liquidity", 7),
        ("capital_flows", 10),
        ("monetary_architecture", 5),
    ])
    def test_indicator_counts(self, all_artifacts, theory_id, expected_count):
        art = all_artifacts[theory_id]
        assert art.total_indicators == expected_count

    def test_all_indicators_have_weights(self, all_artifacts):
        for art in all_artifacts.values():
            for phase in art.phases:
                for ind in phase.indicators:
                    assert 0 < ind.weight <= 1.0, (
                        f"{art.source.theory_id}/{ind.indicator_id}: weight={ind.weight}"
                    )

    def test_all_indicators_have_primary_field(self, all_artifacts):
        for art in all_artifacts.values():
            for phase in art.phases:
                for ind in phase.indicators:
                    assert ind.primary_field, (
                        f"{art.source.theory_id}/{ind.indicator_id}: no primary_field"
                    )

    def test_clean_warn_blocked_counts_consistent(self, all_artifacts):
        for art in all_artifacts.values():
            assert art.clean_count + art.warning_count + art.blocked_count == art.total_indicators


# ---------------------------------------------------------------------------
# 2. Artifact serialization tests
# ---------------------------------------------------------------------------

class TestArtifactSerialization:
    """Test artifact save/load roundtrip."""

    def test_save_and_load_roundtrip(self, all_artifacts):
        art = all_artifacts["valuation_mean_reversion"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.compiled.json"
            save_artifact(art, path)
            loaded = load_artifact("test", path)
            assert loaded.source.theory_id == art.source.theory_id
            assert loaded.total_indicators == art.total_indicators
            assert len(loaded.phases) == len(art.phases)

    def test_artifact_json_is_valid(self, all_artifacts):
        art = all_artifacts["fiscal_dominance_arithmetic"]
        json_str = art.model_dump_json()
        data = json.loads(json_str)
        assert data["source"]["theory_id"] == "fiscal_dominance_arithmetic"
        assert data["phase_model"] == "single_phase"

    def test_load_all_from_disk(self):
        """Load artifacts from the actual artifacts/v9/ directory."""
        if not ARTIFACTS_DIR.exists():
            pytest.skip("Artifacts not saved to disk")
        loaded = load_all_artifacts()
        assert len(loaded) == 8


# ---------------------------------------------------------------------------
# 3. Validator behavior tests
# ---------------------------------------------------------------------------

class TestValidation:
    """Test Phase 1 validator on Phase 2 artifacts."""

    def test_clean_theories_pass_validation(self, all_artifacts, validator):
        clean_theories = [
            "debt_cycle_long", "fiscal_dominance_arithmetic",
            "fiscal_dominance_liquidity", "capital_flows",
        ]
        for tid in clean_theories:
            report = validator.validate(all_artifacts[tid])
            assert report.passed, f"{tid}: {report.summary()}"

    def test_blocked_indicators_cause_validation_errors(self, all_artifacts, validator):
        # debt_cycle_short has UNRESOLVED:loan_growth_yoy
        report = validator.validate(all_artifacts["debt_cycle_short"])
        assert not report.passed
        assert any("UNRESOLVED" in f.message for f in report.errors())

    def test_monetary_architecture_has_unresolved_errors(self, all_artifacts, validator):
        report = validator.validate(all_artifacts["monetary_architecture"])
        assert not report.passed
        unresolved = [f for f in report.errors() if "UNRESOLVED" in f.message]
        assert len(unresolved) >= 2  # CCBS + energy settlement

    def test_validation_errors_are_only_from_blocked_or_partial_indicators(self, all_artifacts, validator):
        """Validation errors should come from blocked or partially-blocked indicators."""
        for tid, art in all_artifacts.items():
            report = validator.validate(art)
            # Both BLOCKED indicators and WARNING indicators with UNRESOLVED sub-fields
            # can cause validation errors
            allowed_ids = {
                ind.indicator_id
                for p in art.phases for ind in p.indicators
                if ind.compilation_status == CompilationStatus.BLOCKED
                or "UNRESOLVED" in str(ind.rule.model_dump_json())
            }
            for finding in report.errors():
                if finding.indicator_id:
                    assert finding.indicator_id in allowed_ids, (
                        f"{tid}/{finding.indicator_id}: unexpected validation error: "
                        f"{finding.message}"
                    )


# ---------------------------------------------------------------------------
# 4. Parallel comparison tests
# ---------------------------------------------------------------------------

class TestParallelComparison:
    """Test the parallel comparison engine."""

    def test_comparison_covers_all_theories(self, all_artifacts, briefing):
        from backend.engine.theory_loader import load_all_theory_packages
        from backend.engine.activation import score_all_packages
        packages = load_all_theory_packages()
        legacy = {r.theory_id: r for r in score_all_packages(packages, briefing)}
        comparisons = run_parallel_comparison(all_artifacts, briefing, legacy)
        assert len(comparisons) == 8

    def test_all_mismatches_are_known_justified(self, all_artifacts, briefing):
        """Every indicator-level mismatch must be in the known-justified inventory.

        v9 Phase 3: score_all_packages() now uses compiled path for 3 approved
        theories (valuation_mean_reversion, debt_cycle_long, fiscal_dominance_arithmetic).
        Comparing compiled artifacts against compiled results = no mismatches for those.
        Only 1 mismatch remains: capital_flows/acc_em_3yr_underperformance (still legacy).
        """
        from backend.engine.theory_loader import load_all_theory_packages
        from backend.engine.activation import score_all_packages
        from backend.engine.v9.semantic_diff import KNOWN_CLASSIFICATIONS, MismatchClass
        packages = load_all_theory_packages()
        legacy = {r.theory_id: r for r in score_all_packages(packages, briefing)}
        comparisons = run_parallel_comparison(all_artifacts, briefing, legacy)

        mismatches = []
        for tid, tc in comparisons.items():
            for phase in tc.phases:
                for ic in phase.indicators:
                    if ic.status == "MISMATCH":
                        mismatches.append((tid, ic.indicator_id))

        # v9 Phase 4B: All 8 theories on compiled path.
        # Compiled vs compiled comparison = identity, so 0 mismatches.
        assert len(mismatches) == 0, f"Expected 0 mismatches (all compiled), got: {mismatches}"

    def test_effective_tier_matches_for_most_theories(self, all_artifacts, briefing):
        from backend.engine.theory_loader import load_all_theory_packages
        from backend.engine.activation import score_all_packages
        packages = load_all_theory_packages()
        legacy = {r.theory_id: r for r in score_all_packages(packages, briefing)}
        comparisons = run_parallel_comparison(all_artifacts, briefing, legacy)

        tier_matches = sum(1 for tc in comparisons.values() if tc.tier_match)
        # At least 5 of 8 should match (some differ due to temporal exclusions)
        assert tier_matches >= 5, (
            f"Only {tier_matches}/8 tier matches: "
            + ", ".join(f"{tid}={tc.compiled_effective_tier}vs{tc.legacy_effective_tier}"
                        for tid, tc in comparisons.items() if not tc.tier_match)
        )


# ---------------------------------------------------------------------------
# 5. Semantic diff classification tests
# ---------------------------------------------------------------------------

class TestSemanticDiff:
    """Test the semantic diff classifier."""

    def test_known_classifications_coverage(self):
        """Verify all known mismatches from spike are classified."""
        expected_keys = {
            ("valuation_mean_reversion", "profit_margins_elevated"),
            ("debt_cycle_short", "exp_initial_claims_low"),
            ("debt_cycle_short", "exp_fed_funds_below_gdp"),
            ("debt_cycle_short", "con_fed_funds_above_gdp"),
            ("debt_cycle_long", "wealth_inequality_extreme"),
            ("structural_fragility", "bld_vix_low"),
            ("structural_fragility", "res_vix_elevated"),
            ("capital_flows", "acc_em_3yr_underperformance"),
        }
        assert expected_keys.issubset(set(KNOWN_CLASSIFICATIONS.keys()))

    def test_known_classifications_are_expected_types(self):
        """All known classifications should be justified, data_infra, or coincidental."""
        valid_types = {
            MismatchClass.JUSTIFIED_IMPROVEMENT,
            MismatchClass.DATA_INFRA_LIMITATION,
            MismatchClass.COINCIDENTAL_PARITY,
        }
        for key, (cls, _expl, _ref) in KNOWN_CLASSIFICATIONS.items():
            assert cls in valid_types, f"{key}: unexpected classification {cls}"

    def test_full_diff_has_zero_human_review_items(self, all_artifacts, briefing):
        """The semantic diff should have zero items needing human review."""
        from backend.engine.theory_loader import load_all_theory_packages
        from backend.engine.activation import score_all_packages
        packages = load_all_theory_packages()
        legacy = {r.theory_id: r for r in score_all_packages(packages, briefing)}
        comparisons = run_parallel_comparison(all_artifacts, briefing, legacy)
        diff = generate_full_diff(comparisons)
        assert diff.total_needs_review == 0, (
            f"Items needing review: {diff.total_needs_review}"
        )

    def test_justified_improvements_count(self, all_artifacts, briefing):
        from backend.engine.theory_loader import load_all_theory_packages
        from backend.engine.activation import score_all_packages
        packages = load_all_theory_packages()
        legacy = {r.theory_id: r for r in score_all_packages(packages, briefing)}
        comparisons = run_parallel_comparison(all_artifacts, briefing, legacy)
        diff = generate_full_diff(comparisons)
        # Should have several justified improvements from known mismatch inventory
        assert diff.total_justified >= 5

    def test_render_diff_produces_markdown(self, all_artifacts, briefing):
        from backend.engine.theory_loader import load_all_theory_packages
        from backend.engine.activation import score_all_packages
        packages = load_all_theory_packages()
        legacy = {r.theory_id: r for r in score_all_packages(packages, briefing)}
        comparisons = run_parallel_comparison(all_artifacts, briefing, legacy)
        diff = generate_full_diff(comparisons)
        report = render_diff_report(diff)
        assert "# V9 Phase 2: Semantic Diff Report" in report
        assert "Justified Improvements" in report


# ---------------------------------------------------------------------------
# 6. Rule builder tests
# ---------------------------------------------------------------------------

class TestRuleBuilders:
    """Test the Phase 0 schema rule builder helpers."""

    def test_scalar_produces_correct_type(self):
        rule = scalar("growth.ism_proxy", "gt", 50.0)
        assert rule.rule_type == "scalar_comparison"
        assert rule.field.field_id == "growth.ism_proxy"
        assert rule.threshold.value == 50.0

    def test_compound_all_produces_correct_type(self):
        rule = compound_all(
            scalar("credit.hy_spread", "lt", 450.0),
            trend("credit.hy_spread", "stable"),
        )
        assert rule.rule_type == "compound"
        assert rule.operator.value == "all"
        assert len(rule.clauses) == 2

    def test_compound_any_produces_correct_type(self):
        rule = compound_any(
            scalar("sp500_net_margin", "gt", 12.0),
            scalar("corporate_profits_gdp_ratio", "gt", 10.0),
        )
        assert rule.rule_type == "compound"
        assert rule.operator.value == "any"

    def test_field_comparison_with_derived(self):
        rule = field_cmp("rates.fed_funds", "lt", derived_fn="nominal_gdp_growth")
        assert rule.rule_type == "field_comparison"
        assert rule.right.operand_type == "derived"
        assert rule.right.function_name == "nominal_gdp_growth"

    def test_persistence_wraps_inner_rule(self):
        inner = scalar("cb_gold_purchases", "gt", 800.0)
        rule = persistence(inner, n=2, k=2, window_val=2)
        assert rule.rule_type == "persistence"
        assert rule.n == 2
        assert rule.condition.rule_type == "scalar_comparison"


# ---------------------------------------------------------------------------
# 7. Blocked / warning indicator handling
# ---------------------------------------------------------------------------

class TestBlockedIndicators:
    """Test stable handling of blocked and warning indicators."""

    def test_blocked_indicators_have_unresolved_fields(self, all_artifacts):
        for art in all_artifacts.values():
            for phase in art.phases:
                for ind in phase.indicators:
                    if ind.compilation_status == CompilationStatus.BLOCKED:
                        assert "UNRESOLVED" in ind.primary_field, (
                            f"{art.source.theory_id}/{ind.indicator_id}: "
                            f"blocked but no UNRESOLVED in primary_field"
                        )

    def test_warning_indicators_have_ambiguities(self, all_artifacts):
        for art in all_artifacts.values():
            for phase in art.phases:
                for ind in phase.indicators:
                    if ind.compilation_status == CompilationStatus.WARNING:
                        has_ambiguity = len(ind.ambiguities) > 0
                        has_warnings = len(ind.compiler_warnings) > 0
                        has_ts = ind.requires_time_series
                        assert has_ambiguity or has_warnings or has_ts, (
                            f"{art.source.theory_id}/{ind.indicator_id}: "
                            f"warning status but no ambiguities/warnings/time_series flag"
                        )

    def test_blocked_count_matches_actual(self, all_artifacts):
        expected_blocked = {
            "debt_cycle_short": 1,    # loan_growth_yoy
            "structural_fragility": 1, # capex_revenue_mismatch
            "monetary_architecture": 1, # ccbs_stress
        }
        for tid, expected in expected_blocked.items():
            assert all_artifacts[tid].blocked_count == expected


# ---------------------------------------------------------------------------
# 8. Specific known mismatch regression tests
# ---------------------------------------------------------------------------

class TestKnownMismatches:
    """Regression tests for the specific known mismatch inventory."""

    def test_eem_spy_3y_relative_sign_is_correct(self, all_artifacts):
        """The eem_spy_3y_relative compiled rule must use lt -30, not lt 30."""
        art = all_artifacts["capital_flows"]
        accum = art.phases[0]  # accumulation
        em_ind = [i for i in accum.indicators if i.indicator_id == "acc_em_3yr_underperformance"]
        assert len(em_ind) == 1
        rule = em_ind[0].rule
        assert rule.rule_type == "scalar_comparison"
        assert rule.threshold.value == -30.0  # negative, not positive
        assert rule.field.field_id == "eem_spy_3y_relative"

    def test_initial_claims_unit_normalization(self, all_artifacts):
        """Initial claims threshold must be in THOUSANDS while field is COUNT."""
        art = all_artifacts["debt_cycle_short"]
        exp = art.phases[0]  # expansion
        claims_ind = [i for i in exp.indicators if i.indicator_id == "exp_initial_claims_low"]
        assert len(claims_ind) == 1
        rule = claims_ind[0].rule
        assert rule.rule_type == "scalar_comparison"
        assert rule.threshold.unit == ValueUnit.THOUSANDS
        assert claims_ind[0].field_unit == ValueUnit.COUNT

    def test_vix_field_resolution_fixed(self, all_artifacts):
        """Phase 2 must use ^VIX, not vix_vs_realized for VIX indicators."""
        art = all_artifacts["structural_fragility"]
        building = art.phases[0]
        vix_ind = [i for i in building.indicators if i.indicator_id == "bld_vix_low"]
        assert len(vix_ind) == 1
        assert vix_ind[0].primary_field == "^VIX"
        assert vix_ind[0].rule.field.field_id == "^VIX"

    def test_wealth_inequality_threshold_is_70(self, all_artifacts):
        """Wealth inequality must check top10 > 70%, not > 10."""
        art = all_artifacts["debt_cycle_long"]
        single = art.phases[0]
        wealth_ind = [i for i in single.indicators if i.indicator_id == "wealth_inequality_extreme"]
        assert len(wealth_ind) == 1
        rule = wealth_ind[0].rule
        assert rule.rule_type == "scalar_comparison"
        assert rule.threshold.value == 70.0

    def test_fed_funds_is_field_comparison(self, all_artifacts):
        """Fed funds vs GDP must be field_comparison, not scalar."""
        art = all_artifacts["debt_cycle_short"]
        exp = art.phases[0]
        ff_ind = [i for i in exp.indicators if i.indicator_id == "exp_fed_funds_below_gdp"]
        assert len(ff_ind) == 1
        assert ff_ind[0].rule.rule_type == "field_comparison"

    def test_profit_margins_is_or_compound(self, all_artifacts):
        """Profit margins must be compound OR, not single scalar."""
        art = all_artifacts["valuation_mean_reversion"]
        single = art.phases[0]
        pm_ind = [i for i in single.indicators if i.indicator_id == "profit_margins_elevated"]
        assert len(pm_ind) == 1
        rule = pm_ind[0].rule
        assert rule.rule_type == "compound"
        assert rule.operator.value == "any"
        assert len(rule.clauses) == 2

    def test_canonical_output_unit_is_percent(self, all_artifacts):
        """Canonical compiler output unit is PERCENT, not SHARE (Phase 1 decision)."""
        art = all_artifacts["capital_flows"]
        accum = art.phases[0]
        for ind in accum.indicators:
            if ind.field_unit == ValueUnit.SHARE:
                pytest.fail(f"{ind.indicator_id}: uses SHARE instead of PERCENT")
