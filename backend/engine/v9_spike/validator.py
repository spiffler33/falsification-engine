"""Deterministic validator for compiled activation artifacts.

Checks:
- Schema validity (all required fields present)
- Field refs exist in known fields or are explicitly unresolved
- Units are explicit where needed
- Rule types are supported
- Ambiguous / unsupported items are surfaced cleanly
- Runtime never receives unresolved rule objects
"""
from __future__ import annotations

from backend.schemas.v9_spike.compiled_activation import (
    AmbiguityLevel,
    CompiledIndicator,
    CompiledPhase,
    CompiledRule,
    CompiledTheoryActivation,
    CompoundRule,
    FieldComparisonRule,
    LookbackExtremeRule,
    PersistenceRule,
    ScalarComparisonRule,
    TrendRule,
    ValueUnit,
)
from backend.engine.v9_spike.haiku_compiler import KNOWN_FIELDS


class ValidationFinding:
    """A single validation finding."""
    def __init__(self, severity: str, indicator: str, message: str):
        self.severity = severity  # "error", "warning", "info"
        self.indicator = indicator
        self.message = message

    def __repr__(self) -> str:
        return f"[{self.severity.upper()}] {self.indicator}: {self.message}"


class ValidationReport:
    """Full validation report for a compiled theory."""
    def __init__(self, theory_id: str):
        self.theory_id = theory_id
        self.findings: list[ValidationFinding] = []

    @property
    def passed(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "info")

    def add(self, severity: str, indicator: str, message: str):
        self.findings.append(ValidationFinding(severity, indicator, message))

    def summary(self) -> str:
        lines = [
            f"Validation: {self.theory_id} -- "
            f"{'PASS' if self.passed else 'FAIL'} "
            f"({self.error_count} errors, {self.warning_count} warnings, "
            f"{self.info_count} info)",
        ]
        for f in self.findings:
            lines.append(f"  {f!r}")
        return "\n".join(lines)


_KNOWN_FIELDS_SET = set(KNOWN_FIELDS)

SUPPORTED_RULE_TYPES = {
    "scalar_comparison", "field_comparison", "trend",
    "persistence", "lookback_extreme", "compound",
}


def _validate_field_ref(field: str, indicator_name: str, report: ValidationReport):
    """Check a single field reference."""
    if field.startswith("UNRESOLVED:"):
        report.add("error", indicator_name, f"Unresolved field ref: {field}")
    elif field not in _KNOWN_FIELDS_SET:
        report.add("warning", indicator_name, f"Unknown field: {field!r} (not in known fields list)")


def _validate_rule(rule: CompiledRule, indicator_name: str, report: ValidationReport):
    """Validate a single compiled rule recursively."""
    active = rule.active_rule()
    if active is None:
        report.add("error", indicator_name, "Empty rule: no rule type set")
        return

    if active.rule_type not in SUPPORTED_RULE_TYPES:
        report.add("error", indicator_name, f"Unsupported rule type: {active.rule_type}")
        return

    if isinstance(active, ScalarComparisonRule):
        _validate_field_ref(active.field, indicator_name, report)
        if active.unit == ValueUnit.UNKNOWN:
            report.add("warning", indicator_name, "Unit is UNKNOWN for scalar comparison")

    elif isinstance(active, FieldComparisonRule):
        _validate_field_ref(active.field_a, indicator_name, report)
        _validate_field_ref(active.field_b, indicator_name, report)

    elif isinstance(active, TrendRule):
        _validate_field_ref(active.field, indicator_name, report)
        if active.window_value <= 0:
            report.add("error", indicator_name, f"Trend window must be positive: {active.window_value}")

    elif isinstance(active, PersistenceRule):
        _validate_field_ref(active.field, indicator_name, report)
        if active.n > active.k:
            report.add("error", indicator_name, f"Persistence n ({active.n}) > k ({active.k})")

    elif isinstance(active, LookbackExtremeRule):
        _validate_field_ref(active.field, indicator_name, report)
        if active.lookback_value <= 0:
            report.add("error", indicator_name, f"Lookback must be positive: {active.lookback_value}")

    elif isinstance(active, CompoundRule):
        if not active.rules:
            report.add("error", indicator_name, "Compound rule has no sub-rules")
        for sub in active.rules:
            _validate_rule(sub, indicator_name, report)


def _validate_indicator(ind: CompiledIndicator, report: ValidationReport):
    """Validate a single compiled indicator."""
    # Check field_refs
    for ref in ind.field_refs:
        _validate_field_ref(ref, ind.indicator_name, report)

    # Check rule
    _validate_rule(ind.rule, ind.indicator_name, report)

    # Ambiguity surfacing
    if ind.ambiguity == AmbiguityLevel.HIGH:
        report.add("warning", ind.indicator_name, f"High ambiguity: {ind.ambiguity_notes}")
    elif ind.ambiguity == AmbiguityLevel.MEDIUM:
        report.add("info", ind.indicator_name, f"Medium ambiguity: {ind.ambiguity_notes}")

    # Compiler warnings
    for w in ind.compiler_warnings:
        report.add("info", ind.indicator_name, f"Compiler warning: {w}")

    # Weight sanity
    if ind.weight <= 0:
        report.add("warning", ind.indicator_name, "Weight is zero or negative")


def validate_compiled_theory(artifact: CompiledTheoryActivation) -> ValidationReport:
    """Validate a complete compiled theory activation artifact.

    Returns a ValidationReport. The artifact is safe for runtime evaluation
    only if report.passed is True.
    """
    report = ValidationReport(artifact.theory_id)

    if not artifact.phases:
        report.add("error", "(theory)", "No phases in compiled artifact")
        return report

    for phase in artifact.phases:
        if not phase.indicators:
            report.add("warning", f"(phase:{phase.phase_name})", "Phase has no indicators")
            continue

        for ind in phase.indicators:
            _validate_indicator(ind, report)

    return report
