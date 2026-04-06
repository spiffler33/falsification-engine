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
from backend.schemas.theory import (
    ContextFlag,
    FalsifierEntry,
    IndicatorOwnership,
    Severity,
    TheoryPackage,
)

REQUIRED_FILES = ("CORE.md", "ACTIVATION.md", "TACTICAL.md", "PLAYBOOK.md")


def _normalize_section_header(line: str) -> str:
    """Normalize a markdown section header for matching.

    Lowercases, replaces underscores with spaces, collapses whitespace.
    '## Activation_Table' and '## activation table' both → '## activation table'.
    '## Deep Falsifiers' and '## deep_falsifiers' both → '## deep falsifiers'.
    """
    return re.sub(r"[\s_]+", " ", line.strip().lower()).strip()


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
    1. ``## theory_id`` section header → ID on the next non-empty line
       (backtick-wrapped or plain)
    2. Frontmatter ``*theory_id: `...`*`` in the first few lines

    FRAGILITY-10: accepts underscore/space/case variants in both the section
    header and the frontmatter key name. Validates the extracted ID is a
    valid snake_case identifier.
    """
    lines = core_text.split("\n")

    # Pattern 1: ## theory_id section header (normalized: underscore/space/case)
    for i, line in enumerate(lines):
        if _normalize_section_header(line) == "## theory id":
            for j in range(i + 1, min(i + 5, len(lines))):
                candidate = lines[j].strip()
                if candidate:
                    tid = candidate.strip("`").strip()
                    if re.fullmatch(r"[a-z][a-z0-9_]+", tid):
                        return tid
                    raise ValueError(
                        f"theory_id value {tid!r} is not a valid "
                        f"snake_case identifier"
                    )
            break

    # Pattern 2: *theory_id: `...`* in frontmatter — accept underscore/space
    # in key name and optional backticks around the value
    m = re.search(
        r"\*theory[_ ]id:\s*`?([^`*\n]+)`?\*", core_text[:500], re.IGNORECASE,
    )
    if m:
        tid = m.group(1).strip()
        if re.fullmatch(r"[a-z][a-z0-9_]+", tid):
            return tid
        raise ValueError(
            f"theory_id value {tid!r} is not a valid snake_case identifier"
        )

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

    # Find ## deep_falsifiers section start (normalized: underscore/space/case)
    section_start = None
    for i, line in enumerate(lines):
        if _normalize_section_header(line) == "## deep falsifiers":
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
    """Return ``(start, end)`` line range for ``## <section_name>``, or *None*.

    Uses normalized header matching so underscore/space/case differences
    in the section header do not break detection.
    """
    target = _normalize_section_header(f"## {section_name}")
    for i, line in enumerate(lines):
        if _normalize_section_header(line) == target:
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


# ---------------------------------------------------------------------------
# Unit 5: Falsifier registry join logic + orphan validation
# ---------------------------------------------------------------------------

_SEVERITY_DISCOUNT = {"minor": 0.10, "medium": 0.25, "major": 0.45}


def build_falsifier_registry(
    core_text: str, activation_text: str,
) -> list[FalsifierEntry]:
    """Pre-join CORE.md deep_falsifiers with ACTIVATION.md severity assignments.

    Core-sourced entries: condition/logic from CORE.md, classification/severity
    from ACTIVATION.md.  State-level entries: self-contained in ACTIVATION.md.

    Raises ValueError on orphan falsifiers in either direction.
    """
    core_entries = parse_deep_falsifiers(core_text)
    sev_entries = parse_falsifier_severity(activation_text)

    core_by_id = {e["falsifier_id"]: e for e in core_entries}
    sev_by_id = {e["falsifier_id"]: e for e in sev_entries}

    # --- Orphan validation (core-sourced entries only) ---
    core_ids = set(core_by_id)
    activation_core_ids = {
        e["falsifier_id"] for e in sev_entries if e["source"] == "core"
    }

    orphans_in_core = core_ids - activation_core_ids
    if orphans_in_core:
        raise ValueError(
            f"CORE.md falsifiers missing from ACTIVATION.md severity assignments: "
            f"{sorted(orphans_in_core)}"
        )

    orphans_in_activation = activation_core_ids - core_ids
    if orphans_in_activation:
        raise ValueError(
            f"ACTIVATION.md references CORE.md falsifiers that do not exist: "
            f"{sorted(orphans_in_activation)}"
        )

    # --- Build registry ---
    registry: list[FalsifierEntry] = []

    for sev in sev_entries:
        fid = sev["falsifier_id"]
        classification = sev["classification"]
        severity_str = sev["severity"]

        if sev["source"] == "core":
            # Join: condition/logic from CORE, classification/severity from ACTIVATION
            core = core_by_id[fid]
            condition = core["condition"]
            logic = core["logic"]
        else:
            # State-level: self-contained in ACTIVATION
            condition = sev.get("condition", "")
            logic = sev.get("logic", "")

        severity = Severity(severity_str) if severity_str else None
        discount = _SEVERITY_DISCOUNT.get(severity_str) if severity_str else None

        registry.append(FalsifierEntry(
            falsifier_id=fid,
            condition=condition,
            logic=logic,
            classification=classification,
            severity=severity,
            discount=discount,
        ))

    return registry


# ---------------------------------------------------------------------------
# Unit 6: ACTIVATION.md activation_table parser with data_ownership
# ---------------------------------------------------------------------------

_OWNERSHIP_KW_RE = re.compile(
    r"(computed-mechanical|web-search|mechanical|qualitative)", re.IGNORECASE,
)

_PHASE_SUBSECTION_RE = re.compile(
    r"^###\s+(Phase\s+[AB]:\s*.+)", re.IGNORECASE,
)

_ACTIVATION_TABLE_SUFFIX_RE = re.compile(r"[—–\-]+\s*(.+)$")

_WEIGHT_NUM_RE = re.compile(r"[\d.]+")

# Canonical data_ownership values for activation_table indicators.
# "qualitative" is NOT valid here — qualitative indicators must live in
# context_flags (validated separately by parse_activation_table).
_VALID_ACTIVATION_OWNERSHIP = {"mechanical", "computed-mechanical", "web-search"}

# Required activation table columns — the parser fails loudly if any are
# missing from the header row (FRAGILITY-02).
_REQUIRED_ACTIVATION_COLS = {
    "indicator", "metric_source", "data_ownership",
    "threshold", "direction", "weight",
}


def _map_activation_columns(header_cells: list[str]) -> dict[str, int]:
    """Map activation table column roles to indices from a header row.

    Handles reasonable header name variations (case-insensitive, multi-word).
    Returns dict mapping canonical role names to column indices.
    """
    m: dict[str, int] = {}
    for i, c in enumerate(header_cells):
        lo = c.lower().strip()
        if lo in ("indicator", "indicator name"):
            m.setdefault("indicator", i)
        elif "metric" in lo and "source" in lo:
            m.setdefault("metric_source", i)
        elif "ownership" in lo:
            m.setdefault("data_ownership", i)
        elif lo == "threshold":
            m.setdefault("threshold", i)
        elif lo == "direction":
            m.setdefault("direction", i)
        elif lo == "weight":
            m.setdefault("weight", i)
    return m


def _parse_activation_rows(
    lines: list[str], start: int, end: int, header_phase: str | None,
) -> list[dict]:
    """Parse indicator rows from an activation_table section.

    *header_phase* overrides phase for all rows (debt_cycle_short pattern).
    Within the section, ``### Phase A/B:`` subsections update the current phase
    (structural_fragility / capital_flows pattern).

    FRAGILITY-02: columns are resolved by header-name mapping, not position.
    """
    entries: list[dict] = []
    current_phase = header_phase
    in_table = False
    col_map: dict[str, int] = {}
    min_cells = 6  # updated to actual value when header is parsed

    for i in range(start, end):
        stripped = lines[i].strip()

        # Track ### Phase subsections
        pm = _PHASE_SUBSECTION_RE.match(stripped)
        if pm:
            current_phase = pm.group(1).strip()
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
        cells = [c for c in cells if c]

        # Skip separator rows (must check before short-row validation)
        if all(_SEPARATOR_CELL_RE.match(c) for c in cells):
            continue

        # FRAGILITY-09: pre-header short rows (< 4 cells) are skipped
        # silently — they may be sub-heading fragments.  Rows with ≥ 4
        # cells are treated as header attempts so that missing-column
        # errors surface clearly.  Post-header, the minimum cell count
        # is derived from the column map.
        if not in_table:
            if len(cells) < 4:
                continue
            # First non-separator row with ≥4 cells is the header.
            # Build column map and validate required columns.
            col_map = _map_activation_columns(cells)
            missing = _REQUIRED_ACTIVATION_COLS - set(col_map.keys())
            if missing:
                raise ValueError(
                    f"Activation table header missing required columns: "
                    f"{sorted(missing)}. Header cells: {cells}"
                )
            min_cells = max(col_map.values()) + 1
            in_table = True
            continue

        # Post-header: data rows must have enough cells for all mapped columns
        if len(cells) < min_cells:
            raise ValueError(
                f"Short activation table row ({len(cells)} cells, "
                f"need {min_cells}+): {stripped!r}"
            )

        # --- Data row: extract by column name (FRAGILITY-02) ---
        indicator_name = cells[col_map["indicator"]]
        metric_source = cells[col_map["metric_source"]]
        ownership_raw = cells[col_map["data_ownership"]]
        threshold = cells[col_map["threshold"]]
        direction = cells[col_map["direction"]]
        weight_str = cells[col_map["weight"]]

        # Extract data ownership keyword
        om = _OWNERSHIP_KW_RE.search(ownership_raw)
        if om:
            data_ownership = om.group(1).lower()
        else:
            # Fallback: strip backticks and take first token
            stripped_own = ownership_raw.strip("`").strip()
            data_ownership = stripped_own.split()[0].lower() if stripped_own else ""

        # BUG-06: validate data_ownership against canonical set.
        # Invalid values must fail loudly rather than silently propagating
        # into scoring where they cause undefined behavior.
        if data_ownership not in _VALID_ACTIVATION_OWNERSHIP:
            raise ValueError(
                f"Indicator {indicator_name!r} has invalid data_ownership "
                f"{data_ownership!r} — must be one of: "
                f"{', '.join(sorted(_VALID_ACTIVATION_OWNERSHIP))}"
            )

        # FRAGILITY-08: reject non-numeric weights loudly.
        # A data row past the header MUST have a parseable numeric weight.
        # Silent skip here would invisibly remove an indicator from scoring.
        wm = _WEIGHT_NUM_RE.search(weight_str)
        if not wm:
            raise ValueError(
                f"Indicator {indicator_name!r} has non-numeric weight: "
                f"{weight_str!r}"
            )
        weight = float(wm.group())

        entries.append({
            "indicator_name": indicator_name,
            "metric_source": metric_source,
            "threshold": threshold,
            "direction": direction,
            "weight": weight,
            "data_ownership": data_ownership,
            "phase": current_phase,
        })

    return entries


def parse_activation_table(activation_text: str) -> list[dict]:
    """Parse ``## activation_table`` section(s) from ACTIVATION.md.

    Returns list of dicts with keys:

    * ``indicator_name`` — human-readable indicator label
    * ``metric_source`` — data source or computed expression
    * ``threshold`` — trigger condition text
    * ``direction`` — above / below / rising / falling etc.
    * ``weight`` — float, scoring weight (0.0–1.0)
    * ``data_ownership`` — ``"mechanical"`` | ``"computed-mechanical"`` | ``"web-search"``
    * ``phase`` — ``None`` for single-phase, or e.g. ``"Phase A: Expansion"``

    Handles both two-phase heading formats:

    * ``## activation_table`` with ``### Phase A/B:`` subsections
      (structural_fragility, capital_flows)
    * ``## activation_table — Phase A/B: ...`` as separate headings
      (debt_cycle_short)

    Raises ``ValueError`` if:

    * No ``## activation_table`` section found.
    * No parseable indicator rows.
    * Any indicator has ``data_ownership`` ``"qualitative"``
      (must be in ``context_flags``, not ``activation_table``).
    """
    lines = activation_text.split("\n")

    # Collect section ranges: (start_line, end_line, phase_from_heading | None)
    # Normalized matching: '## Activation Table', '## activation_table' etc.
    # all match.  Phase suffix (e.g. '— Phase A: Expansion') extracted from
    # the original line to preserve casing.
    ranges: list[tuple[int, int, str | None]] = []
    for i, line in enumerate(lines):
        norm = _normalize_section_header(line)
        if norm == "## activation table" or norm.startswith(
            "## activation table "
        ):
            # Extract optional phase suffix from original line
            suffix_m = _ACTIVATION_TABLE_SUFFIX_RE.search(line.strip())
            phase = suffix_m.group(1).strip() if suffix_m else None
            # Section ends at next ## heading (not ###)
            end = len(lines)
            for j in range(i + 1, len(lines)):
                s = lines[j].strip()
                if s.startswith("## ") and not s.startswith("### "):
                    end = j
                    break
            ranges.append((i + 1, end, phase))

    if not ranges:
        raise ValueError("ACTIVATION.md has no ## activation_table section")

    entries: list[dict] = []
    for start, end, header_phase in ranges:
        entries.extend(_parse_activation_rows(lines, start, end, header_phase))

    if not entries:
        raise ValueError(
            "activation_table section(s) contain no parseable indicator rows"
        )

    # Validate: qualitative indicators must not appear in activation_table
    for entry in entries:
        if entry["data_ownership"] == "qualitative":
            raise ValueError(
                f"Qualitative indicator {entry['indicator_name']!r} found in "
                f"activation_table — qualitative indicators must be in "
                f"context_flags, not activation_table"
            )

    return entries


# ---------------------------------------------------------------------------
# Unit 7: ACTIVATION.md context_flags parser
# ---------------------------------------------------------------------------

_VALID_CTX_OWNERSHIP = {"qualitative", "web-search"}


def _map_context_flag_columns(header_cells: list[str]) -> dict[str, int]:
    """Map context flag table column roles to indices from a header row.

    Handles all observed column name variations across the 8 theories.
    """
    m: dict[str, int] = {}
    for i, c in enumerate(header_cells):
        lo = c.lower().strip()
        if lo == "flag":
            m.setdefault("flag_name", i)
        elif lo == "source":
            m.setdefault("source", i)
        elif lo == "data ownership":
            m.setdefault("data_ownership", i)
        elif lo in ("what to look for", "description"):
            m.setdefault("description", i)
        elif lo in ("usage", "why context, not scored"):
            m.setdefault("usage", i)
    return m


def _extract_ctx_ownership(raw: str) -> str:
    """Extract a valid data_ownership keyword from raw cell text.

    Handles backtick-wrapped values and compound entries like
    ``web-search / computed-mechanical`` → ``'web-search'``.
    """
    lo = raw.lower().strip().strip("`").strip()
    for kw in ("web-search", "qualitative"):
        if kw in lo:
            return kw
    return lo  # return as-is; validation will catch invalid values


def parse_context_flags(activation_text: str) -> list[dict]:
    """Parse ``## context_flags`` section from ACTIVATION.md.

    Returns list of dicts with keys:

    * ``flag_name`` — human-readable flag label
    * ``source`` — data source description (empty if column absent)
    * ``data_ownership`` — ``"qualitative"`` or ``"web-search"``
    * ``description`` — what to look for / flag description
    * ``usage`` — how the flag is used (empty if column absent)

    Handles column variations across all 8 theories:

    * Most: ``| Flag | Source | Data Ownership | What to Look For |``
    * structural_fragility: adds ``| Usage |`` column
    * fiscal_dominance_liquidity: swaps Source / Data Ownership order
    * debt_cycle_short: no Data Ownership column (defaults to ``qualitative``)
    * capital_flows: ``| Flag | Description | Why Context, Not Scored |``

    Context flags have NO weight. Weight columns are ignored.

    Raises ``ValueError`` if:

    * No ``## context_flags`` section found.
    * No parseable table rows.
    * Any entry has ``data_ownership`` not in {``qualitative``, ``web-search``}.
    """
    lines = activation_text.split("\n")

    # Find ## context_flags section (normalized: underscore/space/case)
    section_start = None
    for i, line in enumerate(lines):
        if _normalize_section_header(line) == "## context flags":
            section_start = i + 1
            break

    if section_start is None:
        raise ValueError("ACTIVATION.md has no ## context_flags section")

    # Section ends at next ## header (not ###) or EOF
    section_end = len(lines)
    for i in range(section_start, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            section_end = i
            break

    entries: list[dict] = []
    col_map: dict[str, int] = {}
    in_table = False

    for i in range(section_start, section_end):
        stripped = lines[i].strip()

        if not stripped.startswith("|"):
            if in_table:
                in_table = False
                col_map = {}
            continue

        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c]

        if len(cells) < 2:
            continue

        # Skip separator rows
        if all(_SEPARATOR_CELL_RE.match(c) for c in cells):
            continue

        # First non-separator row is the header
        if not in_table:
            col_map = _map_context_flag_columns(cells)
            in_table = True
            continue

        # --- Data row ---
        def _cell(key: str, default: str = "") -> str:
            idx = col_map.get(key)
            if idx is not None and idx < len(cells):
                return cells[idx]
            return default

        flag_name = _cell("flag_name") or cells[0]
        source = _cell("source")
        description = _cell("description")
        usage = _cell("usage")

        # FRAGILITY-04: Data ownership — extract from column, or default to
        # "qualitative" when the column is absent.  Missing ownership column
        # is allowed ONLY when every flag in the table is qualitative (e.g.
        # debt_cycle_short).  The constraint is validated below after all
        # entries are collected.
        has_ownership_col = "data_ownership" in col_map
        if has_ownership_col:
            data_ownership = _extract_ctx_ownership(_cell("data_ownership"))
        else:
            data_ownership = "qualitative"

        entries.append({
            "flag_name": flag_name,
            "source": source,
            "data_ownership": data_ownership,
            "description": description,
            "usage": usage,
        })

    if not entries:
        raise ValueError("context_flags section contains no parseable table rows")

    # Validate data_ownership values
    for entry in entries:
        if entry["data_ownership"] not in _VALID_CTX_OWNERSHIP:
            raise ValueError(
                f"Context flag {entry['flag_name']!r} has invalid data_ownership "
                f"{entry['data_ownership']!r} — must be 'qualitative' or 'web-search'"
            )

    # FRAGILITY-04 constraint: if ownership column was absent, every entry
    # must be qualitative.  If any entry needs web-search ownership, the
    # column must be present so the classification is explicit.
    if not has_ownership_col:
        non_qual = [
            e for e in entries if e["data_ownership"] != "qualitative"
        ]
        if non_qual:
            names = [e["flag_name"] for e in non_qual]
            raise ValueError(
                f"context_flags table has no Data Ownership column but "
                f"{len(non_qual)} flag(s) resolved to non-qualitative "
                f"ownership: {names}. Add the ownership column to make "
                f"classifications explicit."
            )

    return entries


# ---------------------------------------------------------------------------
# Unit 8: INTERACTION_MATRIX.md parser
# ---------------------------------------------------------------------------

_PAIRWISE_NORMALIZED = "## pairwise interaction table"
_SHARED_UPSTREAM_NORMALIZED = "## shared upstream cause warning"


def _strip_phase_annotation(theory_ref: str) -> tuple[str, str | None]:
    """Strip phase annotation from a theory reference.

    Returns (theory_id, phase_annotation_or_None).
    E.g. "structural_fragility (Building)" -> ("structural_fragility", "Building")
    """
    m = re.search(r"\(([^)]+)\)\s*$", theory_ref.strip())
    if m:
        phase = m.group(1).strip()
        theory_id = theory_ref[:m.start()].strip()
        return theory_id, phase
    return theory_ref.strip(), None


def _extract_theory_ids_from_ref(theory_ref: str) -> list[str]:
    """Extract all theory_ids from a theories-affected cell.

    Splits on commas that are outside parentheses (descriptions can
    contain commas, e.g. "fiscal_dominance_liquidity (reserve injection, flow)").

    Returns list of snake_case theory_id strings.
    """
    # Split respecting parentheses — only split on commas at depth 0
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in theory_ref:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())

    ids: list[str] = []
    for part in parts:
        if not part:
            continue
        m = re.match(r"([a-z][a-z0-9_]+)", part.strip())
        if m:
            ids.append(m.group(1))
    return ids


def parse_interaction_pairwise(matrix_text: str) -> list[dict]:
    """Parse the ## Pairwise Interaction Table from INTERACTION_MATRIX.md.

    Returns list of dicts with keys:
    * ``theory_a`` — theory_id (without phase annotation)
    * ``theory_a_phase`` — phase annotation or None
    * ``theory_b`` — theory_id (without phase annotation)
    * ``theory_b_phase`` — phase annotation or None
    * ``relationship`` — relationship description (e.g. "A triggers B")
    * ``invariant_logic`` — the causal relationship text
    * ``expression_detail_location`` — file path references
    """
    lines = matrix_text.split("\n")

    # Find section start (normalized: underscore/space/case)
    section_start = None
    for i, line in enumerate(lines):
        if _normalize_section_header(line) == _PAIRWISE_NORMALIZED:
            section_start = i + 1
            break

    if section_start is None:
        raise ValueError(
            "INTERACTION_MATRIX.md has no ## Pairwise Interaction Table section"
        )

    # Section ends at next ## header or EOF
    section_end = len(lines)
    for i in range(section_start, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            if _normalize_section_header(stripped) != _PAIRWISE_NORMALIZED:
                section_end = i
                break

    entries: list[dict] = []
    in_table = False

    for i in range(section_start, section_end):
        stripped = lines[i].strip()

        if not stripped.startswith("|"):
            if in_table:
                in_table = False
            continue

        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c]

        if len(cells) < 5:
            continue

        # Skip separator rows
        if all(_SEPARATOR_CELL_RE.match(c) for c in cells):
            continue

        # First non-separator row is the header — skip it
        if not in_table:
            in_table = True
            continue

        # --- Data row ---
        theory_a_raw = cells[0]
        theory_b_raw = cells[1]
        relationship = cells[2]
        invariant_logic = cells[3]
        expression_detail_location = cells[4] if len(cells) > 4 else ""

        theory_a, theory_a_phase = _strip_phase_annotation(theory_a_raw)
        theory_b, theory_b_phase = _strip_phase_annotation(theory_b_raw)

        # Strip bold markers from relationship
        relationship = relationship.replace("**", "").strip()

        entries.append({
            "theory_a": theory_a,
            "theory_a_phase": theory_a_phase,
            "theory_b": theory_b,
            "theory_b_phase": theory_b_phase,
            "relationship": relationship,
            "invariant_logic": invariant_logic,
            "expression_detail_location": expression_detail_location,
        })

    if not entries:
        raise ValueError(
            "Pairwise Interaction Table contains no parseable rows"
        )

    return entries


def parse_shared_upstream_warnings(matrix_text: str) -> list[dict]:
    """Parse the ## Shared Upstream Cause Warnings from INTERACTION_MATRIX.md.

    Returns list of dicts with keys:
    * ``shared_cause`` — description of the shared upstream cause
    * ``theories_affected`` — list of theory_id strings
    * ``discounting_note`` — guidance on how to handle double-counting
    """
    lines = matrix_text.split("\n")

    # Find section start (normalized: underscore/space/case)
    # Accepts both "Warnings" and "Warning" via startswith
    section_start = None
    for i, line in enumerate(lines):
        if _normalize_section_header(line).startswith(_SHARED_UPSTREAM_NORMALIZED):
            section_start = i + 1
            break

    if section_start is None:
        raise ValueError(
            "INTERACTION_MATRIX.md has no ## Shared Upstream Cause Warnings section"
        )

    # Section ends at next ## header or EOF
    section_end = len(lines)
    for i in range(section_start, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            if not _normalize_section_header(stripped).startswith(
                _SHARED_UPSTREAM_NORMALIZED
            ):
                section_end = i
                break

    entries: list[dict] = []
    in_table = False

    for i in range(section_start, section_end):
        stripped = lines[i].strip()

        if not stripped.startswith("|"):
            if in_table:
                in_table = False
            continue

        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c]

        if len(cells) < 3:
            continue

        # Skip separator rows
        if all(_SEPARATOR_CELL_RE.match(c) for c in cells):
            continue

        # First non-separator row is the header — skip it
        if not in_table:
            in_table = True
            continue

        # --- Data row ---
        shared_cause = cells[0]
        theories_affected_raw = cells[1]
        discounting_note = cells[2]

        theories_affected = _extract_theory_ids_from_ref(theories_affected_raw)

        entries.append({
            "shared_cause": shared_cause,
            "theories_affected": theories_affected,
            "discounting_note": discounting_note,
        })

    if not entries:
        raise ValueError(
            "Shared Upstream Cause Warnings contains no parseable rows"
        )

    return entries


def parse_interaction_matrix(
    matrix_text: str,
    known_theory_ids: set[str] | None = None,
) -> dict:
    """Parse INTERACTION_MATRIX.md into structured data.

    Returns dict with keys:
    * ``pairwise`` — list of pairwise interaction entries
    * ``shared_upstream_warnings`` — list of shared upstream cause warnings

    If *known_theory_ids* is provided, validates that every theory_id
    referenced in both tables exists in the set. Raises ValueError on
    unknown IDs.
    """
    pairwise = parse_interaction_pairwise(matrix_text)
    warnings = parse_shared_upstream_warnings(matrix_text)

    if known_theory_ids is not None:
        unknown: set[str] = set()

        for entry in pairwise:
            if entry["theory_a"] not in known_theory_ids:
                unknown.add(entry["theory_a"])
            if entry["theory_b"] not in known_theory_ids:
                unknown.add(entry["theory_b"])

        for entry in warnings:
            for tid in entry["theories_affected"]:
                if tid not in known_theory_ids:
                    unknown.add(tid)

        if unknown:
            raise ValueError(
                f"INTERACTION_MATRIX references unknown theory_ids: "
                f"{sorted(unknown)}"
            )

    return {
        "pairwise": pairwise,
        "shared_upstream_warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Unit 9: Interaction matrix filtering by activation status
# ---------------------------------------------------------------------------


def filter_interaction_matrix(
    matrix_data: dict,
    active_theory_ids: set[str],
) -> dict:
    """Filter parsed interaction matrix to rows relevant to active theories.

    Pairwise rows: kept when at least one theory is Active.
    Shared upstream warnings: kept when at least two affected theories are Active.

    Accepts *active_theory_ids* (not ActivationResult) so theory_loader
    stays independent of the activation schema.
    """
    pairwise = matrix_data.get("pairwise", [])
    warnings = matrix_data.get("shared_upstream_warnings", [])

    filtered_pairwise = [
        entry for entry in pairwise
        if entry["theory_a"] in active_theory_ids
        or entry["theory_b"] in active_theory_ids
    ]

    filtered_warnings = [
        entry for entry in warnings
        if sum(1 for t in entry["theories_affected"] if t in active_theory_ids) >= 2
    ]

    return {
        "pairwise": filtered_pairwise,
        "shared_upstream_warnings": filtered_warnings,
    }


# ---------------------------------------------------------------------------
# Unit 11: Theory package enrichment — typed objects on TheoryPackage
# ---------------------------------------------------------------------------


def build_indicator_ownership(activation_text: str) -> list[IndicatorOwnership]:
    """Convert parsed activation table entries into IndicatorOwnership objects.

    Each scored indicator in the activation_table becomes an IndicatorOwnership
    record.  Qualitative indicators never appear — ``parse_activation_table``
    rejects them with a hard error.
    """
    entries = parse_activation_table(activation_text)
    return [
        IndicatorOwnership(
            indicator_name=e["indicator_name"],
            metric_source=e["metric_source"],
            data_ownership=e["data_ownership"],
        )
        for e in entries
    ]


def build_context_flag_list(activation_text: str) -> list[ContextFlag]:
    """Convert parsed context flag entries into ContextFlag objects."""
    entries = parse_context_flags(activation_text)
    return [ContextFlag(**e) for e in entries]


def validate_required_sections(
    core_text: str, activation_text: str,
) -> None:
    """Pre-flight check that all required sections exist in theory package text.

    Normalizes headers before matching so underscore/space/case differences
    do not cause false negatives. Reports ALL missing sections in a single
    error rather than failing on the first.

    Required CORE.md sections: ``## theory_id``, ``## deep_falsifiers``.
    Required ACTIVATION.md sections: ``## activation_table``,
    ``## context_flags``, and at least one of ``## falsifier_severity_assignments``
    or ``## state_falsifiers``.
    """
    core_headers = {
        _normalize_section_header(line)
        for line in core_text.split("\n")
        if line.strip().startswith("## ")
    }
    act_headers = {
        _normalize_section_header(line)
        for line in activation_text.split("\n")
        if line.strip().startswith("## ")
    }

    missing: list[str] = []

    # theory_id: accept either ## section header or frontmatter pattern
    has_theory_id_header = "## theory id" in core_headers
    has_theory_id_frontmatter = bool(
        re.search(r"\*theory[_ ]id:\s*`?[^`*\n]+`?\*", core_text[:500], re.IGNORECASE)
    )
    if not has_theory_id_header and not has_theory_id_frontmatter:
        missing.append("CORE.md: ## theory_id (or frontmatter *theory_id: `...`*)")

    if "## deep falsifiers" not in core_headers:
        missing.append("CORE.md: ## deep_falsifiers")

    # activation_table may appear with a phase suffix, so use prefix check
    if not any(h == "## activation table" or h.startswith("## activation table ")
               for h in act_headers):
        missing.append("ACTIVATION.md: ## activation_table")

    if "## context flags" not in act_headers:
        missing.append("ACTIVATION.md: ## context_flags")

    has_sev = "## falsifier severity assignments" in act_headers
    has_state = "## state falsifiers" in act_headers
    if not has_sev and not has_state:
        missing.append(
            "ACTIVATION.md: ## falsifier_severity_assignments or ## state_falsifiers"
        )

    if missing:
        raise ValueError(
            f"Theory package missing required sections: {'; '.join(missing)}"
        )


def enrich_theory_package(pkg: TheoryPackage) -> TheoryPackage:
    """Populate enrichment fields on a loaded theory package.

    Attaches:
    - falsifier_registry: pre-joined FalsifierEntry objects (CORE + ACTIVATION)
    - data_ownership: IndicatorOwnership objects from activation_table
    - context_flags: ContextFlag objects from context_flags section

    Runs ``validate_required_sections`` as a pre-flight gate before parsing.
    Returns a new TheoryPackage; the original is not modified.
    """
    validate_required_sections(pkg.core, pkg.activation)
    registry = build_falsifier_registry(pkg.core, pkg.activation)
    ownership = build_indicator_ownership(pkg.activation)
    flags = build_context_flag_list(pkg.activation)
    return pkg.model_copy(update={
        "falsifier_registry": registry,
        "data_ownership": ownership,
        "context_flags": flags,
    })


# ---------------------------------------------------------------------------
# Unit 15: REGISTRY_INDEX.md generation
# ---------------------------------------------------------------------------

_STABILITY_MARKER_RE = re.compile(r"stability[_ ]class", re.IGNORECASE)


def _extract_stability_class(core_text: str) -> str:
    """Extract stability_class ('persistent' or 'cyclical') from CORE.md.

    Handles all formatting variations across the 8 theory modules:
    frontmatter (``*stability_class: cyclical*``), section headers
    (``## stability_class``), bold markers, backtick wrapping, etc.

    Strategy: find the first "stability class" marker, then search for the
    keyword within the next 300 characters. This avoids fragile markdown
    structure parsing.
    """
    m = _STABILITY_MARKER_RE.search(core_text)
    if m is None:
        return "unknown"
    window = core_text[m.end():m.end() + 300].lower()
    if "persistent" in window:
        return "persistent"
    if "cyclical" in window:
        return "cyclical"
    return "unknown"


def _extract_phase_summary(activation_text: str) -> tuple[int, list[str]]:
    """Extract phase count and human-readable labels from ACTIVATION.md.

    Reuses ``parse_activation_table`` — the same parser the activation engine
    relies on — to detect phases from scored indicators, then extracts labels
    from the phase strings (e.g. ``"Phase A: Expansion"`` → ``"Expansion"``).

    Returns ``(phase_count, [labels])``.  Single-phase: ``(1, [])``.
    """
    entries = parse_activation_table(activation_text)
    phases_present = sorted({e["phase"] for e in entries if e["phase"]})
    if len(phases_present) < 2:
        return (1, [])
    labels: list[str] = []
    for phase_str in phases_present:
        lm = re.search(r"Phase\s+[AB]:\s*(.+)", phase_str)
        labels.append(lm.group(1).strip() if lm else phase_str)
    return (len(labels), labels)


def generate_registry_index(
    packages: list[TheoryPackage],
    output_path: Path | None = None,
) -> str:
    """Generate theories/REGISTRY_INDEX.md — mechanical summary of the theory registry.

    Writes a markdown table with one row per theory: theory_id, stability_class,
    phases, phase_names, falsifier counts, indicator count, context flag count.

    This is a convenience file for LLM orientation — the LLM reads
    REGISTRY_INDEX.md first to understand what theories exist before touching
    individual packages. Regenerated on every loader run; should not be
    manually edited.

    Returns the generated markdown content.
    """
    lines: list[str] = [
        "<!-- REGISTRY_INDEX.md -- Auto-generated. Do not edit manually. -->",
        "# Theory Registry Index",
        "",
        (
            "| theory_id | stability_class | phases | phase_names "
            "| falsifier_count (hard) | falsifier_count (soft) "
            "| indicator_count | context_flag_count |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for pkg in sorted(packages, key=lambda p: p.theory_id):
        stability = _extract_stability_class(pkg.core)
        phase_count, phase_labels = _extract_phase_summary(pkg.activation)
        phase_names = " / ".join(phase_labels) if phase_labels else "-"
        hard = sum(1 for f in pkg.falsifier_registry if f.classification == "hard")
        soft = sum(1 for f in pkg.falsifier_registry if f.classification == "soft")
        indicators = len(pkg.data_ownership)
        ctx_flags = len(pkg.context_flags)
        lines.append(
            f"| {pkg.theory_id} | {stability} | {phase_count} | {phase_names} "
            f"| {hard} | {soft} | {indicators} | {ctx_flags} |"
        )

    content = "\n".join(lines) + "\n"
    target = output_path or (THEORIES_DIR / "REGISTRY_INDEX.md")
    target.write_text(content, encoding="utf-8")
    return content
