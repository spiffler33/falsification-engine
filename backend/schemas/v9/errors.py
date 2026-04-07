"""v9 validator error taxonomy.

Explicit, structured error types for the validation pipeline.
Every validation failure is one of these types. No ad-hoc strings.

The taxonomy is organized by validation phase:
  1. Schema errors — structural problems with the artifact
  2. Field errors — problems with field references
  3. Unit errors — unit mismatches and conversion failures
  4. Rule errors — problems with rule structure or semantics
  5. Phase errors — problems with phase structure or transitions
  6. Semantic errors — cross-cutting semantic problems

Each error type carries:
  - A unique error_code for programmatic matching
  - A severity (error blocks runtime, warning allows with flag, info is advisory)
  - A structured detail payload
  - A human-readable message

Design principle: prefer loud failure over permissive interpretation.
If validation can't prove something is correct, it fails.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Severity of a validation finding.

    ERROR: artifact cannot be used for runtime evaluation
    WARNING: artifact is usable but has quality concerns
    INFO: advisory information for human reviewer
    """
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ---------------------------------------------------------------------------
# Error codes — the complete taxonomy
# ---------------------------------------------------------------------------

class ErrorCode(str, Enum):
    """Canonical error codes for the v9 validator.

    Every validation finding has exactly one error code.
    Error codes are stable identifiers — do not rename or reuse.
    """
    # --- Schema errors (S_xxx) ---
    S_EMPTY_ARTIFACT = "empty_artifact"             # artifact has no phases
    S_EMPTY_PHASE = "empty_phase"                   # phase has no indicators
    S_INVALID_SCHEMA_VERSION = "invalid_schema_version"
    S_MISSING_REQUIRED_FIELD = "missing_required_field"
    S_INVALID_WEIGHT = "invalid_weight"             # weight <= 0 or > 1

    # --- Field errors (F_xxx) ---
    F_UNKNOWN_FIELD = "unknown_field"               # field_id not in registry
    F_UNRESOLVED_FIELD = "unresolved_field"         # field starts with UNRESOLVED:
    F_MISSING_FIELD_METADATA = "missing_field_metadata"  # field exists but lacks metadata
    F_UNAVAILABLE_SERIES = "unavailable_series"     # field exists but no series data

    # --- Unit errors (U_xxx) ---
    U_UNIT_MISMATCH = "unit_mismatch"               # field unit vs literal unit incompatible
    U_UNKNOWN_UNIT = "unknown_unit"                  # unit is UNKNOWN (not declared)
    U_UNCONVERTIBLE_UNITS = "unconvertible_units"   # no conversion between units
    U_SCALE_MISMATCH = "scale_mismatch"             # e.g., comparing thousands to raw count

    # --- Rule errors (R_xxx) ---
    R_UNSUPPORTED_RULE_TYPE = "unsupported_rule_type"
    R_EMPTY_RULE = "empty_rule"                     # rule has no content
    R_EMPTY_COMPOUND = "empty_compound"             # compound rule has no clauses
    R_INVALID_PERSISTENCE = "invalid_persistence"   # n > k, or n <= 0
    R_INVALID_WINDOW = "invalid_window"             # window value <= 0
    R_INVALID_COMPARATOR = "invalid_comparator"
    R_TRIVIAL_PLACEHOLDER = "trivial_placeholder"   # suspiciously trivial rule (gt 0.0)
    R_MISSING_NAMED_PATTERN = "missing_named_pattern"  # named pattern not registered
    R_INVALID_DELTA_DIRECTION = "invalid_delta_direction"  # delta_change with stable direction

    # --- Phase errors (P_xxx) ---
    P_INVALID_PHASE_REFERENCE = "invalid_phase_reference"
    P_PHASE_MODEL_MISMATCH = "phase_model_mismatch"  # declared two_phase but only 1 phase
    P_DUPLICATE_PHASE_ID = "duplicate_phase_id"
    P_MISSING_THRESHOLDS = "missing_thresholds"      # phase missing activation thresholds

    # --- Semantic errors (X_xxx) ---
    X_ILLEGAL_COMPARISON = "illegal_comparison"      # comparing incompatible semantic types
    X_AMBIGUOUS_THRESHOLD = "ambiguous_threshold"    # threshold couldn't be deterministically parsed
    X_BLOCKED_BY_MISSING_SERIES = "blocked_by_missing_series"  # requires series, none available
    X_UNRESOLVED_OPERAND = "unresolved_operand"      # operand couldn't be resolved
    X_UNRESOLVED_DERIVED = "unresolved_derived"      # derived function not registered
    X_DEPENDENCY_MISSING = "dependency_missing"      # computed field's dependency not in registry


# ---------------------------------------------------------------------------
# Validation finding — one issue found during validation
# ---------------------------------------------------------------------------

class ValidationFinding(BaseModel):
    """A single validation finding.

    Every finding is one typed error from the taxonomy.
    Programmatic code matches on error_code, not on message strings.
    """
    error_code: ErrorCode
    severity: Severity
    indicator_id: str = ""      # which indicator (empty = artifact-level)
    phase_id: str = ""          # which phase (empty = artifact-level)
    message: str                # human-readable description
    detail: dict[str, Any] = {} # structured payload for programmatic use

    @property
    def is_error(self) -> bool:
        return self.severity == Severity.ERROR

    @property
    def is_warning(self) -> bool:
        return self.severity == Severity.WARNING


# ---------------------------------------------------------------------------
# Validation report — all findings for one artifact
# ---------------------------------------------------------------------------

class ValidationReport(BaseModel):
    """Complete validation report for one compiled artifact.

    The artifact is safe for runtime evaluation only if passed is True
    (no findings with severity=ERROR).
    """
    theory_id: str
    findings: list[ValidationFinding] = []

    @property
    def passed(self) -> bool:
        """True if no errors (warnings and info are allowed)."""
        return not any(f.is_error for f in self.findings)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.is_error)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.is_warning)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.INFO)

    def errors(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.is_error]

    def warnings(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.is_warning]

    def add(
        self,
        error_code: ErrorCode,
        severity: Severity,
        message: str,
        indicator_id: str = "",
        phase_id: str = "",
        detail: Optional[dict[str, Any]] = None,
    ) -> None:
        """Add a finding to the report."""
        self.findings.append(ValidationFinding(
            error_code=error_code,
            severity=severity,
            indicator_id=indicator_id,
            phase_id=phase_id,
            message=message,
            detail=detail or {},
        ))

    def add_error(
        self, error_code: ErrorCode, message: str, **kwargs: Any,
    ) -> None:
        """Convenience: add an ERROR finding."""
        self.add(error_code, Severity.ERROR, message, **kwargs)

    def add_warning(
        self, error_code: ErrorCode, message: str, **kwargs: Any,
    ) -> None:
        """Convenience: add a WARNING finding."""
        self.add(error_code, Severity.WARNING, message, **kwargs)

    def add_info(
        self, error_code: ErrorCode, message: str, **kwargs: Any,
    ) -> None:
        """Convenience: add an INFO finding."""
        self.add(error_code, Severity.INFO, message, **kwargs)

    def summary(self) -> str:
        """Human-readable summary."""
        status = "PASS" if self.passed else "FAIL"
        lines = [
            f"Validation: {self.theory_id} -- {status} "
            f"({self.error_count} errors, {self.warning_count} warnings, {self.info_count} info)",
        ]
        for f in self.findings:
            prefix = f"  [{f.severity.value.upper()}]"
            loc = f.indicator_id or f.phase_id or "(artifact)"
            lines.append(f"{prefix} {loc}: [{f.error_code.value}] {f.message}")
        return "\n".join(lines)

    def findings_by_code(self, code: ErrorCode) -> list[ValidationFinding]:
        """Get all findings with a specific error code."""
        return [f for f in self.findings if f.error_code == code]

    def has_code(self, code: ErrorCode) -> bool:
        """Check if any finding has this error code."""
        return any(f.error_code == code for f in self.findings)
