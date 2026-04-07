"""v9 canonical compiled activation schema.

This is the production schema for compiled activation artifacts.
Each theory module's English activation semantics are compiled into
one of these artifacts. The artifact is:

  1. Produced by the Haiku compiler (upstream, Phase 2)
  2. Validated deterministically (Phase 1 validator)
  3. Consumed by the deterministic runtime evaluator (Phase 1 runtime)

The artifact is the machine contract between English and deterministic scoring.
It is checked into the repo alongside the theory module and becomes the
runtime source of truth for activation evaluation.

Design decisions vs spike schema:
  - Uses discriminated union Rule type instead of optional-field wrapper
  - Explicit source provenance with file/section/line references
  - Structured ambiguity model (not just a string level + notes)
  - Explicit validation status as part of the artifact
  - Indicator-level exclusion policy for denominator handling
  - Richer compiler metadata (prompt version, schema version, etc.)
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from backend.schemas.v9.rules import Rule
from backend.schemas.v9.units import SemanticType, ValueUnit


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ArtifactStatus(str, Enum):
    """Lifecycle status of a compiled artifact."""
    DRAFT = "draft"           # freshly compiled, not yet reviewed
    REVIEWED = "reviewed"     # human has reviewed, not yet approved for runtime
    APPROVED = "approved"     # approved for runtime evaluation
    REJECTED = "rejected"     # reviewed and rejected (needs recompilation)
    SUPERSEDED = "superseded" # replaced by a newer compilation


class AmbiguityLevel(str, Enum):
    """How much interpretation the compiler had to apply."""
    NONE = "none"       # unambiguous, maps cleanly to primitives
    LOW = "low"         # minor interpretation, high confidence
    MEDIUM = "medium"   # meaningful interpretation, moderate confidence
    HIGH = "high"       # significant ambiguity, low confidence


class CompilationStatus(str, Enum):
    """Whether an indicator compiled successfully."""
    CLEAN = "clean"           # compiled without issues
    WARNING = "warning"       # compiled but with concerns
    BLOCKED = "blocked"       # could not compile — not evaluable


class ValidationStatus(str, Enum):
    """Outcome of deterministic validation."""
    PASS = "pass"
    WARNING = "warning"       # passed but with warnings
    FAIL = "fail"


class ExclusionPolicy(str, Enum):
    """How to handle an indicator in the scoring denominator.

    Controls what happens when an indicator cannot be evaluated
    (e.g., because it requires time-series data not yet available).
    """
    SCORE_IF_EVALUABLE = "score_if_evaluable"  # include in denominator only if evaluable
    ALWAYS_INCLUDE = "always_include"           # always in denominator (missing = False)
    EXCLUDE_FROM_SCORING = "exclude_from_scoring"  # never in denominator (context flag)


class PhaseModel(str, Enum):
    """Whether the theory has one or two activation phases."""
    SINGLE_PHASE = "single_phase"
    TWO_PHASE = "two_phase"


# ---------------------------------------------------------------------------
# Source provenance — where the English came from
# ---------------------------------------------------------------------------

class SourceProvenance(BaseModel):
    """Tracks exactly where the source English was found.

    A human reviewing the artifact should be able to find the
    original text in the theory module using this reference.
    """
    file: str = ""              # relative path to source file
    section: str = ""           # section name within file
    line_range: str = ""        # e.g., "12-18"


# ---------------------------------------------------------------------------
# Ambiguity record — structured, not just a string
# ---------------------------------------------------------------------------

class AmbiguityRecord(BaseModel):
    """A single ambiguity finding from compilation.

    Each ambiguity has a level, a specific description, and optionally
    a suggested resolution for the human reviewer.
    """
    level: AmbiguityLevel
    description: str
    suggestion: str = ""        # optional human-facing resolution suggestion


# ---------------------------------------------------------------------------
# Compiled indicator
# ---------------------------------------------------------------------------

class CompiledIndicator(BaseModel):
    """A single compiled indicator — one row from the activation table.

    This is the unit of compilation: one English threshold/direction
    description compiled into one deterministic rule.

    Carries full provenance so a human can trace:
      1. What the English said (source_text, source)
      2. What the compiler thought it meant (normalized_paraphrase)
      3. What the runtime will evaluate (rule)
      4. What was ambiguous (ambiguities, compilation_status)
    """
    # Identity
    indicator_id: str                           # unique within theory, e.g., "expansion_ism_above_contraction"
    display_name: str                           # human-readable name

    # Source
    source_text: str                            # original English threshold + direction
    source: SourceProvenance = SourceProvenance()
    normalized_paraphrase: str = ""             # compiler's plain-English interpretation

    # The rule
    rule: Rule

    # Field metadata
    primary_field: str                          # the main field this indicator checks
    field_dependencies: list[str] = []          # all fields needed for evaluation
    field_unit: ValueUnit = ValueUnit.UNKNOWN   # unit of the primary field in the briefing
    field_semantic_type: SemanticType = SemanticType.LEVEL

    # Scoring
    weight: float                               # activation weight from theory module
    exclusion_policy: ExclusionPolicy = ExclusionPolicy.SCORE_IF_EVALUABLE

    # Compilation quality
    compilation_status: CompilationStatus = CompilationStatus.CLEAN
    ambiguities: list[AmbiguityRecord] = []
    compiler_warnings: list[str] = []
    requires_time_series: bool = False          # True if rule needs historical data


# ---------------------------------------------------------------------------
# Compiled phase
# ---------------------------------------------------------------------------

class CompiledPhase(BaseModel):
    """All compiled indicators for one activation phase."""
    phase_id: str                               # "single", "expansion", "contraction", etc.
    phase_label: str                            # human-readable label
    indicators: list[CompiledIndicator]
    activation_threshold: float = 0.60          # score >= this -> Active
    adjacent_threshold: float = 0.30            # score >= this -> Adjacent


# ---------------------------------------------------------------------------
# Compiler metadata
# ---------------------------------------------------------------------------

class CompilerMetadata(BaseModel):
    """Metadata about how this artifact was produced."""
    model_config = {"protected_namespaces": ()}

    compiler_engine: str = "haiku"              # which compiler produced this
    model_id: str = ""                          # e.g., "claude-haiku-4-5-20251001"
    schema_version: int = 1                     # artifact schema version
    prompt_version: str = ""                    # version of the compilation prompt
    compiled_at: str = ""                       # ISO timestamp
    compilation_duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Source package reference
# ---------------------------------------------------------------------------

class SourcePackageRef(BaseModel):
    """Reference to the source theory package that was compiled."""
    theory_id: str
    package_version: int = 1
    source_hash: str = ""                       # hash of the activation section
    activation_file: str = ""                   # relative path to ACTIVATION.md


# ---------------------------------------------------------------------------
# Validation summary (attached after validation, not during compilation)
# ---------------------------------------------------------------------------

class ValidationSummary(BaseModel):
    """Summary of deterministic validation results.

    Attached to the artifact after the validator runs.
    Only artifacts with status=PASS are eligible for runtime use.
    """
    status: ValidationStatus = ValidationStatus.FAIL
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    errors: list[str] = []
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# Top-level artifact
# ---------------------------------------------------------------------------

class CompiledActivationArtifact(BaseModel):
    """The complete compiled activation artifact for one theory.

    This is the top-level object that gets serialized and checked
    into the repo as the machine contract for a theory's activation
    semantics.

    Lifecycle:
      1. Compiler produces artifact with status=DRAFT
      2. Validator runs -> validation populated
      3. Human reviews -> status becomes APPROVED or REJECTED
      4. Runtime loads only APPROVED artifacts
    """
    # Schema
    schema_version: int = 1
    artifact_type: str = "compiled_activation"

    # Status
    artifact_status: ArtifactStatus = ArtifactStatus.DRAFT
    approval_timestamp: Optional[str] = None
    approval_justification: Optional[str] = None

    # Source
    source: SourcePackageRef

    # Compiler
    compiler: CompilerMetadata = CompilerMetadata()

    # Theory structure
    phase_model: PhaseModel
    phases: list[CompiledPhase]

    # Validation (populated after validation pass)
    validation: ValidationSummary = ValidationSummary()

    # Aggregate stats
    total_indicators: int = 0
    clean_count: int = 0
    warning_count: int = 0
    blocked_count: int = 0

    # Top-level notes
    artifact_notes: list[str] = []
