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
