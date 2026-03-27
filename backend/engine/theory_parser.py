# theory_parser.py — Parse theory module markdown files into structured Python objects.
# Depends on: backend/schemas/theory.py, backend/config.py (THEORIES_DIR)
# Depended on by: engine/activation.py, engine/prompt_builder.py, api/theories.py
#
# Strategy: section-header driven parsing. We split the markdown by ## headers,
# then parse tables within each section using column-header detection.
# This handles column-order variations (e.g. Severity position in soft falsifiers)
# and supports N modules without hardcoding.
from __future__ import annotations

import json
import re
from pathlib import Path

from backend.config import THEORIES_DIR
from backend.schemas.theory import (
    ActivationPhase,
    ConditionalPrediction,
    Direction,
    DirectionalPrediction,
    DownstreamEffect,
    HardFalsifier,
    Indicator,
    Severity,
    SoftFalsifier,
    TheoryMetadata,
    TheoryModule,
)


def load_all_theories(theories_dir: Path | None = None) -> list[TheoryModule]:
    """Load and parse all theory modules from the theories directory."""
    d = theories_dir or THEORIES_DIR
    modules = []
    for path in sorted(d.glob("THEORY_MODULE_*.md")):
        module = parse_theory_module(path)
        if module:
            modules.append(module)
    return modules


def parse_theory_module(path: Path) -> TheoryModule | None:
    """Parse a single theory module markdown file into a TheoryModule."""
    text = path.read_text(encoding="utf-8")
    sections = _split_sections(text)

    # Extract theory_id
    theory_id = _extract_theory_id(sections)
    if not theory_id:
        return None

    # Extract title from first line
    title = ""
    first_line = text.strip().split("\n")[0]
    if first_line.startswith("# "):
        title = first_line[2:].strip()

    # Detect two-phase
    activation_text = sections.get("activation_conditions", "")
    is_two_phase = "### Phase A:" in activation_text or "### Phase A " in activation_text

    # Parse activation phases
    phases = _parse_activation_phases(activation_text, is_two_phase)

    # Parse falsifiers
    falsifier_text = sections.get("falsifiers", "")
    hard_falsifiers = _parse_hard_falsifiers(falsifier_text)
    soft_falsifiers = _parse_soft_falsifiers(falsifier_text)

    # Parse predictions
    predictions_text = sections.get("predictions_when_active", "")
    directional = _parse_directional_predictions(predictions_text)
    conditional = _parse_conditional_predictions(predictions_text)

    # Parse downstream implications
    downstream_text = sections.get("downstream_implications", "")
    downstream = _parse_downstream_effects(downstream_text)

    # Parse metadata
    metadata_text = sections.get("metadata", "")
    metadata = _parse_metadata(metadata_text)

    # Scope limits
    scope_text = sections.get("scope_limits", "")

    return TheoryModule(
        theory_id=theory_id,
        title=title,
        is_two_phase=is_two_phase,
        phases=phases,
        hard_falsifiers=hard_falsifiers,
        soft_falsifiers=soft_falsifiers,
        directional_predictions=directional,
        conditional_predictions=conditional,
        downstream_effects=downstream,
        metadata=metadata,
        scope_limits=scope_text.strip(),
        raw_markdown=text,
    )


# ---------------------------------------------------------------------------
# Section splitting
# ---------------------------------------------------------------------------

def _split_sections(text: str) -> dict[str, str]:
    """Split markdown into sections by ## headers. Returns {header_slug: content}."""
    sections: dict[str, str] = {}
    current_key = ""
    current_lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith("## ") and not line.startswith("### "):
            if current_key:
                sections[current_key] = "\n".join(current_lines)
            # Normalize header to snake_case slug
            header = line[3:].strip()
            current_key = _slugify(header)
            current_lines = []
        else:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines)

    return sections


def _slugify(header: str) -> str:
    """Convert a section header to a slug for dict keys."""
    s = header.lower().strip()
    s = re.sub(r"[^a-z0-9\s_]", "", s)
    s = re.sub(r"\s+", "_", s)
    return s


# ---------------------------------------------------------------------------
# Theory ID extraction
# ---------------------------------------------------------------------------

def _extract_theory_id(sections: dict[str, str]) -> str:
    """Extract theory_id from the theory_id section (backtick-wrapped)."""
    text = sections.get("theory_id", "")
    m = re.search(r"`([a-z_]+)`", text)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Table parsing utilities
# ---------------------------------------------------------------------------

def _parse_table(text: str) -> list[dict[str, str]]:
    """Parse a markdown table into a list of row dicts keyed by header names.

    Handles the pipe-delimited format:
    | Header1 | Header2 | ...
    |---------|---------|----
    | val1    | val2    | ...
    """
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

    # Find table lines (start with |)
    table_lines = [l for l in lines if l.startswith("|")]
    if len(table_lines) < 3:  # need header + separator + at least 1 row
        return []

    # Parse header
    header_line = table_lines[0]
    headers = [h.strip().strip("*").strip() for h in header_line.split("|")[1:-1]]
    headers = [h for h in headers if h]  # remove empty

    if not headers:
        return []

    # Skip separator line (index 1), parse data rows
    rows = []
    for row_line in table_lines[2:]:
        cells = [c.strip() for c in row_line.split("|")[1:-1]]
        if len(cells) >= len(headers):
            row = {headers[i]: cells[i] for i in range(len(headers))}
            rows.append(row)
        elif cells:
            # Fewer cells than headers — pad with empty
            row = {}
            for i, h in enumerate(headers):
                row[h] = cells[i] if i < len(cells) else ""
            rows.append(row)

    return rows


def _find_table_after_header(text: str, header_pattern: str) -> str:
    """Find the markdown table block that follows a ### header matching the pattern."""
    lines = text.split("\n")
    in_section = False
    table_lines: list[str] = []
    collecting = False

    for line in lines:
        stripped = line.strip()
        if re.match(header_pattern, stripped, re.IGNORECASE):
            in_section = True
            collecting = False
            table_lines = []
            continue

        if in_section:
            # Stop at the next ### header
            if stripped.startswith("### ") or stripped.startswith("## "):
                if table_lines:
                    break
                in_section = False
                continue

            if stripped.startswith("|"):
                collecting = True
                table_lines.append(stripped)
            elif collecting and not stripped.startswith("|") and stripped:
                # Non-table non-empty line after table started — table ended
                break

    return "\n".join(table_lines)


def _find_all_tables(text: str) -> list[str]:
    """Find all contiguous table blocks in a text section."""
    lines = text.split("\n")
    tables: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            current.append(stripped)
        else:
            if current:
                tables.append("\n".join(current))
                current = []
    if current:
        tables.append("\n".join(current))

    return tables


# ---------------------------------------------------------------------------
# Activation condition parsing
# ---------------------------------------------------------------------------

def _parse_activation_phases(text: str, is_two_phase: bool) -> list[ActivationPhase]:
    """Parse activation conditions into phases with indicators."""
    if not text.strip():
        return []

    if is_two_phase:
        return _parse_two_phase_activation(text)
    else:
        return _parse_single_phase_activation(text)


def _parse_single_phase_activation(text: str) -> list[ActivationPhase]:
    """Parse activation for a single-phase theory."""
    tables = _find_all_tables(text)
    # The first table with indicator-like columns is the activation table
    for table_text in tables:
        rows = _parse_table(table_text)
        if rows and _looks_like_indicator_table(rows[0]):
            indicators = [_row_to_indicator(r) for r in rows]
            return [ActivationPhase(
                phase_name="single",
                phase_label="Active",
                indicators=[i for i in indicators if i is not None],
            )]
    return []


def _parse_two_phase_activation(text: str) -> list[ActivationPhase]:
    """Parse activation for a two-phase theory. Phase B checked first per spec."""
    phases: list[ActivationPhase] = []

    # Find Phase A and Phase B subsections
    phase_a_match = re.search(r"###\s*Phase\s*A[:\s]+(.+?)(?=\n)", text)
    phase_b_match = re.search(r"###\s*Phase\s*B[:\s]+(.+?)(?=\n)", text)

    phase_a_label = phase_a_match.group(1).strip() if phase_a_match else "Phase A"
    phase_b_label = phase_b_match.group(1).strip() if phase_b_match else "Phase B"

    # Split text at Phase B header
    phase_split = re.split(r"###\s*Phase\s*B", text, maxsplit=1)
    phase_a_text = phase_split[0] if phase_split else ""
    phase_b_text = phase_split[1] if len(phase_split) > 1 else ""

    # Parse Phase A indicators
    phase_a_indicators = _extract_indicators_from_section(phase_a_text)
    if phase_a_indicators:
        phases.append(ActivationPhase(
            phase_name="phase_a",
            phase_label=phase_a_label,
            indicators=phase_a_indicators,
        ))

    # Parse Phase B indicators
    phase_b_indicators = _extract_indicators_from_section(phase_b_text)
    if phase_b_indicators:
        phases.append(ActivationPhase(
            phase_name="phase_b",
            phase_label=phase_b_label,
            indicators=phase_b_indicators,
        ))

    return phases


def _extract_indicators_from_section(text: str) -> list[Indicator]:
    """Extract indicators from all tables in a section that look like indicator tables."""
    indicators: list[Indicator] = []
    tables = _find_all_tables(text)
    for table_text in tables:
        rows = _parse_table(table_text)
        if rows and _looks_like_indicator_table(rows[0]):
            for r in rows:
                ind = _row_to_indicator(r)
                if ind is not None:
                    indicators.append(ind)
    return indicators


def _looks_like_indicator_table(row: dict[str, str]) -> bool:
    """Check if a table row looks like an activation indicator table."""
    keys_lower = {k.lower() for k in row.keys()}
    return "weight" in keys_lower and ("indicator" in keys_lower or "metric source" in keys_lower)


def _row_to_indicator(row: dict[str, str]) -> Indicator | None:
    """Convert a table row dict to an Indicator object."""
    # Normalize keys to lowercase
    norm = {k.lower().strip(): v.strip() for k, v in row.items()}

    name = norm.get("indicator", "")
    metric_source = norm.get("metric source", "")
    threshold = norm.get("threshold", "")
    direction_str = norm.get("direction", "").lower().strip()
    weight_str = norm.get("weight", "0")
    rationale = norm.get("rationale", "")

    if not name:
        return None

    # Parse weight
    requires_web_search = "web search" in metric_source.lower()
    is_qualitative = weight_str.lower() in ("qualitative", "n/a", "-", "")

    weight = -1.0
    if not is_qualitative:
        try:
            weight = float(weight_str)
        except ValueError:
            is_qualitative = True
            weight = -1.0

    # Parse direction
    direction = _parse_direction(direction_str)

    return Indicator(
        name=name,
        metric_source=metric_source,
        threshold=threshold,
        direction=direction,
        weight=weight,
        rationale=rationale,
        requires_web_search=requires_web_search,
        is_qualitative=is_qualitative,
    )


def _parse_direction(s: str) -> Direction:
    """Parse direction string to Direction enum, with fuzzy matching."""
    s = s.lower().strip()
    if s in ("above", "above target", "exceeds"):
        return Direction.ABOVE
    if s in ("below", "below target"):
        return Direction.BELOW
    if s in ("rising", "increasing", "expanding"):
        return Direction.RISING
    if s in ("falling", "declining", "decreasing", "contracting"):
        return Direction.FALLING
    if "between" in s:
        return Direction.BETWEEN
    # Default: try to infer from context
    if "above" in s:
        return Direction.ABOVE
    if "below" in s:
        return Direction.BELOW
    return Direction.ABOVE  # fallback


# ---------------------------------------------------------------------------
# Falsifier parsing
# ---------------------------------------------------------------------------

def _parse_hard_falsifiers(text: str) -> list[HardFalsifier]:
    """Parse hard falsifiers from the falsifiers section."""
    # Find the Hard Falsifiers subsection
    table_text = _find_table_after_header(text, r"###\s*Hard\s*Falsifiers")
    if not table_text:
        return []

    rows = _parse_table(table_text)
    results = []
    for row in rows:
        norm = {k.lower().strip().rstrip("s"): v.strip() for k, v in row.items()}
        # Also try original keys
        norm2 = {k.lower().strip(): v.strip() for k, v in row.items()}

        fid = norm2.get("#", "") or norm.get("#", "")
        condition = norm2.get("condition", "") or norm.get("condition", "")
        metric = norm2.get("metric", "") or norm.get("metric", "")
        threshold = norm2.get("threshold", "") or norm.get("threshold", "")
        rationale = norm2.get("rationale", "") or norm.get("rationale", "")

        if not fid:
            continue

        results.append(HardFalsifier(
            id=fid,
            condition=condition,
            metric=metric,
            threshold=threshold,
            rationale=rationale,
        ))

    return results


def _parse_soft_falsifiers(text: str) -> list[SoftFalsifier]:
    """Parse soft falsifiers with dynamic Severity column detection."""
    table_text = _find_table_after_header(text, r"###\s*Soft\s*Falsifiers")
    if not table_text:
        return []

    rows = _parse_table(table_text)
    if not rows:
        return []

    def _extract_severity_keyword(text: str) -> str:
        """Extract 'minor', 'medium', or 'major' from a cell that may contain extra text.

        Handles formats like '**major** — explanation...' or '**Medium**'.
        """
        clean = text.strip().strip("*").strip().lower()
        for keyword in ("major", "medium", "minor"):
            if clean.startswith(keyword):
                return keyword
        return ""

    # Detect which column contains Severity by checking headers
    first_row_keys = list(rows[0].keys())
    header_lower = [k.lower().strip() for k in first_row_keys]

    # Find the severity column index
    severity_idx = None
    for i, h in enumerate(header_lower):
        if "severity" in h:
            severity_idx = i
            break

    results = []
    for row in rows:
        norm = {k.lower().strip(): v.strip() for k, v in row.items()}

        fid = norm.get("#", "")
        if not fid:
            continue

        # Extract severity — find the column
        severity_str = ""
        for k, v in row.items():
            if "severity" in k.lower():
                severity_str = _extract_severity_keyword(v)
                break

        # If severity not found in headers, look in cell values
        if not severity_str:
            for v in row.values():
                found = _extract_severity_keyword(v)
                if found:
                    severity_str = found
                    break

        # Map remaining fields — exclude # and severity columns
        other_values = []
        for k, v in row.items():
            k_lower = k.lower().strip()
            if k_lower == "#" or "severity" in k_lower:
                continue
            other_values.append((k_lower, v.strip()))

        # Standard order after removing # and severity: condition, metric, threshold, implication
        condition = ""
        metric = ""
        threshold = ""
        implication = ""

        for k, v in other_values:
            if "condition" in k:
                condition = v
            elif "metric" in k:
                metric = v
            elif "threshold" in k:
                threshold = v
            elif "implication" in k:
                implication = v

        # Parse severity enum
        try:
            severity = Severity(severity_str)
        except ValueError:
            severity = Severity.MINOR

        results.append(SoftFalsifier(
            id=fid,
            severity=severity,
            condition=condition,
            metric=metric,
            threshold=threshold,
            implication=implication,
        ))

    return results


# ---------------------------------------------------------------------------
# Prediction parsing
# ---------------------------------------------------------------------------

def _parse_directional_predictions(text: str) -> list[DirectionalPrediction]:
    """Parse directional prediction tables from predictions_when_active section."""
    # Find tables under "Directional" headers (may be phase-specific)
    tables = _find_all_tables(text)
    results = []

    for table_text in tables:
        rows = _parse_table(table_text)
        for row in rows:
            norm = {k.lower().strip(): v.strip() for k, v in row.items()}
            asset = norm.get("asset", "")
            if not asset:
                continue

            results.append(DirectionalPrediction(
                asset=asset,
                direction=norm.get("direction", ""),
                magnitude_range=norm.get("magnitude range", ""),
                timeframe=norm.get("timeframe", ""),
                mechanism=norm.get("mechanism", "") or norm.get("condition", ""),
            ))

    # Deduplicate by asset name (tables may appear for each phase)
    seen = set()
    unique = []
    for p in results:
        key = (p.asset, p.direction)
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return unique


def _parse_conditional_predictions(text: str) -> list[ConditionalPrediction]:
    """Parse conditional prediction tables."""
    # Find the Conditional subsection table
    table_text = _find_table_after_header(
        text, r"###\s*Conditional\s*\(interaction"
    )
    if not table_text:
        # Try alternate header patterns
        table_text = _find_table_after_header(text, r"###\s*Conditional")
    if not table_text:
        return []

    rows = _parse_table(table_text)
    results = []
    for row in rows:
        norm = {k.lower().strip(): v.strip() for k, v in row.items()}

        # Handle both 3-col and 4-col variants
        type_val = norm.get("type", "Mechanism interaction")
        condition = norm.get("condition", "")
        prediction = norm.get("prediction", "")
        specificity = norm.get("specificity gain", "")

        if condition:
            results.append(ConditionalPrediction(
                type=type_val,
                condition=condition,
                prediction=prediction,
                specificity_gain=specificity,
            ))

    return results


# ---------------------------------------------------------------------------
# Downstream implications
# ---------------------------------------------------------------------------

def _parse_downstream_effects(text: str) -> list[DownstreamEffect]:
    """Parse the affects[] table from downstream_implications section."""
    table_text = _find_table_after_header(text, r"###\s*affects")
    if not table_text:
        # Try finding any table in the section
        tables = _find_all_tables(text)
        if tables:
            table_text = tables[0]

    if not table_text:
        return []

    rows = _parse_table(table_text)
    results = []
    for row in rows:
        norm = {k.lower().strip(): v.strip() for k, v in row.items()}
        target = norm.get("target theory", "")
        if not target:
            continue

        # Extract theory_id from backticks if present
        m = re.search(r"`([a-z_]+)`", target)
        target_id = m.group(1) if m else target

        relationship = norm.get("relationship", "")
        # Clean bold markdown from relationship
        relationship = relationship.strip("*").strip()

        results.append(DownstreamEffect(
            target_theory_id=target_id,
            relationship=relationship,
            description=norm.get("description", ""),
        ))

    return results


# ---------------------------------------------------------------------------
# Metadata parsing
# ---------------------------------------------------------------------------

def _parse_metadata(text: str) -> TheoryMetadata | None:
    """Extract JSON metadata block from the metadata section."""
    # Find JSON code block
    m = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    if not m:
        return None

    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None

    return TheoryMetadata(
        theory_id=data.get("theory_id", ""),
        version=data.get("version", 1),
        last_updated=data.get("last_updated", ""),
        update_type=data.get("update_type", ""),
        confidence_in_specification=data.get("confidence_in_specification", ""),
        notes=data.get("notes", ""),
        historical_episodes_referenced=data.get("historical_episodes_referenced", []),
    )
