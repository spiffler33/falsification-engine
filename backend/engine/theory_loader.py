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
from backend.schemas.theory import FalsifierEntry, Severity, TheoryPackage

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

_ACTIVATION_TABLE_RE = re.compile(
    r"^##\s+activation_table(?:\s*[—–\-]+\s*(.+))?$", re.IGNORECASE,
)

_WEIGHT_NUM_RE = re.compile(r"[\d.]+")


def _parse_activation_rows(
    lines: list[str], start: int, end: int, header_phase: str | None,
) -> list[dict]:
    """Parse indicator rows from an activation_table section.

    *header_phase* overrides phase for all rows (debt_cycle_short pattern).
    Within the section, ``### Phase A/B:`` subsections update the current phase
    (structural_fragility / capital_flows pattern).
    """
    entries: list[dict] = []
    current_phase = header_phase
    in_table = False

    for i in range(start, end):
        stripped = lines[i].strip()

        # Track ### Phase subsections
        pm = _PHASE_SUBSECTION_RE.match(stripped)
        if pm:
            current_phase = pm.group(1).strip()
            in_table = False
            continue

        # Non-table line resets table state
        if not stripped.startswith("|"):
            if in_table:
                in_table = False
            continue

        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c]

        if len(cells) < 6:
            continue

        # Skip separator rows
        if all(_SEPARATOR_CELL_RE.match(c) for c in cells):
            continue

        # First non-separator table row is the header — skip it
        if not in_table:
            in_table = True
            continue

        # --- Data row ---
        # Columns: Indicator | Metric Source | Data Ownership | Threshold
        #          | Direction | Weight | Calibration Rationale
        indicator_name = cells[0]
        metric_source = cells[1]
        ownership_raw = cells[2]
        threshold = cells[3]
        direction = cells[4]
        weight_str = cells[5]

        # Extract data ownership keyword
        om = _OWNERSHIP_KW_RE.search(ownership_raw)
        if om:
            data_ownership = om.group(1).lower()
        else:
            # Fallback: strip backticks and take first token
            stripped_own = ownership_raw.strip("`").strip()
            data_ownership = stripped_own.split()[0].lower() if stripped_own else ""

        # Parse weight (may have annotations like `[CALIBRATION]`)
        wm = _WEIGHT_NUM_RE.search(weight_str)
        if not wm:
            continue  # Not a data row
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
    ranges: list[tuple[int, int, str | None]] = []
    for i, line in enumerate(lines):
        m = _ACTIVATION_TABLE_RE.match(line.strip())
        if m:
            phase = m.group(1).strip() if m.group(1) else None
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

_CONTEXT_FLAG_SECTION_RE = re.compile(
    r"^##\s+context_flags\s*$", re.IGNORECASE,
)

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

    # Find ## context_flags section
    section_start = None
    for i, line in enumerate(lines):
        if _CONTEXT_FLAG_SECTION_RE.match(line.strip()):
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

        # Data ownership: extract from column, or default to qualitative
        if "data_ownership" in col_map:
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

    return entries
