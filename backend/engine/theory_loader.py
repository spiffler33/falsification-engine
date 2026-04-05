# theory_loader.py — Load v2 four-file theory packages from disk.
# Depends on: backend/config.py (THEORIES_DIR), backend/schemas/theory.py (TheoryPackage)
# Depended on by: (future) activation scoring, prompt builder, conviction pipeline
#
# Reads THEORY_MODULE_*_v2/ directories. Each directory must contain:
#   CORE.md, ACTIVATION.md, TACTICAL.md, PLAYBOOK.md
# theory_id is extracted from CORE.md content — NOT from the directory name
# (handles the fiscal_dominance_arithmatic typo).
from __future__ import annotations

import re
from pathlib import Path

from backend.config import THEORIES_DIR
from backend.schemas.theory import TheoryPackage

REQUIRED_FILES = ("CORE.md", "ACTIVATION.md", "TACTICAL.md", "PLAYBOOK.md")


def discover_theory_dirs(theories_dir: Path | None = None) -> list[Path]:
    """Find all THEORY_MODULE_*_v2/ directories, validating all four files exist."""
    d = theories_dir or THEORIES_DIR
    dirs = sorted(
        p for p in d.iterdir()
        if p.is_dir() and p.name.startswith("THEORY_MODULE_") and p.name.endswith("_v2")
    )

    for dir_path in dirs:
        missing = [f for f in REQUIRED_FILES if not (dir_path / f).exists()]
        if missing:
            raise FileNotFoundError(
                f"Theory directory {dir_path.name} is missing required files: "
                f"{', '.join(missing)}"
            )

    return dirs


def _extract_theory_id(core_text: str) -> str:
    """Extract theory_id from CORE.md content.

    Two patterns across the 8 theory packages:
    1. ``## theory_id`` section header → backtick-wrapped ID on the next non-empty line
    2. Frontmatter ``*theory_id: `...`*`` in the first few lines
    """
    lines = core_text.split("\n")

    # Pattern 1: ## theory_id section header
    for i, line in enumerate(lines):
        if line.strip().lower() == "## theory_id":
            for j in range(i + 1, min(i + 5, len(lines))):
                candidate = lines[j].strip()
                if candidate:
                    return candidate.strip("`").strip()
            break

    # Pattern 2: *theory_id: `...`* in frontmatter
    m = re.search(r"\*theory_id:\s*`([^`]+)`\*", core_text[:500])
    if m:
        return m.group(1).strip()

    raise ValueError("Could not extract theory_id from CORE.md content")


def load_theory_package(dir_path: Path) -> TheoryPackage:
    """Load a single theory package from a four-file directory.

    Returns TheoryPackage with raw text fields populated and registries empty
    (filled by later units: falsifier registry builder, data ownership parser).
    """
    core = (dir_path / "CORE.md").read_text(encoding="utf-8")
    activation = (dir_path / "ACTIVATION.md").read_text(encoding="utf-8")
    tactical = (dir_path / "TACTICAL.md").read_text(encoding="utf-8")
    playbook = (dir_path / "PLAYBOOK.md").read_text(encoding="utf-8")

    theory_id = _extract_theory_id(core)

    return TheoryPackage(
        theory_id=theory_id,
        core=core,
        activation=activation,
        tactical=tactical,
        playbook=playbook,
    )


def load_all_theory_packages(theories_dir: Path | None = None) -> list[TheoryPackage]:
    """Discover and load all theory packages. Raises on any failure — no partial loads."""
    dirs = discover_theory_dirs(theories_dir)
    return [load_theory_package(d) for d in dirs]


# ---------------------------------------------------------------------------
# Unit 3: CORE.md deep_falsifiers parser
# ---------------------------------------------------------------------------

_SEPARATOR_CELL_RE = re.compile(r"^-+$")


def parse_deep_falsifiers(core_text: str) -> list[dict]:
    """Parse the ## deep_falsifiers section from CORE.md.

    Returns list of dicts with keys: falsifier_id, condition, logic.
    These are the CORE.md side of the falsifier registry join —
    classification/severity comes from ACTIVATION.md (Unit 4).

    Handles format variations across the 8 theories:
    - First column header may be '#' or 'ID'
    - Section may contain multiple sub-tables under ### sub-headers
      (e.g., monetary_architecture has Theory-Killing + Theory-Modifying)
    """
    lines = core_text.split("\n")

    # Find ## deep_falsifiers section start (line after the header)
    section_start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s+deep_falsifiers\s*$", line.strip(), re.IGNORECASE):
            section_start = i + 1
            break

    if section_start is None:
        raise ValueError("CORE.md has no ## deep_falsifiers section")

    # Section ends at next ## header (not ### sub-header) or EOF
    section_end = len(lines)
    for i in range(section_start, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            section_end = i
            break

    entries: list[dict] = []
    for line in lines[section_start:section_end]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue

        # Split by pipe, drop empty edge cells from leading/trailing |
        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c]

        if len(cells) < 3:
            continue

        # Skip separator rows (e.g., |---|-----------|-------|)
        if all(_SEPARATOR_CELL_RE.match(c) for c in cells):
            continue

        # Skip header rows (first cell is '#' or 'ID')
        if cells[0].lower() in ("#", "id"):
            continue

        falsifier_id = cells[0]
        condition = cells[1]
        logic = cells[2]

        if not falsifier_id or not condition or not logic:
            raise ValueError(
                f"deep_falsifiers table row has empty field: "
                f"id={falsifier_id!r}, condition={condition!r}, logic={logic!r}"
            )

        entries.append({
            "falsifier_id": falsifier_id,
            "condition": condition,
            "logic": logic,
        })

    if not entries:
        raise ValueError("deep_falsifiers section contains no parseable table rows")

    return entries
