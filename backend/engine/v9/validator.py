"""v9 Phase 1: Artifact validator.

Validates compiled activation artifacts using the Phase 0 error taxonomy.
The validator runs BEFORE the evaluator — only validated artifacts should
be evaluated at runtime.

Validation checks:
  1. Schema: non-empty artifact, valid weights, schema version
  2. Fields: existence in registry, unresolved references
  3. Units: compatibility between field and threshold
  4. Rules: well-formed structure, no trivial placeholders
  5. Phases: model consistency, no duplicate IDs
  6. Semantic: comparison legality, dependency integrity, named patterns

Design principle: prefer loud failure over permissive interpretation.
If validation can't prove something is correct, it fails.
"""
from __future__ import annotations

from backend.schemas.v9.compiled_activation import (
    CompiledActivationArtifact,
    CompiledIndicator,
    CompiledPhase,
    PhaseModel,
)
from backend.schemas.v9.errors import (
    ErrorCode,
    Severity,
    ValidationFinding,
    ValidationReport,
)
from backend.schemas.v9.field_registry import FieldRegistry
from backend.schemas.v9.rules import (
    CompoundRule,
    DeltaChangeRule,
    FieldComparisonRule,
    FieldOperand,
    HistoricalExtremeRule,
    LiteralOperand,
    NamedPatternRule,
    PersistenceRule,
    Rule,
    ScalarComparisonRule,
    TrendDirection,
    TrendStateRule,
    REGISTERED_NAMED_PATTERNS,
)
from backend.schemas.v9.units import (
    SemanticType,
    ValueUnit,
    are_comparable,
    can_convert,
)
from backend.engine.v9.derived_functions import is_registered as is_derived_registered
from backend.engine.v9.series_interface import SeriesStore


class ArtifactValidator:
    """Validates a compiled activation artifact.

    Usage:
        validator = ArtifactValidator(registry, series_store=None)
        report = validator.validate(artifact)
        if report.passed:
            # safe to evaluate
    """

    def __init__(
        self,
        registry: FieldRegistry,
        series_store: SeriesStore | None = None,
    ):
        self._registry = registry
        self._series_store = series_store

    def validate(
        self, artifact: CompiledActivationArtifact,
    ) -> ValidationReport:
        """Run all validation checks on an artifact.

        Returns a ValidationReport with all findings.
        """
        report = ValidationReport(theory_id=artifact.source.theory_id)

        self._check_schema(artifact, report)
        self._check_phases(artifact, report)

        for phase in artifact.phases:
            for indicator in phase.indicators:
                self._check_indicator(indicator, phase.phase_id, report)

        return report

    # -------------------------------------------------------------------
    # Schema checks
    # -------------------------------------------------------------------

    def _check_schema(
        self,
        artifact: CompiledActivationArtifact,
        report: ValidationReport,
    ) -> None:
        """Schema-level validation."""
        if not artifact.phases:
            report.add_error(
                ErrorCode.S_EMPTY_ARTIFACT,
                "Artifact has no phases",
            )

        if artifact.schema_version < 1:
            report.add_error(
                ErrorCode.S_INVALID_SCHEMA_VERSION,
                f"Invalid schema version: {artifact.schema_version}",
            )

    # -------------------------------------------------------------------
    # Phase checks
    # -------------------------------------------------------------------

    def _check_phases(
        self,
        artifact: CompiledActivationArtifact,
        report: ValidationReport,
    ) -> None:
        """Phase-level validation."""
        phase_ids = [p.phase_id for p in artifact.phases]

        # Duplicate phase IDs
        seen = set()
        for pid in phase_ids:
            if pid in seen:
                report.add_error(
                    ErrorCode.P_DUPLICATE_PHASE_ID,
                    f"Duplicate phase_id: {pid}",
                    phase_id=pid,
                )
            seen.add(pid)

        # Phase model consistency
        if artifact.phase_model == PhaseModel.TWO_PHASE and len(artifact.phases) < 2:
            report.add_error(
                ErrorCode.P_PHASE_MODEL_MISMATCH,
                f"Declared two_phase but only {len(artifact.phases)} phase(s)",
            )
        if artifact.phase_model == PhaseModel.SINGLE_PHASE and len(artifact.phases) > 1:
            report.add_warning(
                ErrorCode.P_PHASE_MODEL_MISMATCH,
                f"Declared single_phase but has {len(artifact.phases)} phases",
            )

        # Empty phases
        for phase in artifact.phases:
            if not phase.indicators:
                report.add_warning(
                    ErrorCode.S_EMPTY_PHASE,
                    f"Phase {phase.phase_id} has no indicators",
                    phase_id=phase.phase_id,
                )

    # -------------------------------------------------------------------
    # Indicator checks
    # -------------------------------------------------------------------

    def _check_indicator(
        self,
        indicator: CompiledIndicator,
        phase_id: str,
        report: ValidationReport,
    ) -> None:
        """Validate a single compiled indicator."""
        ind_id = indicator.indicator_id

        # Weight
        if indicator.weight <= 0 or indicator.weight > 1:
            report.add_error(
                ErrorCode.S_INVALID_WEIGHT,
                f"Invalid weight: {indicator.weight}",
                indicator_id=ind_id,
                phase_id=phase_id,
            )

        # Primary field
        self._check_field_exists(
            indicator.primary_field, ind_id, phase_id, report,
        )

        # Field dependencies
        for dep in indicator.field_dependencies:
            self._check_field_exists(dep, ind_id, phase_id, report)

        # Rule validation
        self._check_rule(indicator.rule, ind_id, phase_id, report)

    # -------------------------------------------------------------------
    # Field checks
    # -------------------------------------------------------------------

    def _check_field_exists(
        self,
        field_id: str,
        indicator_id: str,
        phase_id: str,
        report: ValidationReport,
    ) -> None:
        """Check that a field_id exists in the registry."""
        if not field_id:
            return

        if field_id.startswith("UNRESOLVED:"):
            report.add_error(
                ErrorCode.F_UNRESOLVED_FIELD,
                f"Unresolved field: {field_id}",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )
            return

        if not self._registry.has_field(field_id):
            report.add_error(
                ErrorCode.F_UNKNOWN_FIELD,
                f"Unknown field: {field_id}",
                indicator_id=indicator_id,
                phase_id=phase_id,
                detail={"field_id": field_id},
            )

    # -------------------------------------------------------------------
    # Rule checks (recursive for compound)
    # -------------------------------------------------------------------

    def _check_rule(
        self,
        rule: Rule,
        indicator_id: str,
        phase_id: str,
        report: ValidationReport,
    ) -> None:
        """Validate a rule's structure and semantics."""
        rt = rule.rule_type

        if rt == "scalar_comparison":
            self._check_scalar_rule(rule, indicator_id, phase_id, report)
        elif rt == "field_comparison":
            self._check_field_comparison_rule(rule, indicator_id, phase_id, report)
        elif rt == "compound":
            self._check_compound_rule(rule, indicator_id, phase_id, report)
        elif rt == "persistence":
            self._check_persistence_rule(rule, indicator_id, phase_id, report)
        elif rt == "trend_state":
            self._check_trend_rule(rule, indicator_id, phase_id, report)
        elif rt == "historical_extreme":
            self._check_historical_extreme_rule(rule, indicator_id, phase_id, report)
        elif rt == "named_pattern":
            self._check_named_pattern_rule(rule, indicator_id, phase_id, report)
        elif rt == "delta_change":
            self._check_delta_change_rule(rule, indicator_id, phase_id, report)
        else:
            report.add_error(
                ErrorCode.R_UNSUPPORTED_RULE_TYPE,
                f"Unknown rule_type: {rt}",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )

    def _check_scalar_rule(
        self,
        rule: ScalarComparisonRule,
        indicator_id: str,
        phase_id: str,
        report: ValidationReport,
    ) -> None:
        """Validate a scalar_comparison rule."""
        # Check field exists
        self._check_field_exists(
            rule.field.field_id, indicator_id, phase_id, report,
        )

        # Check unit compatibility
        field_entry = self._registry.get_field(rule.field.field_id)
        if field_entry and rule.threshold.unit != ValueUnit.DIMENSIONLESS:
            ok, reason = self._registry.check_unit_compatibility(
                rule.field.field_id, rule.threshold.unit,
            )
            if not ok:
                report.add_error(
                    ErrorCode.U_UNIT_MISMATCH,
                    f"Unit mismatch: {reason}",
                    indicator_id=indicator_id,
                    phase_id=phase_id,
                    detail={"field_id": rule.field.field_id,
                            "field_unit": field_entry.unit.value,
                            "threshold_unit": rule.threshold.unit.value},
                )

        # Trivial placeholder detection
        if (rule.threshold.value == 0.0
                and rule.threshold.unit == ValueUnit.DIMENSIONLESS):
            report.add_warning(
                ErrorCode.R_TRIVIAL_PLACEHOLDER,
                f"Suspiciously trivial threshold: {rule.comparator.value} 0.0 (dimensionless)",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )

    def _check_field_comparison_rule(
        self,
        rule: FieldComparisonRule,
        indicator_id: str,
        phase_id: str,
        report: ValidationReport,
    ) -> None:
        """Validate a field_comparison rule."""
        # Check operand fields
        if isinstance(rule.left, FieldOperand):
            self._check_field_exists(
                rule.left.field_id, indicator_id, phase_id, report,
            )
        if isinstance(rule.right, FieldOperand):
            self._check_field_exists(
                rule.right.field_id, indicator_id, phase_id, report,
            )

        # Check derived function registration
        from backend.schemas.v9.rules import DerivedOperand
        if isinstance(rule.right, DerivedOperand):
            if not is_derived_registered(rule.right.function_name):
                report.add_error(
                    ErrorCode.X_UNRESOLVED_DERIVED,
                    f"Unregistered derived function: {rule.right.function_name}",
                    indicator_id=indicator_id,
                    phase_id=phase_id,
                )

        # Semantic comparison legality
        left_st = None
        right_st = None
        if isinstance(rule.left, FieldOperand):
            left_st = self._get_semantic_type(rule.left.field_id, rule.left.semantic_type)
        if isinstance(rule.right, FieldOperand):
            right_st = self._get_semantic_type(rule.right.field_id, rule.right.semantic_type)

        if left_st and right_st and not are_comparable(left_st, right_st):
            report.add_error(
                ErrorCode.X_ILLEGAL_COMPARISON,
                f"Illegal comparison: {left_st.value} vs {right_st.value}",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )

    def _check_compound_rule(
        self,
        rule: CompoundRule,
        indicator_id: str,
        phase_id: str,
        report: ValidationReport,
    ) -> None:
        """Validate a compound rule (recursive)."""
        if not rule.clauses:
            report.add_error(
                ErrorCode.R_EMPTY_COMPOUND,
                "Compound rule has no clauses",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )
            return

        for clause in rule.clauses:
            self._check_rule(clause, indicator_id, phase_id, report)

    def _check_persistence_rule(
        self,
        rule: PersistenceRule,
        indicator_id: str,
        phase_id: str,
        report: ValidationReport,
    ) -> None:
        """Validate a persistence rule."""
        if rule.n <= 0:
            report.add_error(
                ErrorCode.R_INVALID_PERSISTENCE,
                f"Persistence n must be > 0, got {rule.n}",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )
        if rule.k is not None and rule.n > rule.k:
            report.add_error(
                ErrorCode.R_INVALID_PERSISTENCE,
                f"Persistence n ({rule.n}) > k ({rule.k})",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )
        if rule.window.value <= 0:
            report.add_error(
                ErrorCode.R_INVALID_WINDOW,
                f"Window value must be > 0, got {rule.window.value}",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )

        # Recursively validate inner condition
        self._check_rule(rule.condition, indicator_id, phase_id, report)

    def _check_trend_rule(
        self,
        rule: TrendStateRule,
        indicator_id: str,
        phase_id: str,
        report: ValidationReport,
    ) -> None:
        """Validate a trend_state rule."""
        self._check_field_exists(
            rule.field.field_id, indicator_id, phase_id, report,
        )
        if rule.window.value <= 0:
            report.add_error(
                ErrorCode.R_INVALID_WINDOW,
                f"Window value must be > 0, got {rule.window.value}",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )

    def _check_historical_extreme_rule(
        self,
        rule: HistoricalExtremeRule,
        indicator_id: str,
        phase_id: str,
        report: ValidationReport,
    ) -> None:
        """Validate a historical_extreme rule."""
        self._check_field_exists(
            rule.field.field_id, indicator_id, phase_id, report,
        )
        if rule.lookback.value <= 0:
            report.add_error(
                ErrorCode.R_INVALID_WINDOW,
                f"Lookback must be > 0, got {rule.lookback.value}",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )

    def _check_named_pattern_rule(
        self,
        rule: NamedPatternRule,
        indicator_id: str,
        phase_id: str,
        report: ValidationReport,
    ) -> None:
        """Validate a named_pattern rule."""
        if rule.name not in REGISTERED_NAMED_PATTERNS:
            report.add_error(
                ErrorCode.R_MISSING_NAMED_PATTERN,
                f"Named pattern not registered: {rule.name}",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )

        for dep in rule.field_dependencies:
            self._check_field_exists(dep, indicator_id, phase_id, report)

    def _check_delta_change_rule(
        self,
        rule: DeltaChangeRule,
        indicator_id: str,
        phase_id: str,
        report: ValidationReport,
    ) -> None:
        """Validate a delta_change rule."""
        self._check_field_exists(
            rule.field.field_id, indicator_id, phase_id, report,
        )
        if rule.window.value <= 0:
            report.add_error(
                ErrorCode.R_INVALID_WINDOW,
                f"Window value must be > 0, got {rule.window.value}",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )
        if rule.direction == TrendDirection.STABLE:
            report.add_error(
                ErrorCode.R_INVALID_DELTA_DIRECTION,
                "delta_change does not support direction=stable",
                indicator_id=indicator_id,
                phase_id=phase_id,
            )

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _get_semantic_type(
        self, field_id: str, fallback: SemanticType,
    ) -> SemanticType:
        """Get semantic type from registry, falling back to the declared type."""
        reg_st = self._registry.get_semantic_type(field_id)
        return reg_st if reg_st else fallback
