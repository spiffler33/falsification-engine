"""v9 Phase 3.7: Generic post-compilation repairs for Haiku output.

Two structural repairs that run AFTER Haiku compilation and BEFORE
validation. Both operate only on compound rules — non-compound rules
are untouched.

Repair 1 — Prune UNRESOLVED compound clauses:
  Removes sub-rules that reference fields not in the registry or
  prefixed with "UNRESOLVED:". These are dead clauses that Haiku
  generated for fields it couldn't resolve.

Repair 2 — Remove illegal field_comparison clauses:
  Removes sub-rules where a field_comparison would fail the validator's
  semantic type comparison check. These are structurally valid rules
  but with operands from incompatible ComparisonClasses.

Both repairs:
  - Log what was removed and why in the indicator's compiler_warnings
  - Add ambiguity records describing the partial compilation
  - Set compilation_status to WARNING for repaired indicators
  - Unwrap single-clause compounds to their inner rule

Depends on: Phase 0 schemas, field_registry, units (are_comparable)
Depended on by: scripts/v9_compile_theories.py
"""
from __future__ import annotations

from backend.schemas.v9.compiled_activation import (
    AmbiguityLevel,
    AmbiguityRecord,
    CompilationStatus,
    CompiledIndicator,
    SourceProvenance,
)
from backend.schemas.v9.field_registry import FieldRegistry
from backend.schemas.v9.rules import (
    Comparator,
    CompoundRule,
    DeltaChangeRule,
    DerivedOperand,
    FieldComparisonRule,
    FieldOperand,
    HistoricalExtremeRule,
    LiteralOperand,
    NamedPatternRule,
    PersistenceRule,
    Rule,
    ScalarComparisonRule,
    TrendStateRule,
)
from backend.schemas.v9.units import SemanticType, ValueUnit, are_comparable


# ---------------------------------------------------------------------------
# Field reference extraction
# ---------------------------------------------------------------------------

def _collect_field_ids(rule: Rule) -> list[str]:
    """Recursively collect all field_ids referenced by a rule."""
    ids = []
    if isinstance(rule, ScalarComparisonRule):
        ids.append(rule.field.field_id)
    elif isinstance(rule, FieldComparisonRule):
        if isinstance(rule.left, FieldOperand):
            ids.append(rule.left.field_id)
        if isinstance(rule.right, FieldOperand):
            ids.append(rule.right.field_id)
    elif isinstance(rule, CompoundRule):
        for clause in rule.clauses:
            ids.extend(_collect_field_ids(clause))
    elif isinstance(rule, PersistenceRule):
        ids.extend(_collect_field_ids(rule.condition))
    elif isinstance(rule, TrendStateRule):
        ids.append(rule.field.field_id)
    elif isinstance(rule, HistoricalExtremeRule):
        ids.append(rule.field.field_id)
    elif isinstance(rule, DeltaChangeRule):
        ids.append(rule.field.field_id)
    elif isinstance(rule, NamedPatternRule):
        ids.extend(rule.field_dependencies)
    return ids


def _has_unresolved_or_missing(rule: Rule, registry: FieldRegistry) -> str:
    """Check if a rule references any UNRESOLVED or missing fields.

    Returns empty string if OK, or a description of the first problem found.
    """
    for fid in _collect_field_ids(rule):
        if fid.startswith("UNRESOLVED:"):
            return f"unresolved:{fid}"
        if not registry.has_field(fid):
            return f"missing:{fid}"
    return ""


# ---------------------------------------------------------------------------
# Illegal comparison detection
# ---------------------------------------------------------------------------

def _has_illegal_comparison(rule: Rule, registry: FieldRegistry) -> str:
    """Check if a rule contains an illegal semantic type comparison.

    Matches the validator's behavior exactly: only checks FieldOperand vs
    FieldOperand comparisons in field_comparison rules. DerivedOperand
    semantic types are NOT checked (the validator skips them too).

    Also checks for unregistered derived functions.
    Returns empty string if OK, or a description.
    """
    if isinstance(rule, FieldComparisonRule):
        # Semantic type check — only for FieldOperand vs FieldOperand
        left_st = _resolve_field_semantic_type(rule.left, registry)
        right_st = _resolve_field_semantic_type(rule.right, registry)
        if left_st and right_st and not are_comparable(left_st, right_st):
            return f"illegal_comparison:{left_st.value}_vs_{right_st.value}"

        # Unregistered derived function check
        if isinstance(rule.right, DerivedOperand):
            from backend.engine.v9.derived_functions import is_registered
            if not is_registered(rule.right.function_name):
                return f"unregistered_derived:{rule.right.function_name}"

    # Recurse into compound and persistence
    if isinstance(rule, CompoundRule):
        for clause in rule.clauses:
            result = _has_illegal_comparison(clause, registry)
            if result:
                return result
    if isinstance(rule, PersistenceRule):
        return _has_illegal_comparison(rule.condition, registry)

    return ""


def _resolve_field_semantic_type(operand, registry: FieldRegistry) -> SemanticType | None:
    """Get semantic type for FieldOperand only. Returns None for non-field operands.

    This matches the validator: it only resolves semantic types for FieldOperand,
    not for DerivedOperand or LiteralOperand.
    """
    if not isinstance(operand, FieldOperand):
        return None
    entry = registry.get_field(operand.field_id)
    if entry:
        return entry.semantic_type
    return operand.semantic_type


# ---------------------------------------------------------------------------
# Repair passes
# ---------------------------------------------------------------------------

def repair_indicators(
    indicators: list[CompiledIndicator],
    registry: FieldRegistry,
) -> list[dict]:
    """Run both repair passes on a list of compiled indicators.

    Modifies indicators in place. Returns a list of repair log entries.
    """
    log = []
    for ind in indicators:
        entries = _repair_single_indicator(ind, registry)
        log.extend(entries)
    return log


def _repair_single_indicator(
    ind: CompiledIndicator,
    registry: FieldRegistry,
) -> list[dict]:
    """Apply repairs to a single indicator. Returns repair log entries."""
    log = []

    if not isinstance(ind.rule, CompoundRule):
        return log

    compound = ind.rule
    original_count = len(compound.clauses)

    # --- Repair 1: prune UNRESOLVED / missing-field clauses ---
    good_clauses = []
    for clause in compound.clauses:
        problem = _has_unresolved_or_missing(clause, registry)
        if problem:
            log.append({
                "indicator_id": ind.indicator_id,
                "repair": "prune_unresolved",
                "removed_clause_type": clause.rule_type,
                "reason": problem,
            })
            ind.compiler_warnings.append(
                f"Repair: removed {clause.rule_type} clause ({problem})"
            )
        else:
            good_clauses.append(clause)

    compound.clauses = good_clauses

    # --- Repair 2: remove illegal comparison clauses ---
    if compound.clauses:
        surviving = []
        for clause in compound.clauses:
            problem = _has_illegal_comparison(clause, registry)
            if problem:
                log.append({
                    "indicator_id": ind.indicator_id,
                    "repair": "remove_illegal_comparison",
                    "removed_clause_type": clause.rule_type,
                    "reason": problem,
                })
                ind.compiler_warnings.append(
                    f"Repair: removed {clause.rule_type} clause ({problem})"
                )
            else:
                surviving.append(clause)
        compound.clauses = surviving

    # --- Post-repair: unwrap or block ---
    removed_count = original_count - len(compound.clauses)

    if removed_count == 0:
        return log

    if not compound.clauses:
        # All clauses removed — indicator is BLOCKED
        ind.compilation_status = CompilationStatus.BLOCKED
        ind.ambiguities.append(AmbiguityRecord(
            level=AmbiguityLevel.HIGH,
            description="All compound clauses removed by repair (all UNRESOLVED or illegal)",
        ))
    elif len(compound.clauses) == 1:
        # Unwrap single-clause compound to its inner rule
        ind.rule = compound.clauses[0]
        ind.compilation_status = CompilationStatus.WARNING
        ind.ambiguities.append(AmbiguityRecord(
            level=AmbiguityLevel.MEDIUM,
            description=f"Compound simplified: {removed_count} clause(s) pruned, "
                        f"1 evaluable clause retained",
        ))
    else:
        # Multiple clauses survive
        ind.compilation_status = CompilationStatus.WARNING
        ind.ambiguities.append(AmbiguityRecord(
            level=AmbiguityLevel.MEDIUM,
            description=f"Compound repaired: {removed_count} clause(s) pruned, "
                        f"{len(compound.clauses)} retained",
        ))

    return log


# ---------------------------------------------------------------------------
# Repair 3 — Inject missing indicators
# ---------------------------------------------------------------------------

# Known indicators that Haiku systematically drops.
# Keyed by (theory_id, indicator_name) → CompiledIndicator constructor kwargs.
_KNOWN_MISSING: dict[tuple[str, str], dict] = {
    ("structural_fragility", "Implied-realized vol gap"): {
        "indicator_id": "implied_realized_vol_gap",
        "display_name": "Implied-realized vol gap",
        "source_text": "Above 5 points",
        "source": SourceProvenance(file="", section="", line_range=""),
        "normalized_paraphrase": "VIX minus 20-day realized vol above 5 points",
        "rule": ScalarComparisonRule(
            rule_type="scalar_comparison",
            field=FieldOperand(
                operand_type="field",
                field_id="vix_vs_realized",
                unit=ValueUnit.INDEX_POINTS,
                semantic_type=SemanticType.SPREAD,
            ),
            comparator=Comparator.GT,
            threshold=LiteralOperand(
                operand_type="literal",
                value=5.0,
                unit=ValueUnit.INDEX_POINTS,
            ),
        ),
        "primary_field": "vix_vs_realized",
        "field_dependencies": [],
        "field_unit": ValueUnit.UNKNOWN,
        "field_semantic_type": SemanticType.LEVEL,
        "weight": 0.10,
        "exclusion_policy": "score_if_evaluable",
        "compilation_status": CompilationStatus.WARNING,
        "ambiguities": [AmbiguityRecord(
            level=AmbiguityLevel.MEDIUM,
            description="Injected by repair: Haiku systematically drops this computed indicator",
        )],
        "compiler_warnings": ["Repair: injected missing indicator (Haiku dropped it)"],
        "requires_time_series": False,
    },
}


def repair_missing_indicators(
    indicators: list[CompiledIndicator],
    parsed_indicators: list[dict],
    theory_id: str,
    phase_id: str,
) -> list[dict]:
    """Detect and inject indicators that Haiku systematically drops.

    Compares the parsed indicator names from ACTIVATION.md against the
    compiled indicator display_names. For known-missing cases, injects
    a deterministic compiled indicator from the _KNOWN_MISSING registry.

    Returns a list of repair log entries.
    """
    compiled_names = {ind.display_name for ind in indicators}
    parsed_names = {ind["indicator_name"] for ind in parsed_indicators}

    missing = parsed_names - compiled_names
    if not missing:
        return []

    log = []
    for name in sorted(missing):
        key = (theory_id, name)
        if key in _KNOWN_MISSING:
            kwargs = dict(_KNOWN_MISSING[key])
            ci = CompiledIndicator(**kwargs)
            indicators.append(ci)
            log.append({
                "indicator_id": kwargs["indicator_id"],
                "repair": "inject_missing",
                "reason": f"Haiku dropped '{name}'; injected from known-missing registry",
            })
        else:
            log.append({
                "indicator_id": f"MISSING:{name}",
                "repair": "detect_missing",
                "reason": f"Haiku dropped '{name}' but no known-missing entry exists",
            })

    return log
