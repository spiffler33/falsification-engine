"""v9 Phase 3.5: Parse ACTIVATION.md files into structured indicator data.

Extracts activation indicator tables from theory module ACTIVATION.md files
for compilation by the Haiku compiler. Handles single-phase and two-phase
theories, including the three different header patterns used across modules.

Depends on: theory markdown files in theories/THEORY_MODULE_*/ACTIVATION.md
Depended on by: scripts/v9_compile_theories.py
"""
from __future__ import annotations

import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Theory directory mapping
# ---------------------------------------------------------------------------

THEORIES_DIR = Path(__file__).resolve().parents[3] / "theories"

THEORY_DIRS: dict[str, str] = {
    "valuation_mean_reversion": "THEORY_MODULE_valuation_mean_reversion_v2",
    "debt_cycle_short": "THEORY_MODULE_debt_cycle_short_v2",
    "debt_cycle_long": "THEORY_MODULE_debt_cycle_long_v2",
    "structural_fragility": "THEORY_MODULE_structural_fragility_v2",
    "fiscal_dominance_arithmetic": "THEORY_MODULE_fiscal_dominance_arithmatic_v2",
    "fiscal_dominance_liquidity": "THEORY_MODULE_fiscal_dominance_liquidity_v2",
    "capital_flows": "THEORY_MODULE_capital_flows_v2",
    "monetary_architecture": "THEORY_MODULE_monetary_architecture_v2",
}

TWO_PHASE_THEORIES: dict[str, dict[str, str]] = {
    "debt_cycle_short": {"a": "Expansion", "b": "Contraction"},
    "structural_fragility": {"a": "Building", "b": "Resolving"},
    "capital_flows": {"a": "Accumulation", "b": "Rotation"},
}

ALL_THEORY_IDS = list(THEORY_DIRS.keys())


def get_activation_path(theory_id: str, theories_dir: Path = None) -> Path:
    """Get the path to a theory's ACTIVATION.md file."""
    base = theories_dir or THEORIES_DIR
    dir_name = THEORY_DIRS.get(theory_id)
    if not dir_name:
        raise ValueError(f"Unknown theory_id: {theory_id}")
    path = base / dir_name / "ACTIVATION.md"
    if not path.exists():
        raise FileNotFoundError(f"ACTIVATION.md not found: {path}")
    return path


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_activation_md(filepath: Path) -> dict:
    """Parse an ACTIVATION.md file into structured indicator data.

    Returns dict with keys:
        theory_id: str
        is_two_phase: bool
        source_file: str
        phases: list of phase dicts, each containing:
            phase_key: str (e.g., "single", "Phase A: Expansion")
            phase_label: str (e.g., "Active", "Expansion")
            phase_id: str (e.g., "single", "expansion")
            indicators: list of indicator dicts with:
                indicator_name, metric_source, data_ownership,
                threshold, direction, weight, calibration_rationale
    """
    text = filepath.read_text()
    theory_id = _extract_theory_id(filepath)
    is_two_phase = theory_id in TWO_PHASE_THEORIES

    if is_two_phase:
        phases = _parse_two_phase(text, theory_id)
    else:
        phases = _parse_single_phase(text)

    return {
        "theory_id": theory_id,
        "is_two_phase": is_two_phase,
        "source_file": str(filepath),
        "phases": phases,
    }


def _extract_theory_id(filepath: Path) -> str:
    """Extract theory_id from directory name."""
    dir_name = filepath.parent.name
    for tid, dname in THEORY_DIRS.items():
        if dir_name == dname:
            return tid
    raise ValueError(f"Cannot determine theory_id from {filepath}")


# ---------------------------------------------------------------------------
# Phase parsing
# ---------------------------------------------------------------------------

def _parse_single_phase(text: str) -> list[dict]:
    """Parse a single-phase ACTIVATION.md."""
    section = _extract_section(text, r"## activation_table\b")
    if not section:
        raise ValueError("Cannot find ## activation_table section")

    indicators = _parse_markdown_table(section)
    return [{
        "phase_key": "single",
        "phase_label": "Active",
        "phase_id": "single",
        "indicators": indicators,
    }]


def _parse_two_phase(text: str, theory_id: str) -> list[dict]:
    """Parse a two-phase ACTIVATION.md.

    Handles three header patterns:
      1. debt_cycle_short: ## activation_table -- Phase A: Expansion
      2. structural_fragility: ## activation_table + ### Phase A: Building
      3. capital_flows: ## activation_table + ### Phase A: Accumulation
    """
    phase_labels = TWO_PHASE_THEORIES[theory_id]
    phases = []

    # Pattern 1: separate ## headers with em-dash (debt_cycle_short)
    phase_a_header = re.search(
        r"## activation_table\s*[—–-]+\s*Phase\s*A\s*:\s*(.+)", text, re.IGNORECASE
    )
    phase_b_header = re.search(
        r"## activation_table\s*[—–-]+\s*Phase\s*B\s*:\s*(.+)", text, re.IGNORECASE
    )

    if phase_a_header and phase_b_header:
        phase_a_text = _extract_between_patterns(
            text,
            r"## activation_table\s*[—–-]+\s*Phase\s*A\b",
            r"## activation_table\s*[—–-]+\s*Phase\s*B\b|###\s+Activation\s+thresholds",
        )
        phase_b_text = _extract_between_patterns(
            text,
            r"## activation_table\s*[—–-]+\s*Phase\s*B\b",
            r"###\s+Activation\s+thresholds|## quadrant|## context|## falsifier",
        )
        phase_a_label = phase_a_header.group(1).strip()
        phase_b_label = phase_b_header.group(1).strip()
    else:
        # Pattern 2/3: parent ## activation_table with ### Phase A/B children
        parent = _extract_section(text, r"## activation_table\b")
        if not parent:
            raise ValueError("Cannot find activation table section")

        phase_a_text = _extract_between_patterns(
            parent,
            r"### Phase\s*A\s*:",
            r"### Phase\s*B\s*:|## \w",
        )
        phase_b_text = _extract_between_patterns(
            parent,
            r"### Phase\s*B\s*:",
            r"## \w",
        )
        phase_a_label = phase_labels["a"]
        phase_b_label = phase_labels["b"]

    if phase_a_text:
        indicators_a = _parse_markdown_table(phase_a_text)
        phases.append({
            "phase_key": f"Phase A: {phase_a_label}",
            "phase_label": phase_a_label,
            "phase_id": phase_a_label.lower(),
            "indicators": indicators_a,
        })

    if phase_b_text:
        indicators_b = _parse_markdown_table(phase_b_text)
        phases.append({
            "phase_key": f"Phase B: {phase_b_label}",
            "phase_label": phase_b_label,
            "phase_id": phase_b_label.lower(),
            "indicators": indicators_b,
        })

    if not phases:
        raise ValueError("No phase indicators found in two-phase theory")

    return phases


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------

def _extract_section(text: str, header_pattern: str) -> str | None:
    """Extract text from a ## header to the next ## header."""
    m = re.search(header_pattern, text, re.IGNORECASE)
    if not m:
        return None
    rest = text[m.end():]
    next_h2 = re.search(r"\n## ", rest)
    if next_h2:
        return text[m.start() : m.end() + next_h2.start()]
    return text[m.start():]


def _extract_between_patterns(text: str, start_pat: str, end_pat: str) -> str | None:
    """Extract text between two regex patterns."""
    m = re.search(start_pat, text, re.IGNORECASE)
    if not m:
        return None
    rest = text[m.end():]
    end = re.search(end_pat, rest, re.IGNORECASE)
    if end:
        return rest[: end.start()]
    return rest


# ---------------------------------------------------------------------------
# Markdown table parser
# ---------------------------------------------------------------------------

def _clean_weight(raw: str) -> str:
    """Strip inline annotations from weight cells.

    Handles patterns like "0.33 `[CALIBRATION]`" by extracting just the
    leading numeric value. This prevents Haiku from receiving non-numeric
    weight strings that cause it to default to equal weights.
    """
    import re
    m = re.match(r"([\d.]+)", raw)
    return m.group(1) if m else raw


def _is_separator_line(line: str) -> bool:
    """Check if a markdown table line is a separator (e.g., |---|---|)."""
    stripped = line.strip().replace("|", "")
    return bool(stripped.strip()) and all(c in "-: " for c in stripped)


def _parse_markdown_table(text: str) -> list[dict]:
    """Parse a markdown table into indicator dicts.

    Expected columns (7):
        Indicator | Metric Source | Data Ownership | Threshold |
        Direction | Weight | Calibration Rationale
    """
    lines = text.split("\n")
    header_found = False
    rows: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if header_found and rows:
                break  # End of table
            continue

        if _is_separator_line(stripped):
            continue

        if not header_found:
            header_found = True
            continue  # Skip header row

        rows.append(stripped)

    indicators = []
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) < 6:
            continue

        indicators.append({
            "indicator_name": cells[0].strip(),
            "metric_source": cells[1].strip(),
            "data_ownership": cells[2].strip() if len(cells) > 2 else "",
            "threshold": cells[3].strip() if len(cells) > 3 else "",
            "direction": cells[4].strip() if len(cells) > 4 else "",
            "weight": _clean_weight(cells[5].strip() if len(cells) > 5 else ""),
            "calibration_rationale": cells[6].strip() if len(cells) > 6 else "",
        })

    return indicators
