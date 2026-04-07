"""Phase 0 contract tests for v9 semantic compiler.

Tests the contract package:
  1. Unit model — enums, conversions, legality checks
  2. Rule schema — instantiation, discriminated union, valid/invalid rules
  3. Compiled activation schema — artifact structure and lifecycle
  4. Field registry — lookup, comparison legality, unit compatibility
  5. Validator error taxonomy — structured errors, report behavior
  6. Series interface — primitive catalogue completeness

These tests are NEW and SEPARATE from the frozen correctness harness.
They do not modify or depend on test_activation_correctness.py.
"""
import pytest

# ---------------------------------------------------------------------------
# 1. Unit model tests
# ---------------------------------------------------------------------------

from backend.schemas.v9.units import (
    ComparisonClass,
    SemanticType,
    TimeUnit,
    TimeWindow,
    UnitValue,
    ValueUnit,
    are_comparable,
    can_convert,
    convert_value,
    get_comparison_class,
    normalize_to_common_unit,
)


class TestValueUnit:
    """ValueUnit enum coverage."""

    def test_all_expected_units_exist(self):
        """The unit enum has all the units we need for the 8 theories."""
        required = [
            "percent", "basis_points", "ratio", "count", "thousands",
            "index_points", "usd_billions", "tons", "dimensionless", "unknown",
        ]
        unit_values = {u.value for u in ValueUnit}
        for r in required:
            assert r in unit_values, f"Missing required unit: {r}"

    def test_unknown_is_sentinel(self):
        assert ValueUnit.UNKNOWN.value == "unknown"


class TestSemanticType:
    """SemanticType enum coverage."""

    def test_all_expected_types_exist(self):
        required = [
            "level", "rate", "growth_rate", "ratio", "spread", "count",
            "price", "return", "balance", "flow", "share_of_total", "index",
            "categorical_state", "duration", "volatility", "relative_performance",
        ]
        type_values = {t.value for t in SemanticType}
        for r in required:
            assert r in type_values, f"Missing required semantic type: {r}"

    def test_every_type_has_comparison_class(self):
        """Every semantic type must map to a comparison class."""
        for st in SemanticType:
            cls = get_comparison_class(st)
            assert isinstance(cls, ComparisonClass)


class TestComparisonLegality:
    """Comparison legality — the core safety contract."""

    def test_rate_vs_rate_is_legal(self):
        assert are_comparable(SemanticType.RATE, SemanticType.RATE)

    def test_rate_vs_spread_is_legal(self):
        """Rates and spreads are both RATE_LIKE."""
        assert are_comparable(SemanticType.RATE, SemanticType.SPREAD)

    def test_rate_vs_growth_rate_is_legal(self):
        assert are_comparable(SemanticType.RATE, SemanticType.GROWTH_RATE)

    def test_rate_vs_level_is_illegal(self):
        """The critical check: fed_funds (rate) vs gdp_latest (level)."""
        assert not are_comparable(SemanticType.RATE, SemanticType.LEVEL)

    def test_count_vs_price_is_illegal(self):
        assert not are_comparable(SemanticType.COUNT, SemanticType.PRICE)

    def test_ratio_vs_share_is_legal(self):
        assert are_comparable(SemanticType.RATIO, SemanticType.SHARE_OF_TOTAL)

    def test_index_vs_volatility_is_legal(self):
        """ISM and VIX are both INDEX_LIKE."""
        assert are_comparable(SemanticType.INDEX, SemanticType.VOLATILITY)

    def test_level_vs_balance_is_legal(self):
        assert are_comparable(SemanticType.LEVEL, SemanticType.BALANCE)

    def test_categorical_vs_anything_is_illegal(self):
        for st in SemanticType:
            if st == SemanticType.CATEGORICAL_STATE:
                continue
            assert not are_comparable(SemanticType.CATEGORICAL_STATE, st), \
                f"Categorical should not be comparable to {st.value}"


class TestUnitConversion:
    """Unit conversion contract."""

    def test_percent_to_basis_points(self):
        assert convert_value(3.5, ValueUnit.PERCENT, ValueUnit.BASIS_POINTS) == 350.0

    def test_basis_points_to_percent(self):
        assert convert_value(350.0, ValueUnit.BASIS_POINTS, ValueUnit.PERCENT) == 3.5

    def test_count_to_thousands(self):
        assert convert_value(202000, ValueUnit.COUNT, ValueUnit.THOUSANDS) == 202.0

    def test_thousands_to_count(self):
        assert convert_value(250.0, ValueUnit.THOUSANDS, ValueUnit.COUNT) == 250000.0

    def test_billions_to_millions(self):
        assert convert_value(1.5, ValueUnit.USD_BILLIONS, ValueUnit.USD_MILLIONS) == 1500.0

    def test_identity_conversion(self):
        assert convert_value(42.0, ValueUnit.PERCENT, ValueUnit.PERCENT) == 42.0

    def test_no_conversion_raises(self):
        """Cannot convert between incompatible units."""
        with pytest.raises(ValueError, match="No conversion"):
            convert_value(100.0, ValueUnit.PERCENT, ValueUnit.TONS)

    def test_can_convert_true(self):
        assert can_convert(ValueUnit.PERCENT, ValueUnit.BASIS_POINTS)

    def test_can_convert_false(self):
        assert not can_convert(ValueUnit.PERCENT, ValueUnit.TONS)

    def test_can_convert_identity(self):
        assert can_convert(ValueUnit.INDEX_POINTS, ValueUnit.INDEX_POINTS)


class TestNormalization:
    """normalize_to_common_unit contract."""

    def test_same_unit_passthrough(self):
        a, b, unit = normalize_to_common_unit(3.5, ValueUnit.PERCENT, 4.0, ValueUnit.PERCENT)
        assert a == 3.5
        assert b == 4.0
        assert unit == ValueUnit.PERCENT

    def test_normalize_bp_to_percent(self):
        a, b, unit = normalize_to_common_unit(3.5, ValueUnit.PERCENT, 450.0, ValueUnit.BASIS_POINTS)
        assert a == 3.5
        assert b == 4.5
        assert unit == ValueUnit.PERCENT

    def test_normalize_count_to_thousands(self):
        """The initial claims bug: 202000 (count) vs 250 (thousands)."""
        a, b, unit = normalize_to_common_unit(
            202000, ValueUnit.COUNT, 250.0, ValueUnit.THOUSANDS,
        )
        # Should normalize thousands to count
        assert unit == ValueUnit.COUNT
        assert a == 202000
        assert b == 250000.0

    def test_normalize_incompatible_raises(self):
        with pytest.raises(ValueError, match="Cannot normalize"):
            normalize_to_common_unit(3.5, ValueUnit.PERCENT, 100.0, ValueUnit.TONS)


class TestUnitValue:
    """UnitValue model."""

    def test_construction(self):
        uv = UnitValue(value=3.5, unit=ValueUnit.PERCENT)
        assert uv.value == 3.5
        assert uv.unit == ValueUnit.PERCENT

    def test_convert_to(self):
        uv = UnitValue(value=3.5, unit=ValueUnit.PERCENT)
        converted = uv.convert_to(ValueUnit.BASIS_POINTS)
        assert converted.value == 350.0
        assert converted.unit == ValueUnit.BASIS_POINTS


class TestTimeWindow:
    def test_construction(self):
        tw = TimeWindow(value=3, unit=TimeUnit.MONTHS)
        assert tw.value == 3
        assert tw.unit == TimeUnit.MONTHS


# ---------------------------------------------------------------------------
# 2. Rule schema tests
# ---------------------------------------------------------------------------

from backend.schemas.v9.rules import (
    Comparator,
    CompoundOperator,
    CompoundRule,
    DeltaChangeRule,
    DeltaMode,
    DerivedOperand,
    ExtremeType,
    FieldComparisonRule,
    FieldOperand,
    HistoricalExtremeRule,
    LiteralOperand,
    NamedPatternRule,
    PersistenceMode,
    PersistenceRule,
    Rule,
    ScalarComparisonRule,
    TrendDirection,
    TrendStateRule,
    REGISTERED_NAMED_PATTERNS,
)

from pydantic import TypeAdapter

RuleAdapter = TypeAdapter(Rule)


class TestScalarComparisonRule:
    def test_basic_construction(self):
        rule = ScalarComparisonRule(
            field=FieldOperand(field_id="shiller_cape", unit=ValueUnit.RATIO, semantic_type=SemanticType.RATIO),
            comparator=Comparator.GT,
            threshold=LiteralOperand(value=30.0, unit=ValueUnit.RATIO),
        )
        assert rule.rule_type == "scalar_comparison"
        assert rule.field.field_id == "shiller_cape"
        assert rule.threshold.value == 30.0

    def test_serialization_roundtrip(self):
        rule = ScalarComparisonRule(
            field=FieldOperand(field_id="growth.ism_proxy", unit=ValueUnit.INDEX_POINTS),
            comparator=Comparator.GT,
            threshold=LiteralOperand(value=50.0, unit=ValueUnit.INDEX_POINTS),
        )
        data = rule.model_dump()
        assert data["rule_type"] == "scalar_comparison"
        restored = RuleAdapter.validate_python(data)
        assert isinstance(restored, ScalarComparisonRule)
        assert restored.field.field_id == "growth.ism_proxy"


class TestFieldComparisonRule:
    def test_fed_funds_vs_gdp_growth(self):
        """The classic v9 motivation: field-to-field comparison."""
        rule = FieldComparisonRule(
            left=FieldOperand(field_id="rates.fed_funds", unit=ValueUnit.PERCENT, semantic_type=SemanticType.RATE),
            comparator=Comparator.LT,
            right=DerivedOperand(
                function_name="nominal_gdp_growth",
                arguments=["growth.gdp_latest"],
                unit=ValueUnit.PERCENT,
                semantic_type=SemanticType.GROWTH_RATE,
            ),
        )
        assert rule.rule_type == "field_comparison"
        assert isinstance(rule.right, DerivedOperand)

    def test_with_offset(self):
        rule = FieldComparisonRule(
            left=FieldOperand(field_id="rates.fed_funds", unit=ValueUnit.PERCENT),
            comparator=Comparator.GT,
            right=FieldOperand(field_id="growth.real_gdp", unit=ValueUnit.PERCENT),
            offset=LiteralOperand(value=1.0, unit=ValueUnit.PERCENT),
        )
        assert rule.offset.value == 1.0


class TestCompoundRule:
    def test_and_compound(self):
        """HY spread < 450bp AND not widening for 3 months."""
        rule = CompoundRule(
            operator=CompoundOperator.ALL,
            clauses=[
                ScalarComparisonRule(
                    field=FieldOperand(field_id="credit.hy_spread", unit=ValueUnit.BASIS_POINTS),
                    comparator=Comparator.LT,
                    threshold=LiteralOperand(value=450.0, unit=ValueUnit.BASIS_POINTS),
                ),
                TrendStateRule(
                    field=FieldOperand(field_id="credit.hy_spread", unit=ValueUnit.BASIS_POINTS),
                    direction=TrendDirection.STABLE,
                    window=TimeWindow(value=3, unit=TimeUnit.MONTHS),
                ),
            ],
        )
        assert rule.rule_type == "compound"
        assert len(rule.clauses) == 2

    def test_or_compound(self):
        """Profit margins > 12% OR corporate profits/GDP > 10%."""
        rule = CompoundRule(
            operator=CompoundOperator.ANY,
            clauses=[
                ScalarComparisonRule(
                    field=FieldOperand(field_id="sp500_net_margin", unit=ValueUnit.PERCENT),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=12.0, unit=ValueUnit.PERCENT),
                ),
                ScalarComparisonRule(
                    field=FieldOperand(field_id="corporate_profits_gdp_ratio", unit=ValueUnit.PERCENT),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=10.0, unit=ValueUnit.PERCENT),
                ),
            ],
        )
        assert rule.operator == CompoundOperator.ANY

    def test_nested_compound_serialization(self):
        """Compound rules can nest (3-level nesting from spike)."""
        inner = CompoundRule(
            operator=CompoundOperator.ALL,
            clauses=[
                ScalarComparisonRule(
                    field=FieldOperand(field_id="credit.hy_spread", unit=ValueUnit.BASIS_POINTS),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=500.0, unit=ValueUnit.BASIS_POINTS),
                ),
                TrendStateRule(
                    field=FieldOperand(field_id="credit.hy_spread", unit=ValueUnit.BASIS_POINTS),
                    direction=TrendDirection.RISING,
                    window=TimeWindow(value=2, unit=TimeUnit.MONTHS),
                ),
            ],
        )
        outer = CompoundRule(
            operator=CompoundOperator.ANY,
            clauses=[
                inner,
                ScalarComparisonRule(
                    field=FieldOperand(field_id="credit.hy_spread", unit=ValueUnit.BASIS_POINTS),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=600.0, unit=ValueUnit.BASIS_POINTS),
                ),
            ],
        )
        data = outer.model_dump()
        restored = RuleAdapter.validate_python(data)
        assert isinstance(restored, CompoundRule)
        assert len(restored.clauses) == 2


class TestPersistenceRule:
    def test_n_of_last_k(self):
        """Net liquidity positive for 2 of last 3 months."""
        rule = PersistenceRule(
            condition=ScalarComparisonRule(
                field=FieldOperand(field_id="net_liquidity", unit=ValueUnit.USD_BILLIONS),
                comparator=Comparator.GT,
                threshold=LiteralOperand(value=0.0, unit=ValueUnit.USD_BILLIONS),
            ),
            mode=PersistenceMode.N_OF_LAST_K,
            n=2,
            k=3,
            window=TimeWindow(value=3, unit=TimeUnit.MONTHS),
        )
        assert rule.rule_type == "persistence"
        assert rule.n == 2
        assert rule.k == 3

    def test_consecutive(self):
        """Fed funds above 4% for 12 consecutive months."""
        rule = PersistenceRule(
            condition=ScalarComparisonRule(
                field=FieldOperand(field_id="rates.fed_funds", unit=ValueUnit.PERCENT),
                comparator=Comparator.GT,
                threshold=LiteralOperand(value=4.0, unit=ValueUnit.PERCENT),
            ),
            mode=PersistenceMode.CONSECUTIVE,
            n=12,
            window=TimeWindow(value=12, unit=TimeUnit.MONTHS),
        )
        assert rule.mode == PersistenceMode.CONSECUTIVE


class TestTrendStateRule:
    def test_falling_trend(self):
        rule = TrendStateRule(
            field=FieldOperand(field_id="growth.ism_proxy", unit=ValueUnit.INDEX_POINTS),
            direction=TrendDirection.FALLING,
            window=TimeWindow(value=3, unit=TimeUnit.MONTHS),
        )
        assert rule.rule_type == "trend_state"
        assert rule.direction == TrendDirection.FALLING


class TestHistoricalExtremeRule:
    def test_above_2year_high(self):
        rule = HistoricalExtremeRule(
            field=FieldOperand(field_id="qqq_iwm_ratio", unit=ValueUnit.RATIO),
            extreme=ExtremeType.HIGH,
            lookback=TimeWindow(value=24, unit=TimeUnit.MONTHS),
            comparator=Comparator.GT,
        )
        assert rule.rule_type == "historical_extreme"

    def test_with_margin(self):
        """Within 10% of record high."""
        rule = HistoricalExtremeRule(
            field=FieldOperand(field_id="finra_margin_debt", unit=ValueUnit.USD_BILLIONS),
            extreme=ExtremeType.HIGH,
            lookback=TimeWindow(value=120, unit=TimeUnit.MONTHS),
            comparator=Comparator.GTE,
            margin=LiteralOperand(value=0.10, unit=ValueUnit.RATIO),
        )
        assert rule.margin.value == 0.10


class TestNamedPatternRule:
    def test_sahm_rule(self):
        rule = NamedPatternRule(
            name="sahm_rule",
            params={
                "field": "growth.unemployment",
                "ma_window": 3,
                "lookback": 12,
                "threshold": 0.50,
            },
            field_dependencies=["growth.unemployment"],
        )
        assert rule.rule_type == "named_pattern"
        assert rule.name in REGISTERED_NAMED_PATTERNS

    def test_unregistered_pattern(self):
        """Can construct but won't pass validation."""
        rule = NamedPatternRule(
            name="totally_fake_pattern",
            params={},
        )
        assert rule.name not in REGISTERED_NAMED_PATTERNS


class TestDeltaChangeRule:
    def test_tga_declining(self):
        """TGA declining by $100B+ over 60 days."""
        rule = DeltaChangeRule(
            field=FieldOperand(field_id="liquidity.tga", unit=ValueUnit.USD_BILLIONS),
            direction=TrendDirection.FALLING,
            magnitude=LiteralOperand(value=100.0, unit=ValueUnit.USD_BILLIONS),
            mode=DeltaMode.ABSOLUTE,
            window=TimeWindow(value=60, unit=TimeUnit.DAYS),
        )
        assert rule.rule_type == "delta_change"
        assert rule.magnitude.value == 100.0


class TestRuleDiscriminatedUnion:
    """The discriminated union pattern must work for serialization/deserialization."""

    def test_roundtrip_all_rule_types(self):
        """Every rule type must survive JSON roundtrip via the Union."""
        rules = [
            ScalarComparisonRule(
                field=FieldOperand(field_id="x"),
                comparator=Comparator.GT,
                threshold=LiteralOperand(value=1.0),
            ),
            FieldComparisonRule(
                left=FieldOperand(field_id="a"),
                comparator=Comparator.LT,
                right=FieldOperand(field_id="b"),
            ),
            CompoundRule(
                operator=CompoundOperator.ALL,
                clauses=[
                    ScalarComparisonRule(
                        field=FieldOperand(field_id="x"),
                        comparator=Comparator.GT,
                        threshold=LiteralOperand(value=1.0),
                    ),
                ],
            ),
            PersistenceRule(
                condition=ScalarComparisonRule(
                    field=FieldOperand(field_id="x"),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=0.0),
                ),
                mode=PersistenceMode.N_OF_LAST_K,
                n=2, k=3,
                window=TimeWindow(value=3, unit=TimeUnit.MONTHS),
            ),
            TrendStateRule(
                field=FieldOperand(field_id="x"),
                direction=TrendDirection.RISING,
                window=TimeWindow(value=3, unit=TimeUnit.MONTHS),
            ),
            HistoricalExtremeRule(
                field=FieldOperand(field_id="x"),
                extreme=ExtremeType.HIGH,
                lookback=TimeWindow(value=24, unit=TimeUnit.MONTHS),
                comparator=Comparator.GT,
            ),
            NamedPatternRule(name="sahm_rule", params={"threshold": 0.5}),
            DeltaChangeRule(
                field=FieldOperand(field_id="x"),
                direction=TrendDirection.FALLING,
                magnitude=LiteralOperand(value=10.0),
                mode=DeltaMode.ABSOLUTE,
                window=TimeWindow(value=30, unit=TimeUnit.DAYS),
            ),
        ]

        for original in rules:
            data = original.model_dump()
            restored = RuleAdapter.validate_python(data)
            assert type(restored) is type(original), \
                f"Roundtrip failed for {original.rule_type}: got {type(restored).__name__}"

    def test_invalid_rule_type_rejected(self):
        """A rule_type not in the union is rejected."""
        with pytest.raises(Exception):
            RuleAdapter.validate_python({"rule_type": "nonexistent", "foo": "bar"})


# ---------------------------------------------------------------------------
# 3. Compiled activation schema tests
# ---------------------------------------------------------------------------

from backend.schemas.v9.compiled_activation import (
    AmbiguityLevel,
    AmbiguityRecord,
    ArtifactStatus,
    CompilationStatus,
    CompiledActivationArtifact,
    CompiledIndicator,
    CompiledPhase,
    CompilerMetadata,
    ExclusionPolicy,
    PhaseModel,
    SourcePackageRef,
    SourceProvenance,
    ValidationStatus,
    ValidationSummary,
)


class TestCompiledIndicator:
    def test_minimal_construction(self):
        ind = CompiledIndicator(
            indicator_id="expansion_ism_above_contraction",
            display_name="ISM proxy above contraction",
            source_text="ISM proxy above contraction | growth.ism_proxy | Above 50",
            rule=ScalarComparisonRule(
                field=FieldOperand(field_id="growth.ism_proxy", unit=ValueUnit.INDEX_POINTS),
                comparator=Comparator.GT,
                threshold=LiteralOperand(value=50.0, unit=ValueUnit.INDEX_POINTS),
            ),
            primary_field="growth.ism_proxy",
            weight=0.15,
        )
        assert ind.indicator_id == "expansion_ism_above_contraction"
        assert ind.compilation_status == CompilationStatus.CLEAN
        assert not ind.requires_time_series

    def test_with_ambiguity(self):
        ind = CompiledIndicator(
            indicator_id="test",
            display_name="Test",
            source_text="some ambiguous text",
            rule=ScalarComparisonRule(
                field=FieldOperand(field_id="x"),
                comparator=Comparator.GT,
                threshold=LiteralOperand(value=0.0),
            ),
            primary_field="x",
            weight=0.10,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[
                AmbiguityRecord(
                    level=AmbiguityLevel.MEDIUM,
                    description="Threshold interpretation required judgment",
                    suggestion="Confirm 50 is the correct ISM contraction threshold",
                ),
            ],
        )
        assert len(ind.ambiguities) == 1
        assert ind.ambiguities[0].level == AmbiguityLevel.MEDIUM


class TestCompiledActivationArtifact:
    def test_full_artifact_construction(self):
        artifact = CompiledActivationArtifact(
            source=SourcePackageRef(theory_id="valuation_mean_reversion"),
            phase_model=PhaseModel.SINGLE_PHASE,
            phases=[
                CompiledPhase(
                    phase_id="single",
                    phase_label="Active",
                    indicators=[
                        CompiledIndicator(
                            indicator_id="erp_compressed",
                            display_name="Equity risk premium compressed",
                            source_text="ERP below 1%",
                            rule=ScalarComparisonRule(
                                field=FieldOperand(field_id="equity_risk_premium", unit=ValueUnit.PERCENT),
                                comparator=Comparator.LT,
                                threshold=LiteralOperand(value=1.0, unit=ValueUnit.PERCENT),
                            ),
                            primary_field="equity_risk_premium",
                            weight=0.20,
                        ),
                    ],
                ),
            ],
            total_indicators=1,
            clean_count=1,
        )
        assert artifact.artifact_status == ArtifactStatus.DRAFT
        assert artifact.schema_version == 1
        assert len(artifact.phases) == 1
        assert len(artifact.phases[0].indicators) == 1

    def test_two_phase_artifact(self):
        artifact = CompiledActivationArtifact(
            source=SourcePackageRef(theory_id="debt_cycle_short"),
            phase_model=PhaseModel.TWO_PHASE,
            phases=[
                CompiledPhase(phase_id="expansion", phase_label="Expansion", indicators=[]),
                CompiledPhase(phase_id="contraction", phase_label="Contraction", indicators=[]),
            ],
        )
        assert artifact.phase_model == PhaseModel.TWO_PHASE
        assert len(artifact.phases) == 2

    def test_validation_summary(self):
        summary = ValidationSummary(
            status=ValidationStatus.WARNING,
            error_count=0,
            warning_count=2,
            warnings=["Unknown field: foo", "Unit is UNKNOWN"],
        )
        assert summary.status == ValidationStatus.WARNING


# ---------------------------------------------------------------------------
# 4. Field registry tests
# ---------------------------------------------------------------------------

from backend.schemas.v9.field_registry import (
    FieldEntry,
    FieldKind,
    FieldRegistry,
    FieldSource,
    DataFrequency,
    build_seed_registry,
)


class TestFieldRegistry:
    @pytest.fixture
    def registry(self):
        return build_seed_registry()

    def test_seed_registry_not_empty(self, registry):
        assert registry.field_count() > 0

    def test_known_fields_exist(self, registry):
        """Key fields from the spike must be in the seed registry."""
        required = [
            "growth.ism_proxy", "growth.initial_claims", "rates.fed_funds",
            "credit.hy_spread", "equity_risk_premium", "shiller_cape",
        ]
        for f in required:
            assert registry.has_field(f), f"Missing required field: {f}"

    def test_unknown_field_not_found(self, registry):
        assert not registry.has_field("totally.fake.field")
        assert registry.get_field("totally.fake.field") is None

    def test_unit_lookup(self, registry):
        assert registry.get_unit("growth.initial_claims") == ValueUnit.COUNT
        assert registry.get_unit("rates.fed_funds") == ValueUnit.PERCENT
        assert registry.get_unit("credit.hy_spread") == ValueUnit.BASIS_POINTS

    def test_semantic_type_lookup(self, registry):
        assert registry.get_semantic_type("rates.fed_funds") == SemanticType.RATE
        assert registry.get_semantic_type("growth.gdp_latest") == SemanticType.LEVEL
        assert registry.get_semantic_type("growth.ism_proxy") == SemanticType.INDEX

    def test_comparison_legality_rate_vs_rate(self, registry):
        """Fed funds vs curve spread — both RATE_LIKE, legal."""
        legal, reason = registry.check_comparison_legality("rates.fed_funds", "rates.curve_2s10s")
        assert legal

    def test_comparison_legality_rate_vs_level(self, registry):
        """Fed funds vs GDP level — RATE_LIKE vs LEVEL_LIKE, illegal."""
        legal, reason = registry.check_comparison_legality("rates.fed_funds", "growth.gdp_latest")
        assert not legal
        assert "mismatch" in reason.lower()

    def test_comparison_legality_unknown_field(self, registry):
        legal, reason = registry.check_comparison_legality("rates.fed_funds", "nonexistent")
        assert not legal
        assert "Unknown field" in reason

    def test_unit_compatibility_matching(self, registry):
        ok, reason = registry.check_unit_compatibility("rates.fed_funds", ValueUnit.PERCENT)
        assert ok

    def test_unit_compatibility_convertible(self, registry):
        """Basis points literal against a percent field — convertible."""
        ok, reason = registry.check_unit_compatibility("rates.fed_funds", ValueUnit.BASIS_POINTS)
        assert ok
        assert "convertible" in reason

    def test_unit_compatibility_mismatch(self, registry):
        """Tons literal against a percent field — not convertible."""
        ok, reason = registry.check_unit_compatibility("rates.fed_funds", ValueUnit.TONS)
        assert not ok
        assert "mismatch" in reason.lower()

    def test_computed_field_dependencies(self, registry):
        """Computed fields should have their dependencies validated."""
        entry = registry.get_field("net_liquidity")
        assert entry is not None
        assert entry.is_computed
        assert len(entry.dependencies) > 0

    def test_validate_dependencies_all_present(self, registry):
        """equity_risk_premium depends on treasury_10y which is in the registry."""
        missing = registry.validate_dependencies("equity_risk_premium")
        assert len(missing) == 0

    def test_register_new_field(self, registry):
        new_entry = FieldEntry(
            field_id="test.new_field",
            display_name="Test New Field",
            unit=ValueUnit.PERCENT,
            semantic_type=SemanticType.RATE,
        )
        registry.register(new_entry)
        assert registry.has_field("test.new_field")

    def test_comparison_class_derivation(self, registry):
        """comparison_class is derived from semantic_type, not stored."""
        entry = registry.get_field("rates.fed_funds")
        assert entry.comparison_class == ComparisonClass.RATE_LIKE


# ---------------------------------------------------------------------------
# 5. Validator error taxonomy tests
# ---------------------------------------------------------------------------

from backend.schemas.v9.errors import (
    ErrorCode,
    Severity,
    ValidationFinding,
    ValidationReport,
)


class TestErrorCode:
    def test_all_codes_are_unique(self):
        """Error codes must be unique strings."""
        values = [e.value for e in ErrorCode]
        assert len(values) == len(set(values))

    def test_expected_codes_exist(self):
        """Key error codes from the spec must exist."""
        required = [
            "unknown_field", "unresolved_field", "unit_mismatch",
            "illegal_comparison", "unsupported_rule_type", "ambiguous_threshold",
            "blocked_by_missing_series", "missing_named_pattern",
            "invalid_phase_reference", "unresolved_operand", "trivial_placeholder",
        ]
        code_values = {e.value for e in ErrorCode}
        for r in required:
            assert r in code_values, f"Missing required error code: {r}"


class TestValidationFinding:
    def test_construction(self):
        f = ValidationFinding(
            error_code=ErrorCode.F_UNKNOWN_FIELD,
            severity=Severity.ERROR,
            indicator_id="test_indicator",
            message="Field 'foo.bar' not in registry",
            detail={"field_id": "foo.bar"},
        )
        assert f.is_error
        assert not f.is_warning

    def test_warning_finding(self):
        f = ValidationFinding(
            error_code=ErrorCode.U_UNKNOWN_UNIT,
            severity=Severity.WARNING,
            message="Unit is UNKNOWN",
        )
        assert f.is_warning
        assert not f.is_error


class TestValidationReport:
    def test_empty_report_passes(self):
        report = ValidationReport(theory_id="test")
        assert report.passed

    def test_report_with_error_fails(self):
        report = ValidationReport(theory_id="test")
        report.add_error(ErrorCode.F_UNKNOWN_FIELD, "Unknown field: foo")
        assert not report.passed
        assert report.error_count == 1

    def test_report_with_only_warnings_passes(self):
        report = ValidationReport(theory_id="test")
        report.add_warning(ErrorCode.U_UNKNOWN_UNIT, "Unit is UNKNOWN")
        report.add_warning(ErrorCode.U_UNKNOWN_UNIT, "Another UNKNOWN unit")
        assert report.passed
        assert report.warning_count == 2

    def test_findings_by_code(self):
        report = ValidationReport(theory_id="test")
        report.add_error(ErrorCode.F_UNKNOWN_FIELD, "Field A")
        report.add_error(ErrorCode.F_UNKNOWN_FIELD, "Field B")
        report.add_warning(ErrorCode.U_UNKNOWN_UNIT, "Unit C")
        assert len(report.findings_by_code(ErrorCode.F_UNKNOWN_FIELD)) == 2
        assert len(report.findings_by_code(ErrorCode.U_UNKNOWN_UNIT)) == 1

    def test_has_code(self):
        report = ValidationReport(theory_id="test")
        report.add_error(ErrorCode.R_TRIVIAL_PLACEHOLDER, "gt 0.0 is suspicious")
        assert report.has_code(ErrorCode.R_TRIVIAL_PLACEHOLDER)
        assert not report.has_code(ErrorCode.F_UNKNOWN_FIELD)

    def test_summary_format(self):
        report = ValidationReport(theory_id="test_theory")
        report.add_error(ErrorCode.F_UNKNOWN_FIELD, "Unknown: foo")
        summary = report.summary()
        assert "test_theory" in summary
        assert "FAIL" in summary
        assert "unknown_field" in summary

    def test_mixed_severities(self):
        report = ValidationReport(theory_id="test")
        report.add_error(ErrorCode.F_UNKNOWN_FIELD, "Unknown: foo")
        report.add_warning(ErrorCode.U_UNKNOWN_UNIT, "UNKNOWN unit")
        report.add_info(ErrorCode.X_AMBIGUOUS_THRESHOLD, "Minor ambiguity")
        assert not report.passed
        assert report.error_count == 1
        assert report.warning_count == 1
        assert report.info_count == 1


# ---------------------------------------------------------------------------
# 6. Series interface tests
# ---------------------------------------------------------------------------

from backend.engine.v9.series_interface import (
    PRIMITIVE_CATALOGUE,
    SUPPORTED_PRIMITIVES,
    PrimitiveResult,
    PrimitiveResultStatus,
    SeriesData,
)


class TestSeriesData:
    def test_construction(self):
        sd = SeriesData("growth.ism_proxy", [50.1, 51.2, 49.8])
        assert sd.field_id == "growth.ism_proxy"
        assert sd.length == 3
        assert sd.latest == 49.8

    def test_empty_series(self):
        sd = SeriesData("x", [])
        assert sd.is_empty
        assert sd.latest is None


class TestPrimitiveCatalogue:
    def test_catalogue_not_empty(self):
        assert len(PRIMITIVE_CATALOGUE) > 0

    def test_expected_primitives_exist(self):
        """Key primitives from the v9 plan must be in the catalogue."""
        required = [
            "latest_value", "absolute_change", "percent_change",
            "rolling_max", "rolling_min", "rolling_mean",
            "percentile_rank", "is_at_extreme",
            "trend_direction", "slope",
            "crossed_above", "crossed_below",
            "count_true", "n_of_last_k", "consecutive_true",
            "evaluate_named_pattern",
        ]
        for r in required:
            assert r in SUPPORTED_PRIMITIVES, f"Missing required primitive: {r}"

    def test_supported_primitives_matches_catalogue(self):
        assert SUPPORTED_PRIMITIVES == frozenset(PRIMITIVE_CATALOGUE.keys())


class TestPrimitiveResult:
    def test_ok_with_value(self):
        r = PrimitiveResult(PrimitiveResultStatus.OK, value=42.0)
        assert r.status == PrimitiveResultStatus.OK
        assert r.value == 42.0

    def test_ok_with_boolean(self):
        r = PrimitiveResult(PrimitiveResultStatus.OK, boolean=True)
        assert r.boolean is True

    def test_insufficient_data(self):
        r = PrimitiveResult(PrimitiveResultStatus.INSUFFICIENT_DATA, detail="need 12, have 3")
        assert r.status == PrimitiveResultStatus.INSUFFICIENT_DATA
        assert r.value is None


# ---------------------------------------------------------------------------
# 7. Cross-cutting integration tests
# ---------------------------------------------------------------------------

class TestCrossCutting:
    """Tests that verify contracts work together correctly."""

    def test_initial_claims_unit_bug_detectable(self):
        """The initial claims unit bug from the spike MUST be detectable.

        The spike found: compiled threshold is 250 (thousands), briefing
        stores 202000 (count). The unit model must detect this mismatch
        and allow normalization.
        """
        registry = build_seed_registry()
        # Field is stored as COUNT in the briefing
        field_unit = registry.get_unit("growth.initial_claims")
        assert field_unit == ValueUnit.COUNT

        # Compiled threshold would be in THOUSANDS
        threshold_unit = ValueUnit.THOUSANDS

        # The unit model must be able to normalize
        ok, reason = registry.check_unit_compatibility("growth.initial_claims", threshold_unit)
        assert ok, f"Should be convertible: {reason}"

        # And normalization should produce correct values
        a, b, common = normalize_to_common_unit(
            202000, ValueUnit.COUNT,
            250.0, ValueUnit.THOUSANDS,
        )
        # 250 thousands = 250,000 count
        assert b == 250000.0
        assert a == 202000
        # Now the comparison works correctly: 202000 < 250000 = True
        assert a < b

    def test_fed_funds_vs_gdp_level_caught(self):
        """Comparing fed_funds (rate) to gdp_latest (level) must be caught.

        This is the GDP level vs growth rate bug from the spike.
        """
        registry = build_seed_registry()
        legal, reason = registry.check_comparison_legality("rates.fed_funds", "growth.gdp_latest")
        assert not legal, "Rate vs level comparison should be illegal"
        assert "mismatch" in reason.lower()

    def test_fed_funds_vs_real_gdp_growth_legal(self):
        """Fed funds (rate) vs real GDP growth (growth_rate) should be legal.

        Both are RATE_LIKE — this is a meaningful comparison.
        """
        registry = build_seed_registry()
        legal, reason = registry.check_comparison_legality("rates.fed_funds", "growth.real_gdp")
        assert legal, f"Rate vs growth_rate should be legal: {reason}"

    def test_error_taxonomy_covers_spike_findings(self):
        """Every type of validation failure from the spike should map to an error code."""
        # Unresolved field (loan_growth_yoy)
        assert ErrorCode.F_UNRESOLVED_FIELD.value == "unresolved_field"
        # Unit mismatch (initial claims)
        assert ErrorCode.U_UNIT_MISMATCH.value == "unit_mismatch"
        # Trivial placeholder (gt 0.0)
        assert ErrorCode.R_TRIVIAL_PLACEHOLDER.value == "trivial_placeholder"
        # Named pattern missing
        assert ErrorCode.R_MISSING_NAMED_PATTERN.value == "missing_named_pattern"
        # Blocked by missing series
        assert ErrorCode.X_BLOCKED_BY_MISSING_SERIES.value == "blocked_by_missing_series"

    def test_artifact_full_lifecycle(self):
        """An artifact can go through the full lifecycle: draft -> validated -> approved."""
        artifact = CompiledActivationArtifact(
            source=SourcePackageRef(theory_id="test_theory"),
            phase_model=PhaseModel.SINGLE_PHASE,
            phases=[
                CompiledPhase(
                    phase_id="single",
                    phase_label="Active",
                    indicators=[
                        CompiledIndicator(
                            indicator_id="test_ind",
                            display_name="Test",
                            source_text="Some condition",
                            rule=ScalarComparisonRule(
                                field=FieldOperand(field_id="x"),
                                comparator=Comparator.GT,
                                threshold=LiteralOperand(value=1.0),
                            ),
                            primary_field="x",
                            weight=0.20,
                        ),
                    ],
                ),
            ],
            total_indicators=1,
            clean_count=1,
        )
        # Starts as DRAFT
        assert artifact.artifact_status == ArtifactStatus.DRAFT

        # Validation passes
        artifact.validation = ValidationSummary(
            status=ValidationStatus.PASS,
            error_count=0,
            warning_count=0,
        )
        assert artifact.validation.status == ValidationStatus.PASS

        # Approve
        artifact.artifact_status = ArtifactStatus.APPROVED
        assert artifact.artifact_status == ArtifactStatus.APPROVED
