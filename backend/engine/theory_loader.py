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


# ---------------------------------------------------------------------------
# Unit 4: ACTIVATION.md falsifier_severity_assignments parser
# ---------------------------------------------------------------------------

_SEVERITY_KEYWORD_RE = re.compile(r"\b(minor|medium|major)\b", re.IGNORECASE)
_HARD_INDICATOR_RE = re.compile(
    r"\b(hard|theory[- ]?kill|binary\s+kill|deactivat|disconfirm)",
    re.IGNORECASE,
)
_FALS_ID_RE = re.compile(r"(H\d+|S\d+|DF\d+|SF\d+)\b")


def _find_severity_section(
    lines: list[str], section_name: str,
) -> tuple[int, int] | None:
    """Return ``(start, end)`` line range for ``## <section_name>``, or *None*."""
    for i, line in enumerate(lines):
        if re.match(
            rf"^##\s+{re.escape(section_name)}\s*$", line.strip(), re.IGNORECASE,
        ):
            start = i + 1
            for j in range(start, len(lines)):
                # Next ## header (not ###) ends the section
                s = lines[j].strip()
                if s.startswith("## ") and not s.startswith("### "):
                    return (start, j)
            return (start, len(lines))
    return None


def _classify_subheader(line: str) -> str | None:
    """Return ``'core'`` or ``'state'`` based on a ``###`` sub-header's wording."""
    lower = line.strip().lower()
    if not lower.startswith("###"):
        return None
    if any(k in lower for k in ("theory-level", "theory level", "deep falsif", "from core")):
        return "core"
    if any(k in lower for k in ("state-level", "state level", "soft falsif", "state falsif")):
        return "state"
    return None


def _map_severity_columns(header_cells: list[str]) -> dict[str, int]:
    """Map table column roles to indices from a header row."""
    m: dict[str, int] = {}
    for i, c in enumerate(header_cells):
        lo = c.lower().strip()
        if lo in ("#", "id"):
            m.setdefault("id", i)
        elif lo.startswith("falsifier"):
            m.setdefault("id", i)
        elif lo == "condition":
            m.setdefault("condition", i)
        elif lo == "classification":
            m.setdefault("classification", i)
        elif lo == "severity":
            m.setdefault("severity", i)
        elif lo in (
            "implication", "rationale", "description", "notes",
            "scoring effect", "effect",
        ):
            m.setdefault("logic", i)
        elif lo == "discount":
            m.setdefault("discount", i)
        elif lo == "location":
            m.setdefault("location", i)
    return m


def _extract_fals_id(text: str) -> str | None:
    """Extract a falsifier ID (H1, S3, DF2, SF1) from text."""
    hit = _FALS_ID_RE.search(text)
    return hit.group(1) if hit else None


def _classify_severity_text(text: str) -> tuple[str, str | None]:
    """Return ``(classification, severity)`` from free-text severity info.

    * ``("hard", None)`` for hard / theory-killing entries.
    * ``("soft", "minor"/"medium"/"major")`` for soft entries.
    * ``("soft", None)`` when soft but severity not determinable from this text.
    """
    if _HARD_INDICATOR_RE.search(text):
        return ("hard", None)
    if "n/a" in text.lower() and "hard" in text.lower():
        return ("hard", None)
    if re.search(r"state\s+change\s*→?\s*inactive", text, re.IGNORECASE):
        return ("hard", None)
    hit = _SEVERITY_KEYWORD_RE.search(text)
    if hit:
        return ("soft", hit.group(1).lower())
    return ("soft", None)


def _determine_source(
    context: str, cells: list[str], col_map: dict[str, int], fid: str | None,
) -> str:
    """Return ``'core'`` or ``'state'`` for an entry."""
    # 1. Sub-header context (most reliable)
    if context in ("core", "state"):
        return context
    # 2. Location column (debt_cycle_short consolidated table)
    if "location" in col_map and col_map["location"] < len(cells):
        loc = cells[col_map["location"]].lower()
        if "core.md" in loc:
            return "core"
        if "activation.md" in loc or "state" in loc:
            return "state"
    # 3. ID prefix heuristic
    if fid and (fid.startswith("H") or fid.startswith("DF")):
        return "core"
    return "state"


def _parse_falsifier_tables(
    lines: list[str], start: int, end: int, *, force_state: bool = False,
) -> list[dict]:
    """Parse all falsifier tables within a line range.

    Tracks ``###`` sub-headers for core/state context.
    *force_state=True* treats all entries as ``source='state'``.
    """
    entries: list[dict] = []
    context = "state" if force_state else "unknown"
    col_map: dict[str, int] = {}
    in_table = False
    auto_id_counter = 0

    for i in range(start, end):
        stripped = lines[i].strip()

        # Track ### sub-headers for context
        if stripped.startswith("### ") and not force_state:
            ctx = _classify_subheader(stripped)
            if ctx:
                context = ctx
            in_table = False
            col_map = {}
            continue

        # Non-table line resets table state
        if not stripped.startswith("|"):
            if in_table:
                in_table = False
                col_map = {}
            continue

        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c != ""]
        if len(cells) < 2:
            continue

        if all(_SEPARATOR_CELL_RE.match(c) for c in cells):
            continue

        # First table line is the header row
        if not in_table:
            col_map = _map_severity_columns(cells)
            in_table = True
            continue

        # --- Data row ---

        # Extract falsifier ID
        id_idx = col_map.get("id", 0)
        fid = _extract_fals_id(cells[id_idx]) if id_idx < len(cells) else None
        if fid is None:
            for cell in cells:
                fid = _extract_fals_id(cell)
                if fid:
                    break
        if fid is None:
            auto_id_counter += 1
            fid = f"ST_{auto_id_counter}"

        # Determine classification + severity
        classification: str | None = None
        severity: str | None = None

        if "classification" in col_map and col_map["classification"] < len(cells):
            classification, severity = _classify_severity_text(
                cells[col_map["classification"]],
            )
        if "severity" in col_map and col_map["severity"] < len(cells):
            cls2, sev2 = _classify_severity_text(cells[col_map["severity"]])
            if classification is None:
                classification = cls2
            if severity is None:
                severity = sev2
        if classification is None:
            for cell in cells:
                cls3, sev3 = _classify_severity_text(cell)
                if cls3 == "hard" or sev3 is not None:
                    classification = cls3
                    severity = sev3
                    break
        classification = classification or "soft"

        # Determine source
        source = "state" if force_state else _determine_source(
            context, cells, col_map, fid,
        )

        entry: dict[str, object] = {
            "falsifier_id": fid,
            "classification": classification,
            "severity": severity,
            "source": source,
        }

        # State-level entries carry condition + logic from ACTIVATION.md
        if source == "state":
            condition: str | None = None
            logic: str | None = None

            if "condition" in col_map and col_map["condition"] < len(cells):
                condition = cells[col_map["condition"]]
            else:
                # Condition may be embedded in the ID cell ("S1: description")
                if id_idx < len(cells):
                    remainder = re.sub(
                        r"^(?:H\d+|S\d+|DF\d+|SF\d+)\s*[:\u2014\u2013\-]\s*",
                        "", cells[id_idx],
                    ).strip()
                    remainder = re.sub(r"^\((.+)\)$", r"\1", remainder)
                    if remainder and remainder != cells[id_idx].strip():
                        condition = remainder
                # First column IS the condition (no ID header at all)
                if condition is None and "id" not in col_map and cells:
                    condition = cells[0]

            if "logic" in col_map and col_map["logic"] < len(cells):
                logic = cells[col_map["logic"]]

            entry["condition"] = condition or ""
            entry["logic"] = logic or ""

        entries.append(entry)

    return entries


def _deduplicate_severity_entries(entries: list[dict]) -> list[dict]:
    """Deduplicate by falsifier_id, preferring entries with more detail."""
    seen: dict[str, dict] = {}
    for entry in entries:
        fid = str(entry["falsifier_id"])
        if fid not in seen:
            seen[fid] = entry
        else:
            existing = seen[fid]
            new_has_cond = bool(entry.get("condition"))
            old_has_cond = bool(existing.get("condition"))
            if new_has_cond and not old_has_cond:
                seen[fid] = entry
            elif entry.get("severity") and not existing.get("severity"):
                seen[fid] = entry
    return list(seen.values())


def parse_falsifier_severity(activation_text: str) -> list[dict]:
    """Parse falsifier severity assignments from ACTIVATION.md.

    Extracts from ``## falsifier_severity_assignments`` and
    ``## state_falsifiers`` sections.  Handles both inline and separate
    state-level falsifier patterns across all 8 theory modules.

    Returns list of dicts with keys:

    * ``falsifier_id`` -- e.g. ``"H1"``, ``"S3"``, ``"DF1"``, ``"SF2"``
    * ``classification`` -- ``"hard"`` or ``"soft"``
    * ``severity`` -- ``"minor"`` / ``"medium"`` / ``"major"`` or ``None`` (hard)
    * ``source`` -- ``"core"`` (theory-level) or ``"state"`` (ACTIVATION-only)

    State-level entries (``source="state"``) additionally carry:

    * ``condition`` -- the falsifier condition text
    * ``logic`` -- implication / rationale text
    """
    lines = activation_text.split("\n")
    sev_range = _find_severity_section(lines, "falsifier_severity_assignments")
    state_range = _find_severity_section(lines, "state_falsifiers")

    if sev_range is None and state_range is None:
        raise ValueError(
            "ACTIVATION.md has no ## falsifier_severity_assignments or "
            "## state_falsifiers section"
        )

    entries: list[dict] = []
    if sev_range is not None:
        entries.extend(_parse_falsifier_tables(lines, *sev_range))
    if state_range is not None:
        entries.extend(
            _parse_falsifier_tables(lines, *state_range, force_state=True),
        )

    entries = _deduplicate_severity_entries(entries)

    if not entries:
        raise ValueError(
            "falsifier_severity_assignments / state_falsifiers sections "
            "contain no parseable entries"
        )

    return entries
