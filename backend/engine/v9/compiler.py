"""v9 Phase 2: Haiku compiler adapter targeting Phase 0 canonical schema.

Compiles English activation indicator descriptions into CompiledActivationArtifact
objects conforming to the Phase 0 schema (discriminated union Rule types).

Two modes:
  1. Haiku mode: sends theory activation text to Claude Haiku API
  2. Artifact mode: loads pre-compiled artifacts from disk

The compiler only does compilation (English -> structured rules).
It does NOT do runtime evaluation. That is the evaluator's job.

Depends on: Phase 0 contracts (schemas/v9/)
Depended on by: compile_all.py, scripts/v9_phase2_compile.py
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

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
    ValidationSummary,
)
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
)
from backend.schemas.v9.units import SemanticType, TimeWindow, TimeUnit, ValueUnit


# ---------------------------------------------------------------------------
# Artifact storage paths
# ---------------------------------------------------------------------------

ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "v9"
PROMPT_VERSION = "phase2_v1"
SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Rule builder helpers — construct Phase 0 schema rules from specs
# ---------------------------------------------------------------------------

def _field(field_id: str, unit: ValueUnit = ValueUnit.UNKNOWN,
           semantic_type: SemanticType = SemanticType.LEVEL) -> FieldOperand:
    return FieldOperand(field_id=field_id, unit=unit, semantic_type=semantic_type)


def _lit(value: float, unit: ValueUnit = ValueUnit.DIMENSIONLESS) -> LiteralOperand:
    return LiteralOperand(value=value, unit=unit)


def _window(value: int, unit: TimeUnit = TimeUnit.MONTHS) -> TimeWindow:
    return TimeWindow(value=value, unit=unit)


def scalar(field_id: str, cmp: str, value: float,
           field_unit: ValueUnit = ValueUnit.UNKNOWN,
           threshold_unit: ValueUnit = ValueUnit.DIMENSIONLESS,
           semantic_type: SemanticType = SemanticType.LEVEL) -> ScalarComparisonRule:
    """Build a scalar_comparison rule."""
    return ScalarComparisonRule(
        field=_field(field_id, field_unit, semantic_type),
        comparator=Comparator(cmp),
        threshold=_lit(value, threshold_unit),
    )


def field_cmp(left_id: str, cmp: str, right_id: str = "",
              derived_fn: str = "", offset: float = 0.0,
              left_unit: ValueUnit = ValueUnit.UNKNOWN,
              right_unit: ValueUnit = ValueUnit.UNKNOWN,
              left_st: SemanticType = SemanticType.LEVEL,
              right_st: SemanticType = SemanticType.LEVEL) -> FieldComparisonRule:
    """Build a field_comparison rule."""
    left = _field(left_id, left_unit, left_st)
    if derived_fn:
        right: Any = DerivedOperand(
            function_name=derived_fn, arguments=[right_id] if right_id else [],
            unit=right_unit, semantic_type=right_st,
        )
    else:
        right = _field(right_id, right_unit, right_st)
    return FieldComparisonRule(
        left=left, comparator=Comparator(cmp), right=right,
        offset=_lit(offset) if offset != 0.0 else None,
    )


def trend(field_id: str, direction: str, window_val: int = 3,
          window_unit: TimeUnit = TimeUnit.MONTHS,
          field_unit: ValueUnit = ValueUnit.UNKNOWN) -> TrendStateRule:
    """Build a trend_state rule."""
    return TrendStateRule(
        field=_field(field_id, field_unit),
        direction=TrendDirection(direction),
        window=_window(window_val, window_unit),
    )


def persistence(condition: Rule, n: int, k: Optional[int] = None,
                window_val: int = 3, window_unit: TimeUnit = TimeUnit.MONTHS,
                mode: str = "n_of_last_k") -> PersistenceRule:
    """Build a persistence rule."""
    return PersistenceRule(
        condition=condition,
        mode=PersistenceMode(mode),
        n=n, k=k,
        window=_window(window_val, window_unit),
    )


def historical_extreme(field_id: str, extreme: str, lookback_val: int,
                       lookback_unit: TimeUnit = TimeUnit.MONTHS,
                       cmp: str = "gt",
                       margin: float = 0.0,
                       field_unit: ValueUnit = ValueUnit.UNKNOWN) -> HistoricalExtremeRule:
    """Build a historical_extreme rule."""
    return HistoricalExtremeRule(
        field=_field(field_id, field_unit),
        extreme=ExtremeType(extreme),
        lookback=_window(lookback_val, lookback_unit),
        comparator=Comparator(cmp),
        margin=_lit(margin) if margin > 0 else None,
    )


def compound_all(*rules: Rule) -> CompoundRule:
    """Build a compound AND rule."""
    return CompoundRule(operator=CompoundOperator.ALL, clauses=list(rules))


def compound_any(*rules: Rule) -> CompoundRule:
    """Build a compound OR rule."""
    return CompoundRule(operator=CompoundOperator.ANY, clauses=list(rules))


def named_pattern(name: str, params: dict = None,
                  deps: list[str] = None) -> NamedPatternRule:
    """Build a named_pattern rule."""
    return NamedPatternRule(
        name=name, params=params or {}, field_dependencies=deps or [],
    )


def delta_change(field_id: str, direction: str, magnitude: float,
                 mode: str = "absolute", window_val: int = 60,
                 window_unit: TimeUnit = TimeUnit.DAYS,
                 mag_unit: ValueUnit = ValueUnit.USD_BILLIONS,
                 field_unit: ValueUnit = ValueUnit.UNKNOWN) -> DeltaChangeRule:
    """Build a delta_change rule."""
    return DeltaChangeRule(
        field=_field(field_id, field_unit),
        direction=TrendDirection(direction),
        magnitude=_lit(magnitude, mag_unit),
        mode=DeltaMode(mode),
        window=_window(window_val, window_unit),
    )


# ---------------------------------------------------------------------------
# Indicator builder
# ---------------------------------------------------------------------------

def make_indicator(
    indicator_id: str,
    display_name: str,
    source_text: str,
    rule: Rule,
    primary_field: str,
    weight: float,
    field_unit: ValueUnit = ValueUnit.UNKNOWN,
    field_semantic_type: SemanticType = SemanticType.LEVEL,
    field_dependencies: list[str] = None,
    exclusion_policy: ExclusionPolicy = ExclusionPolicy.SCORE_IF_EVALUABLE,
    compilation_status: CompilationStatus = CompilationStatus.CLEAN,
    ambiguities: list[AmbiguityRecord] = None,
    warnings: list[str] = None,
    requires_time_series: bool = False,
    paraphrase: str = "",
) -> CompiledIndicator:
    """Build a CompiledIndicator."""
    return CompiledIndicator(
        indicator_id=indicator_id,
        display_name=display_name,
        source_text=source_text,
        normalized_paraphrase=paraphrase or source_text,
        rule=rule,
        primary_field=primary_field,
        field_dependencies=field_dependencies or [],
        field_unit=field_unit,
        field_semantic_type=field_semantic_type,
        weight=weight,
        exclusion_policy=exclusion_policy,
        compilation_status=compilation_status,
        ambiguities=ambiguities or [],
        compiler_warnings=warnings or [],
        requires_time_series=requires_time_series,
    )


# ---------------------------------------------------------------------------
# Artifact builder
# ---------------------------------------------------------------------------

def make_artifact(
    theory_id: str,
    phase_model: PhaseModel,
    phases: list[CompiledPhase],
    source_file: str = "",
    notes: list[str] = None,
) -> CompiledActivationArtifact:
    """Build a CompiledActivationArtifact."""
    total = sum(len(p.indicators) for p in phases)
    clean = sum(
        1 for p in phases for i in p.indicators
        if i.compilation_status == CompilationStatus.CLEAN
    )
    blocked = sum(
        1 for p in phases for i in p.indicators
        if i.compilation_status == CompilationStatus.BLOCKED
    )
    warning = total - clean - blocked

    return CompiledActivationArtifact(
        schema_version=SCHEMA_VERSION,
        artifact_status=ArtifactStatus.DRAFT,
        source=SourcePackageRef(
            theory_id=theory_id,
            package_version=2,
            activation_file=source_file or f"theories/THEORY_MODULE_{theory_id.upper()}_v2/ACTIVATION.md",
        ),
        compiler=CompilerMetadata(
            compiler_engine="haiku_phase2",
            model_id="claude-haiku-4-5-20251001",
            schema_version=SCHEMA_VERSION,
            prompt_version=PROMPT_VERSION,
            compiled_at=datetime.now(timezone.utc).isoformat(),
        ),
        phase_model=phase_model,
        phases=phases,
        total_indicators=total,
        clean_count=clean,
        warning_count=warning,
        blocked_count=blocked,
        artifact_notes=notes or [],
    )


def make_phase(phase_id: str, phase_label: str,
               indicators: list[CompiledIndicator]) -> CompiledPhase:
    """Build a CompiledPhase."""
    return CompiledPhase(
        phase_id=phase_id,
        phase_label=phase_label,
        indicators=indicators,
    )


# ---------------------------------------------------------------------------
# Artifact I/O
# ---------------------------------------------------------------------------

def save_artifact(artifact: CompiledActivationArtifact, path: Path = None) -> Path:
    """Serialize a compiled artifact to JSON."""
    if path is None:
        path = ARTIFACTS_DIR / f"{artifact.source.theory_id}.compiled.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(artifact.model_dump_json(indent=2))
    return path


def load_artifact(theory_id: str, path: Path = None) -> CompiledActivationArtifact:
    """Load a compiled artifact from JSON."""
    if path is None:
        path = ARTIFACTS_DIR / f"{theory_id}.compiled.json"
    data = json.loads(path.read_text())
    return CompiledActivationArtifact(**data)


def load_all_artifacts(
    artifacts_dir: Path = None,
) -> dict[str, CompiledActivationArtifact]:
    """Load all compiled artifacts from a directory."""
    d = artifacts_dir or ARTIFACTS_DIR
    results = {}
    for p in sorted(d.glob("*.compiled.json")):
        theory_id = p.stem.replace(".compiled", "")
        results[theory_id] = load_artifact(theory_id, p)
    return results


# ---------------------------------------------------------------------------
# Haiku compiler adapter (live compilation via API)
# ---------------------------------------------------------------------------

COMPILER_SYSTEM_PROMPT = """\
You are a semantic compiler. Your job is to translate English activation indicator \
descriptions into deterministic machine-readable rule objects conforming to the v9 schema.

You are NOT reasoning about markets. You are doing precise English-to-structured-data \
translation.

## Rule types

1. **scalar_comparison**: field vs literal.
   {{"rule_type":"scalar_comparison","field":{{"field_id":"...","unit":"...","semantic_type":"..."}},\
"comparator":"gt|gte|lt|lte|eq","threshold":{{"value":N,"unit":"..."}}}}

2. **field_comparison**: field vs field or derived.
   {{"rule_type":"field_comparison","left":{{"operand_type":"field","field_id":"..."}},\
"comparator":"...","right":{{"operand_type":"field"|"derived","field_id":"..."|"function_name":"..."}}}}

3. **compound**: boolean all/any of sub-rules.
   {{"rule_type":"compound","operator":"all"|"any","clauses":[...rules...]}}

4. **trend_state**: directional trend.
   {{"rule_type":"trend_state","field":{{"field_id":"..."}},\
"direction":"rising"|"falling"|"stable","window":{{"value":N,"unit":"months"|"weeks"|...}}}}

5. **persistence**: n-of-last-k or consecutive.
   {{"rule_type":"persistence","condition":{{...rule...}},"mode":"n_of_last_k"|"consecutive",\
"n":N,"k":K,"window":{{"value":N,"unit":"..."}}}}

6. **historical_extreme**: above/below N-period high/low.
   {{"rule_type":"historical_extreme","field":{{"field_id":"..."}},\
"extreme":"high"|"low","lookback":{{"value":N,"unit":"..."}},\
"comparator":"gt"|"lt"}}

7. **named_pattern**: well-known statistical patterns.
   {{"rule_type":"named_pattern","name":"sahm_rule"|"resteepened_after_inversion",\
"params":{{...}},"field_dependencies":[...]}}

8. **delta_change**: absolute/percent change over window.
   {{"rule_type":"delta_change","field":{{"field_id":"..."}},\
"direction":"rising"|"falling","magnitude":{{"value":N,"unit":"..."}},\
"mode":"absolute"|"percent","window":{{"value":N,"unit":"..."}}}}

## Available fields
{known_fields}

## Output format
For each indicator, emit:
```json
{{
  "indicator_id": "snake_case_id",
  "display_name": "Human Readable Name",
  "source_text": "original threshold text",
  "paraphrase": "compiler's interpretation",
  "rule": {{ ... typed rule ... }},
  "primary_field": "field_id",
  "field_dependencies": ["field_id", ...],
  "weight": 0.XX,
  "compilation_status": "clean"|"warning"|"blocked",
  "ambiguity_level": "none"|"low"|"medium"|"high",
  "ambiguity_notes": "...",
  "requires_time_series": true|false,
  "warnings": ["..."]
}}
```

## Rules
1. NEVER GUESS. If ambiguous, set ambiguity_level=medium/high.
2. Combine scalar+temporal as compound(all,[scalar, trend/persistence]).
3. "X vs Y" or "X below Y growth" = field_comparison or derived.
4. Map to known fields. Unknown = "UNRESOLVED:original text", blocked.
5. Units explicit: "300bp"=basis_points, "1.0%"=percent, "$500B"=usd_billions.
6. Temporal rules require time_series=true.
7. Canonical output unit is PERCENT, not SHARE.

Return a JSON array. No markdown, no explanation.
"""


class HaikuCompilerAdapter:
    """Calls Haiku API to compile theory activation text into Phase 0 artifacts.

    Usage:
        compiler = HaikuCompilerAdapter(api_key="...")
        artifact = compiler.compile_theory(theory_id, activation_entries, is_two_phase)
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = None
        self.model = "claude-haiku-4-5-20251001"
        self.stats = {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                      "latencies": [], "errors": 0}

    @property
    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def compile_theory(
        self,
        theory_id: str,
        activation_entries: list[dict],
        is_two_phase: bool = False,
    ) -> CompiledActivationArtifact:
        """Compile a theory's activation entries via Haiku."""
        from backend.engine.v9.registry_builder import build_full_registry
        registry = build_full_registry()
        known_fields = [f.field_id for f in registry._fields.values()]

        phase_groups: dict[str, list[dict]] = {}
        for entry in activation_entries:
            phase = entry.get("phase") or "single"
            phase_groups.setdefault(phase, []).append(entry)

        compiled_phases = []
        for phase_key, entries in sorted(phase_groups.items()):
            indicators, stats = self._compile_batch(
                entries, theory_id, phase_key, known_fields,
            )
            phase_id, phase_label = _parse_phase_key(phase_key, is_two_phase)
            compiled_phases.append(make_phase(phase_id, phase_label, indicators))

        phase_model = PhaseModel.TWO_PHASE if is_two_phase else PhaseModel.SINGLE_PHASE
        return make_artifact(theory_id, phase_model, compiled_phases)

    def _compile_batch(
        self,
        entries: list[dict],
        theory_id: str,
        phase_key: str,
        known_fields: list[str],
    ) -> tuple[list[CompiledIndicator], dict]:
        """Compile a batch of indicators via a single Haiku call."""
        prompt_lines = [
            f"Theory: {theory_id}, Phase: {phase_key}",
            f"Compile these {len(entries)} indicators:",
            "",
        ]
        for e in entries:
            prompt_lines.extend([
                f"---",
                f"Indicator: {e['indicator_name']}",
                f"Metric Source: {e['metric_source']}",
                f"Threshold: {e['threshold']}",
                f"Direction: {e['direction']}",
                f"Weight: {e['weight']}",
                "",
            ])

        system = COMPILER_SYSTEM_PROMPT.format(
            known_fields="\n".join(f"- {f}" for f in known_fields)
        )

        t0 = time.time()
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                temperature=0.0,
                system=system,
                messages=[{"role": "user", "content": "\n".join(prompt_lines)}],
            )
            latency = time.time() - t0
            self.stats["calls"] += 1
            self.stats["input_tokens"] += response.usage.input_tokens
            self.stats["output_tokens"] += response.usage.output_tokens
            self.stats["latencies"].append(latency)

            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw = "\n".join(lines)

            items = json.loads(raw)
        except Exception as e:
            self.stats["errors"] += 1
            return [], {"error": str(e)}

        # Parse into CompiledIndicator objects
        weight_lookup = {e["indicator_name"]: float(e["weight"]) for e in entries}
        indicators = []
        for item in items:
            try:
                ind = _parse_haiku_indicator(item, weight_lookup)
                indicators.append(ind)
            except Exception as e:
                indicators.append(make_indicator(
                    indicator_id=item.get("indicator_id", "parse_error"),
                    display_name=item.get("display_name", "Parse Error"),
                    source_text=str(item),
                    rule=scalar("UNRESOLVED:parse_error", "gt", 0),
                    primary_field="UNRESOLVED:parse_error",
                    weight=0.1,
                    compilation_status=CompilationStatus.BLOCKED,
                    warnings=[f"Parse error: {e}"],
                ))

        return indicators, {"latency_s": latency if "latency" in dir() else 0}


def _parse_phase_key(phase_key: str, is_two_phase: bool) -> tuple[str, str]:
    """Parse a phase key into (phase_id, phase_label)."""
    if not is_two_phase or phase_key == "single":
        return "single", "Active"
    import re
    m = re.search(r"Phase\s*([AB])\s*:\s*(.+)", phase_key, re.IGNORECASE)
    if m:
        letter = m.group(1).upper()
        label = m.group(2).strip()
        return f"phase_{letter.lower()}", label
    return phase_key.lower().replace(" ", "_"), phase_key


def _parse_haiku_indicator(item: dict, weight_lookup: dict) -> CompiledIndicator:
    """Parse a Haiku output item into a CompiledIndicator."""
    rule = _parse_rule_recursive(item["rule"])
    name = item.get("display_name", item.get("indicator_id", ""))
    weight = weight_lookup.get(name, item.get("weight", 0.1))

    ambiguity_level = AmbiguityLevel(item.get("ambiguity_level", "none"))
    ambiguities = []
    if ambiguity_level != AmbiguityLevel.NONE:
        ambiguities.append(AmbiguityRecord(
            level=ambiguity_level,
            description=item.get("ambiguity_notes", ""),
        ))

    status = CompilationStatus(item.get("compilation_status", "clean"))

    return make_indicator(
        indicator_id=item.get("indicator_id", ""),
        display_name=name,
        source_text=item.get("source_text", ""),
        rule=rule,
        primary_field=item.get("primary_field", ""),
        weight=weight,
        compilation_status=status,
        ambiguities=ambiguities,
        warnings=item.get("warnings", []),
        requires_time_series=item.get("requires_time_series", False),
        paraphrase=item.get("paraphrase", ""),
    )


def _parse_rule_recursive(data: dict) -> Rule:
    """Recursively parse a rule dict into a typed Rule."""
    rt = data.get("rule_type", "scalar_comparison")

    if rt == "scalar_comparison":
        f = data.get("field", {})
        t = data.get("threshold", {})
        return ScalarComparisonRule(
            field=FieldOperand(
                field_id=f.get("field_id", ""),
                unit=ValueUnit(f.get("unit", "unknown")),
                semantic_type=SemanticType(f.get("semantic_type", "level")),
            ),
            comparator=Comparator(data.get("comparator", "gt")),
            threshold=LiteralOperand(
                value=float(t.get("value", 0)),
                unit=ValueUnit(t.get("unit", "dimensionless")),
            ),
        )
    elif rt == "field_comparison":
        left = _parse_operand(data.get("left", {}))
        right = _parse_operand(data.get("right", {}))
        offset = None
        if data.get("offset"):
            offset = LiteralOperand(
                value=float(data["offset"].get("value", 0)),
                unit=ValueUnit(data["offset"].get("unit", "dimensionless")),
            )
        return FieldComparisonRule(
            left=left, comparator=Comparator(data.get("comparator", "lt")),
            right=right, offset=offset,
        )
    elif rt == "compound":
        clauses = [_parse_rule_recursive(c) for c in data.get("clauses", [])]
        return CompoundRule(
            operator=CompoundOperator(data.get("operator", "all")),
            clauses=clauses,
        )
    elif rt == "trend_state":
        f = data.get("field", {})
        w = data.get("window", {})
        return TrendStateRule(
            field=FieldOperand(field_id=f.get("field_id", "")),
            direction=TrendDirection(data.get("direction", "rising")),
            window=TimeWindow(
                value=int(w.get("value", 3)),
                unit=TimeUnit(w.get("unit", "months")),
            ),
        )
    elif rt == "persistence":
        cond = _parse_rule_recursive(data.get("condition", {}))
        w = data.get("window", {})
        return PersistenceRule(
            condition=cond,
            mode=PersistenceMode(data.get("mode", "n_of_last_k")),
            n=int(data.get("n", 1)),
            k=int(data.get("k")) if data.get("k") is not None else None,
            window=TimeWindow(
                value=int(w.get("value", 3)),
                unit=TimeUnit(w.get("unit", "months")),
            ),
        )
    elif rt == "historical_extreme":
        f = data.get("field", {})
        lb = data.get("lookback", {})
        margin = None
        if data.get("margin"):
            margin = LiteralOperand(value=float(data["margin"].get("value", 0)))
        return HistoricalExtremeRule(
            field=FieldOperand(field_id=f.get("field_id", "")),
            extreme=ExtremeType(data.get("extreme", "high")),
            lookback=TimeWindow(
                value=int(lb.get("value", 12)),
                unit=TimeUnit(lb.get("unit", "months")),
            ),
            comparator=Comparator(data.get("comparator", "gt")),
            margin=margin,
        )
    elif rt == "named_pattern":
        return NamedPatternRule(
            name=data.get("name", ""),
            params=data.get("params", {}),
            field_dependencies=data.get("field_dependencies", []),
        )
    elif rt == "delta_change":
        f = data.get("field", {})
        m = data.get("magnitude", {})
        w = data.get("window", {})
        return DeltaChangeRule(
            field=FieldOperand(field_id=f.get("field_id", "")),
            direction=TrendDirection(data.get("direction", "falling")),
            magnitude=LiteralOperand(
                value=float(m.get("value", 0)),
                unit=ValueUnit(m.get("unit", "dimensionless")),
            ),
            mode=DeltaMode(data.get("mode", "absolute")),
            window=TimeWindow(
                value=int(w.get("value", 60)),
                unit=TimeUnit(w.get("unit", "days")),
            ),
        )
    else:
        return ScalarComparisonRule(
            field=FieldOperand(field_id="UNRESOLVED:" + rt),
            comparator=Comparator.GT,
            threshold=LiteralOperand(value=0),
        )


def _parse_operand(data: dict):
    """Parse an operand from Haiku output."""
    ot = data.get("operand_type", "field")
    if ot == "derived":
        return DerivedOperand(
            function_name=data.get("function_name", ""),
            arguments=data.get("arguments", []),
            unit=ValueUnit(data.get("unit", "unknown")),
            semantic_type=SemanticType(data.get("semantic_type", "level")),
        )
    elif ot == "literal":
        return LiteralOperand(
            value=float(data.get("value", 0)),
            unit=ValueUnit(data.get("unit", "dimensionless")),
        )
    else:
        return FieldOperand(
            field_id=data.get("field_id", ""),
            unit=ValueUnit(data.get("unit", "unknown")),
            semantic_type=SemanticType(data.get("semantic_type", "level")),
        )
