# test_theory_loader.py — Tests for v8 theory package loader (Units 2-5).
import re
from pathlib import Path

import pytest

from backend.config import THEORIES_DIR
from backend.engine.theory_loader import (
    build_falsifier_registry,
    discover_theory_dirs,
    load_all_theory_packages,
    load_theory_package,
    parse_activation_table,
    parse_context_flags,
    parse_deep_falsifiers,
    parse_falsifier_severity,
    parse_interaction_matrix,
    parse_interaction_pairwise,
    parse_shared_upstream_warnings,
)
from backend.schemas.theory import FalsifierEntry

EXPECTED_THEORY_IDS = {
    "capital_flows",
    "debt_cycle_long",
    "debt_cycle_short",
    "fiscal_dominance_arithmetic",
    "fiscal_dominance_liquidity",
    "monetary_architecture",
    "structural_fragility",
    "valuation_mean_reversion",
}


# ---------------------------------------------------------------------------
# discover_theory_dirs
# ---------------------------------------------------------------------------

class TestDiscoverTheoryDirs:

    def test_discovers_all_eight_dirs(self):
        dirs = discover_theory_dirs()
        assert len(dirs) == 8

    def test_all_dirs_are_v2(self):
        dirs = discover_theory_dirs()
        for d in dirs:
            assert d.name.endswith("_v2"), f"Unexpected dir name: {d.name}"

    def test_dirs_are_sorted(self):
        dirs = discover_theory_dirs()
        names = [d.name for d in dirs]
        assert names == sorted(names)

    def test_missing_file_raises_with_file_name(self, tmp_path):
        theory_dir = tmp_path / "THEORY_MODULE_test_theory_v2"
        theory_dir.mkdir()
        (theory_dir / "CORE.md").write_text("# test")
        (theory_dir / "ACTIVATION.md").write_text("# test")
        (theory_dir / "TACTICAL.md").write_text("# test")
        # PLAYBOOK.md is deliberately missing

        with pytest.raises(FileNotFoundError, match="PLAYBOOK.md"):
            discover_theory_dirs(tmp_path)

    def test_missing_multiple_files_lists_all(self, tmp_path):
        theory_dir = tmp_path / "THEORY_MODULE_sparse_v2"
        theory_dir.mkdir()
        (theory_dir / "CORE.md").write_text("# test")
        # Missing ACTIVATION.md, TACTICAL.md, PLAYBOOK.md

        with pytest.raises(FileNotFoundError, match="ACTIVATION.md") as exc_info:
            discover_theory_dirs(tmp_path)
        assert "TACTICAL.md" in str(exc_info.value)
        assert "PLAYBOOK.md" in str(exc_info.value)

    def test_ignores_non_matching_dirs(self, tmp_path):
        # Valid dir
        good = tmp_path / "THEORY_MODULE_good_v2"
        good.mkdir()
        for f in ("CORE.md", "ACTIVATION.md", "TACTICAL.md", "PLAYBOOK.md"):
            (good / f).write_text("# placeholder")

        # Non-matching dirs that should be ignored
        (tmp_path / "old_format").mkdir()
        (tmp_path / "INTERACTION_MATRIX.md").write_text("# matrix")
        (tmp_path / "some_other_dir").mkdir()

        dirs = discover_theory_dirs(tmp_path)
        assert len(dirs) == 1
        assert dirs[0].name == "THEORY_MODULE_good_v2"


# ---------------------------------------------------------------------------
# load_theory_package
# ---------------------------------------------------------------------------

class TestLoadTheoryPackage:

    def test_all_packages_have_nonempty_fields(self):
        for d in discover_theory_dirs():
            pkg = load_theory_package(d)
            assert pkg.core, f"{d.name}: core is empty"
            assert pkg.activation, f"{d.name}: activation is empty"
            assert pkg.tactical, f"{d.name}: tactical is empty"
            assert pkg.playbook, f"{d.name}: playbook is empty"

    def test_theory_ids_match_expected(self):
        loaded_ids = {load_theory_package(d).theory_id for d in discover_theory_dirs()}
        assert loaded_ids == EXPECTED_THEORY_IDS

    def test_arithmatic_dir_loads_arithmetic_id(self):
        """Directory has typo 'arithmatic' but theory_id from CORE.md is 'arithmetic'."""
        dir_path = THEORIES_DIR / "THEORY_MODULE_fiscal_dominance_arithmatic_v2"
        pkg = load_theory_package(dir_path)
        assert pkg.theory_id == "fiscal_dominance_arithmetic"

    def test_registries_empty_on_load(self):
        """Registries are populated by later units, not the loader."""
        for d in discover_theory_dirs():
            pkg = load_theory_package(d)
            assert pkg.falsifier_registry == [], f"{pkg.theory_id}: falsifier_registry not empty"
            assert pkg.data_ownership == [], f"{pkg.theory_id}: data_ownership not empty"
            assert pkg.context_flags == [], f"{pkg.theory_id}: context_flags not empty"

    def test_theory_id_extraction_section_header(self, tmp_path):
        """Pattern 1: ## theory_id section with backtick-wrapped value."""
        d = tmp_path / "THEORY_MODULE_test_v2"
        d.mkdir()
        (d / "CORE.md").write_text("# Test Theory\n\n## theory_id\n\n`test_theory`\n")
        (d / "ACTIVATION.md").write_text("# act")
        (d / "TACTICAL.md").write_text("# tac")
        (d / "PLAYBOOK.md").write_text("# play")

        pkg = load_theory_package(d)
        assert pkg.theory_id == "test_theory"

    def test_theory_id_extraction_frontmatter(self, tmp_path):
        """Pattern 2: *theory_id: `...`* in frontmatter."""
        d = tmp_path / "THEORY_MODULE_test_v2"
        d.mkdir()
        (d / "CORE.md").write_text("# Test\n\n*theory_id: `frontmatter_test`*\n\n## core_claim\n")
        (d / "ACTIVATION.md").write_text("# act")
        (d / "TACTICAL.md").write_text("# tac")
        (d / "PLAYBOOK.md").write_text("# play")

        pkg = load_theory_package(d)
        assert pkg.theory_id == "frontmatter_test"

    def test_theory_id_extraction_fails_gracefully(self, tmp_path):
        """CORE.md with no recognizable theory_id raises ValueError."""
        d = tmp_path / "THEORY_MODULE_bad_v2"
        d.mkdir()
        (d / "CORE.md").write_text("# No theory id here\n\nJust some text.\n")
        (d / "ACTIVATION.md").write_text("# act")
        (d / "TACTICAL.md").write_text("# tac")
        (d / "PLAYBOOK.md").write_text("# play")

        with pytest.raises(ValueError, match="Could not extract theory_id"):
            load_theory_package(d)


# ---------------------------------------------------------------------------
# load_all_theory_packages
# ---------------------------------------------------------------------------

class TestLoadAllTheoryPackages:

    def test_loads_all_eight(self):
        packages = load_all_theory_packages()
        assert len(packages) == 8

    def test_all_ids_present(self):
        packages = load_all_theory_packages()
        loaded_ids = {p.theory_id for p in packages}
        assert loaded_ids == EXPECTED_THEORY_IDS

    def test_no_partial_load_on_missing_file(self, tmp_path):
        """If one directory is invalid, the entire load fails."""
        for name in ("THEORY_MODULE_good1_v2", "THEORY_MODULE_good2_v2"):
            d = tmp_path / name
            d.mkdir()
            for f in ("CORE.md", "ACTIVATION.md", "TACTICAL.md", "PLAYBOOK.md"):
                (d / f).write_text("# placeholder")

        bad = tmp_path / "THEORY_MODULE_bad_v2"
        bad.mkdir()
        (bad / "CORE.md").write_text("# test")

        with pytest.raises(FileNotFoundError):
            load_all_theory_packages(tmp_path)


# ---------------------------------------------------------------------------
# parse_deep_falsifiers — Unit 3
# ---------------------------------------------------------------------------

# Expected falsifier ID pattern: uppercase letter prefix + digits (H1, S4, DF3, etc.)
_FALSIFIER_ID_RE = re.compile(r"^[A-Z]+\d+$")


class TestParseDeepFalsifiersLive:
    """Tests against the real CORE.md files in the repo."""

    @pytest.fixture()
    def all_core_texts(self):
        """Load core text for all 8 theories."""
        dirs = discover_theory_dirs()
        return {
            load_theory_package(d).theory_id: load_theory_package(d).core
            for d in dirs
        }

    def test_all_eight_parse_successfully(self, all_core_texts):
        for theory_id, core_text in all_core_texts.items():
            entries = parse_deep_falsifiers(core_text)
            assert len(entries) >= 2, f"{theory_id}: expected at least 2 falsifiers"

    def test_each_entry_has_nonempty_fields(self, all_core_texts):
        for theory_id, core_text in all_core_texts.items():
            for entry in parse_deep_falsifiers(core_text):
                assert entry["falsifier_id"], f"{theory_id}: empty falsifier_id"
                assert entry["condition"], f"{theory_id}: empty condition"
                assert entry["logic"], f"{theory_id}: empty logic"

    def test_falsifier_ids_follow_pattern(self, all_core_texts):
        for theory_id, core_text in all_core_texts.items():
            for entry in parse_deep_falsifiers(core_text):
                fid = entry["falsifier_id"]
                assert _FALSIFIER_ID_RE.match(fid), (
                    f"{theory_id}: falsifier_id {fid!r} does not match [HS]\\d+ pattern"
                )

    def test_monetary_architecture_has_hard_and_soft(self, all_core_texts):
        """monetary_architecture has both H-prefix and S-prefix entries (two sub-tables)."""
        entries = parse_deep_falsifiers(all_core_texts["monetary_architecture"])
        ids = [e["falsifier_id"] for e in entries]
        hard_ids = [i for i in ids if i.startswith("H")]
        soft_ids = [i for i in ids if i.startswith("S")]
        assert len(hard_ids) >= 1, "Expected at least one hard falsifier"
        assert len(soft_ids) >= 1, "Expected at least one soft falsifier"

    def test_no_duplicate_ids_per_theory(self, all_core_texts):
        for theory_id, core_text in all_core_texts.items():
            entries = parse_deep_falsifiers(core_text)
            ids = [e["falsifier_id"] for e in entries]
            assert len(ids) == len(set(ids)), (
                f"{theory_id}: duplicate falsifier_ids: {ids}"
            )


class TestParseDeepFalsifiersSynthetic:
    """Tests with synthetic markdown to verify parser edge cases."""

    def test_basic_table_hash_header(self):
        """Standard format with | # | header."""
        text = (
            "## deep_falsifiers\n\n"
            "| # | Condition | Logic |\n"
            "|---|-----------|-------|\n"
            "| H1 | Price drops 50% | Market crash invalidates |\n"
            "| H2 | GDP grows 5% | Growth falsifies |\n"
            "\n---\n\n## stability_class\n"
        )
        entries = parse_deep_falsifiers(text)
        assert len(entries) == 2
        assert entries[0] == {
            "falsifier_id": "H1",
            "condition": "Price drops 50%",
            "logic": "Market crash invalidates",
        }
        assert entries[1]["falsifier_id"] == "H2"

    def test_basic_table_id_header(self):
        """Format with | ID | header."""
        text = (
            "## deep_falsifiers\n\n"
            "Some preamble text.\n\n"
            "| ID | Condition | Logic |\n"
            "|----|-----------|-------|\n"
            "| H1 | Condition one | Logic one |\n"
        )
        entries = parse_deep_falsifiers(text)
        assert len(entries) == 1
        assert entries[0]["falsifier_id"] == "H1"

    def test_multiple_sub_tables(self):
        """Two sub-tables under ### headers (monetary_architecture pattern)."""
        text = (
            "## deep_falsifiers\n\n"
            "*Severity in ACTIVATION.md.*\n\n"
            "### Theory-Killing Conditions\n\n"
            "| ID | Condition | Logic |\n"
            "|----|-----------|-------|\n"
            "| H1 | Hard condition | Hard logic |\n\n"
            "### Theory-Modifying Conditions\n\n"
            "| ID | Condition | Logic |\n"
            "|----|-----------|-------|\n"
            "| S1 | Soft condition | Soft logic |\n"
            "| S4 | Another soft | More logic |\n\n"
            "---\n\n## revision_triggers\n"
        )
        entries = parse_deep_falsifiers(text)
        assert len(entries) == 3
        ids = [e["falsifier_id"] for e in entries]
        assert ids == ["H1", "S1", "S4"]

    def test_missing_section_raises(self):
        text = "## core_claim\n\nSome text.\n\n## stability_class\n"
        with pytest.raises(ValueError, match="no ## deep_falsifiers section"):
            parse_deep_falsifiers(text)

    def test_empty_table_raises(self):
        text = (
            "## deep_falsifiers\n\n"
            "No table here, just text.\n\n"
            "## stability_class\n"
        )
        with pytest.raises(ValueError, match="no parseable table rows"):
            parse_deep_falsifiers(text)

    def test_section_stops_at_next_h2(self):
        """Parser should NOT include tables from the next ## section."""
        text = (
            "## deep_falsifiers\n\n"
            "| # | Condition | Logic |\n"
            "|---|-----------|-------|\n"
            "| H1 | Condition A | Logic A |\n\n"
            "## historical_episodes\n\n"
            "| Episode | Features | Lesson |\n"
            "|---------|----------|--------|\n"
            "| 2008 | Credit | Crash |\n"
        )
        entries = parse_deep_falsifiers(text)
        assert len(entries) == 1
        assert entries[0]["falsifier_id"] == "H1"

    def test_preamble_text_before_table_ignored(self):
        """Non-table lines between section header and table are ignored."""
        text = (
            "## deep_falsifiers\n\n"
            "These conditions would kill the theory ITSELF.\n"
            "Severity is assigned in ACTIVATION.md.\n\n"
            "| # | Condition | Logic |\n"
            "|---|-----------|-------|\n"
            "| H1 | Cond | Log |\n"
        )
        entries = parse_deep_falsifiers(text)
        assert len(entries) == 1


# ---------------------------------------------------------------------------
# parse_falsifier_severity — Unit 4
# ---------------------------------------------------------------------------

_VALID_CLASSIFICATIONS = {"hard", "soft"}
_VALID_SEVERITIES = {"minor", "medium", "major"}
_VALID_SOURCES = {"core", "state"}


class TestParseFalsifierSeverityLive:
    """Tests against the real ACTIVATION.md files in the repo."""

    @pytest.fixture()
    def all_activation_texts(self):
        dirs = discover_theory_dirs()
        return {
            load_theory_package(d).theory_id: load_theory_package(d).activation
            for d in dirs
        }

    def test_all_eight_parse_successfully(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            entries = parse_falsifier_severity(text)
            assert len(entries) >= 3, f"{theory_id}: expected at least 3 entries"

    def test_each_entry_has_valid_fields(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            for entry in parse_falsifier_severity(text):
                assert entry["falsifier_id"], f"{theory_id}: empty falsifier_id"
                assert entry["classification"] in _VALID_CLASSIFICATIONS, (
                    f"{theory_id}: bad classification {entry['classification']!r}"
                )
                assert entry["source"] in _VALID_SOURCES, (
                    f"{theory_id}: bad source {entry['source']!r}"
                )

    def test_hard_falsifiers_have_no_severity(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            for entry in parse_falsifier_severity(text):
                if entry["classification"] == "hard":
                    assert entry["severity"] is None, (
                        f"{theory_id} {entry['falsifier_id']}: hard should have None severity"
                    )

    def test_soft_falsifiers_have_severity(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            for entry in parse_falsifier_severity(text):
                if entry["classification"] == "soft":
                    assert entry["severity"] in _VALID_SEVERITIES, (
                        f"{theory_id} {entry['falsifier_id']}: soft needs minor/medium/major"
                    )

    def test_state_entries_have_condition_and_logic(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            for entry in parse_falsifier_severity(text):
                if entry["source"] == "state":
                    assert entry.get("condition"), (
                        f"{theory_id} {entry['falsifier_id']}: state entry empty condition"
                    )
                    assert entry.get("logic"), (
                        f"{theory_id} {entry['falsifier_id']}: state entry empty logic"
                    )

    def test_core_entries_have_no_condition(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            for entry in parse_falsifier_severity(text):
                if entry["source"] == "core":
                    assert "condition" not in entry, (
                        f"{theory_id} {entry['falsifier_id']}: core should not have condition"
                    )

    def test_no_duplicate_ids_per_theory(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            entries = parse_falsifier_severity(text)
            ids = [e["falsifier_id"] for e in entries]
            assert len(ids) == len(set(ids)), (
                f"{theory_id}: duplicate IDs: {[x for x in ids if ids.count(x) > 1]}"
            )

    # --- Theory-specific structural assertions ---

    def test_structural_fragility_inline_state(self, all_activation_texts):
        """structural_fragility: state falsifiers inline in falsifier_severity_assignments."""
        entries = parse_falsifier_severity(all_activation_texts["structural_fragility"])
        hard = [e for e in entries if e["classification"] == "hard"]
        soft = [e for e in entries if e["classification"] == "soft"]
        assert len(hard) >= 4, "Expected H1-H4 hard falsifiers"
        assert len(soft) >= 3, "Expected S1-S3 soft falsifiers"

    def test_valuation_mean_reversion_separate_state(self, all_activation_texts):
        """valuation_mean_reversion: separate ## state_falsifiers section."""
        entries = parse_falsifier_severity(all_activation_texts["valuation_mean_reversion"])
        hard = [e for e in entries if e["classification"] == "hard"]
        state = [e for e in entries if e["source"] == "state"]
        assert len(hard) >= 3, "Expected H1-H3"
        assert len(state) >= 5, "Expected S1-S5"

    def test_monetary_architecture_core_soft(self, all_activation_texts):
        """monetary_architecture: S1, S4 are soft but sourced from CORE.md."""
        entries = parse_falsifier_severity(all_activation_texts["monetary_architecture"])
        core_soft = [e for e in entries if e["source"] == "core" and e["classification"] == "soft"]
        assert len(core_soft) >= 2, "Expected S1, S4 as core-sourced soft falsifiers"

    def test_fiscal_dominance_liquidity_df_prefix(self, all_activation_texts):
        """fiscal_dominance_liquidity: uses DF prefix for theory-level falsifiers."""
        entries = parse_falsifier_severity(all_activation_texts["fiscal_dominance_liquidity"])
        df_entries = [e for e in entries if str(e["falsifier_id"]).startswith("DF")]
        assert len(df_entries) >= 3, "Expected DF1-DF3"
        for e in df_entries:
            assert e["classification"] == "hard"
            assert e["source"] == "core"

    def test_debt_cycle_short_dedup(self, all_activation_texts):
        """debt_cycle_short: S entries deduplicated in favour of state_falsifiers detail."""
        entries = parse_falsifier_severity(all_activation_texts["debt_cycle_short"])
        s_entries = [e for e in entries if str(e["falsifier_id"]).startswith("S")]
        for e in s_entries:
            assert e.get("condition"), (
                f"S entry {e['falsifier_id']} should have condition after dedup"
            )

    def test_capital_flows_auto_id_state(self, all_activation_texts):
        """capital_flows: unnamed state_falsifiers entries get auto-generated IDs."""
        entries = parse_falsifier_severity(all_activation_texts["capital_flows"])
        auto = [e for e in entries if str(e["falsifier_id"]).startswith("ST_")]
        assert len(auto) >= 1, "Expected auto-generated IDs for unnamed state entries"


class TestParseFalsifierSeveritySynthetic:
    """Tests with synthetic markdown to verify parser edge cases."""

    def test_basic_theory_and_state(self):
        text = (
            "## falsifier_severity_assignments\n\n"
            "### Theory-level falsifiers\n\n"
            "| Falsifier | Severity | Rationale |\n"
            "|-----------|----------|----------|\n"
            "| H1 \u2014 Hard condition one | **Hard** | Kills theory |\n"
            "| H2 \u2014 Hard condition two | **theory-killing** | Also kills |\n\n"
            "### State-level falsifiers\n\n"
            "| # | Condition | Severity | Implication |\n"
            "|---|-----------|----------|-------------|\n"
            "| S1 | Rates drop | **major** (0.45) | Caps magnitude |\n"
            "| S2 | Growth surge | **minor** (0.10) | Extends timeline |\n"
        )
        entries = parse_falsifier_severity(text)
        assert len(entries) == 4

        hard = [e for e in entries if e["classification"] == "hard"]
        soft = [e for e in entries if e["classification"] == "soft"]
        assert len(hard) == 2
        assert len(soft) == 2

        for h in hard:
            assert h["source"] == "core"
            assert h["severity"] is None
            assert "condition" not in h

        s1 = next(e for e in entries if e["falsifier_id"] == "S1")
        assert s1["severity"] == "major"
        assert s1["source"] == "state"
        assert s1["condition"] == "Rates drop"
        assert s1["logic"] == "Caps magnitude"

    def test_separate_state_section(self):
        text = (
            "## falsifier_severity_assignments\n\n"
            "| Falsifier | Severity | Rationale |\n"
            "|-----------|----------|----------|\n"
            "| H1 \u2014 Kill condition | **Hard** | Theory dead |\n\n"
            "---\n\n"
            "## state_falsifiers\n\n"
            "| # | Condition | Severity | Implication |\n"
            "|---|-----------|----------|-------------|\n"
            "| S1 | Dollar drops | **medium** (0.25) | Changes expression |\n"
        )
        entries = parse_falsifier_severity(text)
        assert len(entries) == 2

        h1 = next(e for e in entries if e["falsifier_id"] == "H1")
        assert h1["classification"] == "hard"
        assert h1["source"] == "core"

        s1 = next(e for e in entries if e["falsifier_id"] == "S1")
        assert s1["severity"] == "medium"
        assert s1["source"] == "state"
        assert s1["condition"] == "Dollar drops"

    def test_consolidated_table_with_location(self):
        """debt_cycle_short pattern: single table with Location column."""
        text = (
            "## falsifier_severity_assignments\n\n"
            "| Falsifier | Location | Severity | Discount |\n"
            "|-----------|----------|----------|----------|\n"
            "| H1 (hard cond) | CORE.md deep_falsifiers | hard \u2014 binary kill | Override |\n"
            "| S1 (soft cond) | ACTIVATION.md state_falsifiers | medium | 0.25 |\n"
        )
        entries = parse_falsifier_severity(text)
        assert len(entries) == 2

        h1 = next(e for e in entries if e["falsifier_id"] == "H1")
        assert h1["source"] == "core"
        assert h1["classification"] == "hard"

        s1 = next(e for e in entries if e["falsifier_id"] == "S1")
        assert s1["source"] == "state"
        assert s1["severity"] == "medium"

    def test_dedup_prefers_condition(self):
        """When same ID appears in both sections, prefer the one with condition."""
        text = (
            "## state_falsifiers\n\n"
            "| # | Condition | Severity | Implication |\n"
            "|---|-----------|----------|-------------|\n"
            "| S1 | Full condition text | **major** (0.45) | Full logic |\n\n"
            "---\n\n"
            "## falsifier_severity_assignments\n\n"
            "| Falsifier | Location | Severity | Discount |\n"
            "|-----------|----------|----------|----------|\n"
            "| H1 (kill) | CORE.md | hard | Override |\n"
            "| S1 (brief) | ACTIVATION.md state_falsifiers | major | 0.45 |\n"
        )
        entries = parse_falsifier_severity(text)
        assert len(entries) == 2

        s1 = next(e for e in entries if e["falsifier_id"] == "S1")
        assert s1["condition"] == "Full condition text"
        assert s1["logic"] == "Full logic"

    def test_classification_column(self):
        """monetary_architecture pattern: explicit Classification column."""
        text = (
            "## falsifier_severity_assignments\n\n"
            "### Deep Falsifiers (from CORE.md)\n\n"
            "| ID | Condition | Classification | Severity | Notes |\n"
            "|----|-----------|---------------|----------|-------|\n"
            "| H1 | Gold selling | **hard** | Theory-killing | No discount |\n"
            "| S1 | RMB stalls | **soft** | **minor** (0.10) | Changes endpoint |\n\n"
            "### State-Level Falsifiers\n\n"
            "| ID | Condition | Severity | Implication |\n"
            "|----|-----------|----------|-------------|\n"
            "| S3 | Fiscal improves | **medium** (0.25) | Removes demand |\n"
        )
        entries = parse_falsifier_severity(text)
        assert len(entries) == 3

        h1 = next(e for e in entries if e["falsifier_id"] == "H1")
        assert h1["classification"] == "hard"
        assert h1["source"] == "core"

        s1 = next(e for e in entries if e["falsifier_id"] == "S1")
        assert s1["classification"] == "soft"
        assert s1["severity"] == "minor"
        assert s1["source"] == "core"
        assert "condition" not in s1

        s3 = next(e for e in entries if e["falsifier_id"] == "S3")
        assert s3["source"] == "state"
        assert s3["condition"] == "Fiscal improves"

    def test_auto_id_for_unnamed_entries(self):
        """Entries without recognized IDs get auto-generated ST_ prefixed IDs."""
        text = (
            "## state_falsifiers\n\n"
            "| Condition | Phase | Severity | Description |\n"
            "|-----------|-------|----------|-------------|\n"
            "| Dollar reverses | B | **major** (0.45) | Rotation aborts |\n"
            "| Growth stalls | A | **medium** (0.25) | Slows timeline |\n"
        )
        entries = parse_falsifier_severity(text)
        assert len(entries) == 2
        assert entries[0]["falsifier_id"] == "ST_1"
        assert entries[1]["falsifier_id"] == "ST_2"
        assert entries[0]["condition"] == "Dollar reverses"
        assert entries[0]["severity"] == "major"

    def test_no_section_raises(self):
        text = "## phases\n\nSome content.\n\n## activation_table\n"
        with pytest.raises(ValueError, match="no.*section"):
            parse_falsifier_severity(text)

    def test_empty_tables_raises(self):
        text = (
            "## falsifier_severity_assignments\n\n"
            "No tables here, just prose.\n\n"
            "## context_flags\n"
        )
        with pytest.raises(ValueError, match="no parseable entries"):
            parse_falsifier_severity(text)

    def test_embedded_condition_in_id_cell(self):
        """capital_flows pattern: condition embedded after ID with colon."""
        text = (
            "## falsifier_severity_assignments\n\n"
            "### Soft Falsifiers (State-Level)\n\n"
            "| Falsifier | Severity | Discount | Rationale |\n"
            "|-----------|----------|----------|----------|\n"
            "| S1: China crisis deepens | **major** | 0.45 | Caps magnitude |\n"
        )
        entries = parse_falsifier_severity(text)
        assert len(entries) == 1
        assert entries[0]["falsifier_id"] == "S1"
        assert entries[0]["source"] == "state"
        assert entries[0]["condition"] == "China crisis deepens"
        assert entries[0]["logic"] == "Caps magnitude"


# ---------------------------------------------------------------------------
# build_falsifier_registry — Unit 5
# ---------------------------------------------------------------------------


class TestBuildFalsifierRegistryLive:
    """Tests against the real CORE.md + ACTIVATION.md files for all 8 theories."""

    @pytest.fixture()
    def all_packages(self):
        dirs = discover_theory_dirs()
        return {
            load_theory_package(d).theory_id: load_theory_package(d)
            for d in dirs
        }

    def test_all_eight_build_successfully(self, all_packages):
        for theory_id, pkg in all_packages.items():
            registry = build_falsifier_registry(pkg.core, pkg.activation)
            assert len(registry) >= 3, (
                f"{theory_id}: expected at least 3 registry entries"
            )

    def test_returns_falsifier_entry_objects(self, all_packages):
        for theory_id, pkg in all_packages.items():
            registry = build_falsifier_registry(pkg.core, pkg.activation)
            for entry in registry:
                assert isinstance(entry, FalsifierEntry), (
                    f"{theory_id}: expected FalsifierEntry, got {type(entry)}"
                )

    def test_all_entries_have_condition_and_logic(self, all_packages):
        for theory_id, pkg in all_packages.items():
            for entry in build_falsifier_registry(pkg.core, pkg.activation):
                assert entry.condition, (
                    f"{theory_id} {entry.falsifier_id}: empty condition"
                )
                assert entry.logic, (
                    f"{theory_id} {entry.falsifier_id}: empty logic"
                )

    def test_hard_entries_have_no_severity_or_discount(self, all_packages):
        for theory_id, pkg in all_packages.items():
            for entry in build_falsifier_registry(pkg.core, pkg.activation):
                if entry.classification == "hard":
                    assert entry.severity is None, (
                        f"{theory_id} {entry.falsifier_id}: hard should have no severity"
                    )
                    assert entry.discount is None, (
                        f"{theory_id} {entry.falsifier_id}: hard should have no discount"
                    )

    def test_soft_entries_have_severity_and_discount(self, all_packages):
        for theory_id, pkg in all_packages.items():
            for entry in build_falsifier_registry(pkg.core, pkg.activation):
                if entry.classification == "soft":
                    assert entry.severity is not None, (
                        f"{theory_id} {entry.falsifier_id}: soft needs severity"
                    )
                    assert entry.discount is not None, (
                        f"{theory_id} {entry.falsifier_id}: soft needs discount"
                    )

    def test_discount_values_match_severity(self, all_packages):
        expected = {"minor": 0.10, "medium": 0.25, "major": 0.45}
        for theory_id, pkg in all_packages.items():
            for entry in build_falsifier_registry(pkg.core, pkg.activation):
                if entry.severity:
                    assert entry.discount == expected[entry.severity.value], (
                        f"{theory_id} {entry.falsifier_id}: "
                        f"severity={entry.severity} but discount={entry.discount}"
                    )

    def test_no_duplicate_ids_per_theory(self, all_packages):
        for theory_id, pkg in all_packages.items():
            registry = build_falsifier_registry(pkg.core, pkg.activation)
            ids = [e.falsifier_id for e in registry]
            assert len(ids) == len(set(ids)), (
                f"{theory_id}: duplicate IDs in registry: "
                f"{[x for x in ids if ids.count(x) > 1]}"
            )

    def test_registry_covers_all_core_ids(self, all_packages):
        """Every CORE.md deep_falsifier ID appears in the registry."""
        for theory_id, pkg in all_packages.items():
            core_ids = {
                e["falsifier_id"] for e in parse_deep_falsifiers(pkg.core)
            }
            registry_ids = {
                e.falsifier_id
                for e in build_falsifier_registry(pkg.core, pkg.activation)
            }
            missing = core_ids - registry_ids
            assert not missing, (
                f"{theory_id}: CORE.md IDs missing from registry: {missing}"
            )

    def test_monetary_architecture_has_core_soft(self, all_packages):
        """monetary_architecture: S1, S4 are soft but sourced from CORE.md."""
        registry = build_falsifier_registry(
            all_packages["monetary_architecture"].core,
            all_packages["monetary_architecture"].activation,
        )
        s1 = next(e for e in registry if e.falsifier_id == "S1")
        s4 = next(e for e in registry if e.falsifier_id == "S4")
        assert s1.classification == "soft"
        assert s4.classification == "soft"
        # These get their condition/logic from CORE.md (non-empty)
        assert s1.condition
        assert s4.condition


class TestBuildFalsifierRegistrySynthetic:
    """Synthetic markdown tests for join logic and orphan validation."""

    CORE_TEMPLATE = (
        "## theory_id\n\n`test_theory`\n\n"
        "## deep_falsifiers\n\n"
        "| # | Condition | Logic |\n"
        "|---|-----------|-------|\n"
        "{rows}\n\n"
        "## stability_class\n"
    )

    SEV_TEMPLATE = (
        "## falsifier_severity_assignments\n\n"
        "### Theory-level falsifiers\n\n"
        "| Falsifier | Severity | Rationale |\n"
        "|-----------|----------|----------|\n"
        "{core_rows}\n\n"
        "### State-level falsifiers\n\n"
        "| # | Condition | Severity | Implication |\n"
        "|---|-----------|----------|-------------|\n"
        "{state_rows}\n"
    )

    def _make_core(self, *rows):
        return self.CORE_TEMPLATE.format(rows="\n".join(rows))

    def _make_activation(self, core_rows=(), state_rows=()):
        return self.SEV_TEMPLATE.format(
            core_rows="\n".join(core_rows),
            state_rows="\n".join(state_rows),
        )

    def test_basic_join(self):
        core = self._make_core(
            "| H1 | Price collapses | Kills mean reversion |",
            "| H2 | Valuation resets | Regime change |",
        )
        activation = self._make_activation(
            core_rows=[
                "| H1 — Price collapses | **Hard** | Kills theory |",
                "| H2 — Valuation resets | **Hard** | Also kills |",
            ],
            state_rows=[
                "| S1 | Dollar drops | **medium** (0.25) | Changes path |",
            ],
        )
        registry = build_falsifier_registry(core, activation)
        assert len(registry) == 3

        h1 = next(e for e in registry if e.falsifier_id == "H1")
        assert h1.condition == "Price collapses"  # from CORE
        assert h1.logic == "Kills mean reversion"  # from CORE
        assert h1.classification == "hard"
        assert h1.severity is None
        assert h1.discount is None

        s1 = next(e for e in registry if e.falsifier_id == "S1")
        assert s1.condition == "Dollar drops"  # from ACTIVATION (state)
        assert s1.classification == "soft"
        assert s1.severity.value == "medium"
        assert s1.discount == 0.25

    def test_discount_minor(self):
        core = self._make_core("| H1 | Cond | Logic |")
        activation = self._make_activation(
            core_rows=["| H1 — Cond | **Hard** | Kills |"],
            state_rows=["| S1 | Minor thing | **minor** (0.10) | Small |"],
        )
        s1 = next(
            e for e in build_falsifier_registry(core, activation)
            if e.falsifier_id == "S1"
        )
        assert s1.discount == 0.10

    def test_discount_major(self):
        core = self._make_core("| H1 | Cond | Logic |")
        activation = self._make_activation(
            core_rows=["| H1 — Cond | **Hard** | Kills |"],
            state_rows=["| S1 | Big thing | **major** (0.45) | Severe |"],
        )
        s1 = next(
            e for e in build_falsifier_registry(core, activation)
            if e.falsifier_id == "S1"
        )
        assert s1.discount == 0.45

    def test_orphan_in_core_raises(self):
        """CORE.md has H2 but ACTIVATION.md only references H1."""
        core = self._make_core(
            "| H1 | Cond one | Logic one |",
            "| H2 | Cond two | Logic two |",
        )
        activation = self._make_activation(
            core_rows=["| H1 — Cond one | **Hard** | Kills |"],
            state_rows=["| S1 | State cond | **minor** (0.10) | Note |"],
        )
        with pytest.raises(ValueError, match="CORE.md falsifiers missing.*H2"):
            build_falsifier_registry(core, activation)

    def test_orphan_in_activation_raises(self):
        """ACTIVATION.md references H2 as core-sourced but CORE.md has no H2."""
        core = self._make_core("| H1 | Cond one | Logic one |")
        activation = self._make_activation(
            core_rows=[
                "| H1 — Cond one | **Hard** | Kills |",
                "| H2 — Ghost entry | **Hard** | Not in CORE |",
            ],
            state_rows=["| S1 | State cond | **minor** (0.10) | Note |"],
        )
        with pytest.raises(ValueError, match="do not exist.*H2"):
            build_falsifier_registry(core, activation)

    def test_state_entries_not_orphan_checked(self):
        """State-level entries have no CORE.md counterpart — this is normal, not an orphan."""
        core = self._make_core("| H1 | Cond | Logic |")
        activation = self._make_activation(
            core_rows=["| H1 — Cond | **Hard** | Kills |"],
            state_rows=[
                "| S1 | State one | **minor** (0.10) | Note |",
                "| S2 | State two | **medium** (0.25) | Note |",
                "| S3 | State three | **major** (0.45) | Note |",
            ],
        )
        registry = build_falsifier_registry(core, activation)
        assert len(registry) == 4  # H1 + S1 + S2 + S3

    def test_soft_core_sourced(self):
        """Soft falsifiers can be core-sourced (monetary_architecture pattern)."""
        core = self._make_core(
            "| H1 | Hard cond | Hard logic |",
            "| S1 | Soft cond from core | Soft logic from core |",
        )
        activation = self._make_activation(
            core_rows=[
                "| H1 — Hard cond | **Hard** | Kills |",
                "| S1 — Soft cond | **soft** minor (0.10) | Modifies |",
            ],
        )
        registry = build_falsifier_registry(core, activation)
        s1 = next(e for e in registry if e.falsifier_id == "S1")
        assert s1.classification == "soft"
        assert s1.severity.value == "minor"
        assert s1.discount == 0.10
        assert s1.condition == "Soft cond from core"  # from CORE, not ACTIVATION
        assert s1.logic == "Soft logic from core"

    def test_empty_core_falsifiers_raises(self):
        """CORE.md with no deep_falsifiers section is an error upstream."""
        core = "## core_claim\n\nText.\n\n## stability_class\n"
        activation = self._make_activation(
            state_rows=["| S1 | Cond | **minor** (0.10) | Note |"],
        )
        with pytest.raises(ValueError, match="no ## deep_falsifiers"):
            build_falsifier_registry(core, activation)


# ---------------------------------------------------------------------------
# parse_activation_table — Unit 6
# ---------------------------------------------------------------------------

_VALID_OWNERSHIPS = {"mechanical", "computed-mechanical", "web-search"}
_TWO_PHASE_THEORIES = {"structural_fragility", "debt_cycle_short", "capital_flows"}
_SINGLE_PHASE_THEORIES = EXPECTED_THEORY_IDS - _TWO_PHASE_THEORIES


class TestParseActivationTableLive:
    """Tests against the real ACTIVATION.md files in the repo."""

    @pytest.fixture()
    def all_activation_texts(self):
        dirs = discover_theory_dirs()
        return {
            load_theory_package(d).theory_id: load_theory_package(d).activation
            for d in dirs
        }

    def test_all_eight_parse_successfully(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            entries = parse_activation_table(text)
            assert len(entries) >= 3, f"{theory_id}: expected at least 3 indicators"

    def test_each_entry_has_nonempty_fields(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            for entry in parse_activation_table(text):
                assert entry["indicator_name"], (
                    f"{theory_id}: empty indicator_name"
                )
                assert entry["metric_source"], (
                    f"{theory_id}: empty metric_source"
                )
                assert entry["threshold"], (
                    f"{theory_id}: empty threshold"
                )
                assert entry["direction"], (
                    f"{theory_id}: empty direction"
                )

    def test_data_ownership_values_valid(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            for entry in parse_activation_table(text):
                assert entry["data_ownership"] in _VALID_OWNERSHIPS, (
                    f"{theory_id} indicator {entry['indicator_name']!r}: "
                    f"bad data_ownership {entry['data_ownership']!r}"
                )

    def test_no_qualitative_in_activation_table(self, all_activation_texts):
        """All 8 files should parse without qualitative error."""
        for theory_id, text in all_activation_texts.items():
            entries = parse_activation_table(text)
            for entry in entries:
                assert entry["data_ownership"] != "qualitative", (
                    f"{theory_id}: qualitative indicator in activation_table"
                )

    def test_weights_are_positive_floats(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            for entry in parse_activation_table(text):
                w = entry["weight"]
                assert isinstance(w, float), (
                    f"{theory_id}: weight is {type(w)}, not float"
                )
                assert 0 < w <= 1.0, (
                    f"{theory_id}: weight {w} out of (0, 1.0] range"
                )

    def test_two_phase_theories_have_phases(self, all_activation_texts):
        for theory_id in _TWO_PHASE_THEORIES:
            entries = parse_activation_table(all_activation_texts[theory_id])
            phases = {e["phase"] for e in entries}
            assert all(p is not None for p in phases), (
                f"{theory_id}: two-phase theory has None phase"
            )
            assert len(phases) == 2, (
                f"{theory_id}: expected 2 phases, got {phases}"
            )

    def test_single_phase_theories_have_no_phase(self, all_activation_texts):
        for theory_id in _SINGLE_PHASE_THEORIES:
            entries = parse_activation_table(all_activation_texts[theory_id])
            for entry in entries:
                assert entry["phase"] is None, (
                    f"{theory_id}: single-phase theory has phase={entry['phase']!r}"
                )

    # --- Theory-specific structural assertions ---

    def test_structural_fragility_phases(self, all_activation_texts):
        """structural_fragility: ### Phase A/B subsection pattern."""
        entries = parse_activation_table(all_activation_texts["structural_fragility"])
        phases = {e["phase"] for e in entries}
        assert any("Building" in p for p in phases), "Expected 'Building' in phase name"
        assert any("Resolving" in p for p in phases), "Expected 'Resolving' in phase name"
        phase_a = [e for e in entries if "Building" in (e["phase"] or "")]
        phase_b = [e for e in entries if "Resolving" in (e["phase"] or "")]
        assert len(phase_a) == 8, f"Expected 8 Phase A indicators, got {len(phase_a)}"
        assert len(phase_b) == 4, f"Expected 4 Phase B indicators, got {len(phase_b)}"

    def test_debt_cycle_short_phases(self, all_activation_texts):
        """debt_cycle_short: separate ## activation_table — Phase A/B headings."""
        entries = parse_activation_table(all_activation_texts["debt_cycle_short"])
        phases = {e["phase"] for e in entries}
        assert any("Expansion" in p for p in phases), "Expected 'Expansion' in phase name"
        assert any("Contraction" in p for p in phases), "Expected 'Contraction' in phase name"
        phase_a = [e for e in entries if "Expansion" in (e["phase"] or "")]
        phase_b = [e for e in entries if "Contraction" in (e["phase"] or "")]
        assert len(phase_a) == 8, f"Expected 8 Expansion indicators, got {len(phase_a)}"
        assert len(phase_b) == 7, f"Expected 7 Contraction indicators, got {len(phase_b)}"

    def test_capital_flows_weight_with_calibration(self, all_activation_texts):
        """capital_flows: weight cells have `[CALIBRATION]` annotations."""
        entries = parse_activation_table(all_activation_texts["capital_flows"])
        weights = [e["weight"] for e in entries]
        assert all(isinstance(w, float) for w in weights)
        # Phase A weights include 0.33, 0.27 etc. — non-standard values
        assert any(w > 0.25 for w in weights), "Expected weights > 0.25 (capital_flows)"

    def test_fiscal_dominance_liquidity_single_phase(self, all_activation_texts):
        entries = parse_activation_table(
            all_activation_texts["fiscal_dominance_liquidity"],
        )
        assert len(entries) == 7
        assert all(e["phase"] is None for e in entries)


class TestParseActivationTableSynthetic:
    """Synthetic markdown tests for parser edge cases."""

    def test_basic_single_phase(self):
        text = (
            "## activation_table\n\n"
            "| Indicator | Metric Source | Data Ownership | Threshold "
            "| Direction | Weight | Rationale |\n"
            "|-----------|--------------|----------------|-----------|"
            "-----------|--------|-----------|\n"
            "| Spread level | credit.hy_spread | mechanical "
            "| Below 300bp | below | 0.30 | Tight spreads |\n"
            "| Vol level | ^VIX | mechanical "
            "| Below 14 | below | 0.20 | Complacency |\n\n"
            "## activation_thresholds\n"
        )
        entries = parse_activation_table(text)
        assert len(entries) == 2
        assert entries[0]["indicator_name"] == "Spread level"
        assert entries[0]["metric_source"] == "credit.hy_spread"
        assert entries[0]["data_ownership"] == "mechanical"
        assert entries[0]["threshold"] == "Below 300bp"
        assert entries[0]["direction"] == "below"
        assert entries[0]["weight"] == 0.30
        assert entries[0]["phase"] is None
        assert entries[1]["indicator_name"] == "Vol level"

    def test_two_phase_subsections(self):
        """### Phase A/B subsection pattern (structural_fragility style)."""
        text = (
            "## activation_table\n\n"
            "### Phase A: Building\n\n"
            "| Indicator | Metric Source | Data Ownership | Threshold "
            "| Direction | Weight | Rationale |\n"
            "|-----------|--------------|----------------|-----------|"
            "-----------|--------|-----------|\n"
            "| Spread A | source_a | mechanical | Below 300 "
            "| below | 0.50 | Note |\n\n"
            "### Phase B: Resolving\n\n"
            "| Indicator | Metric Source | Data Ownership | Threshold "
            "| Direction | Weight | Rationale |\n"
            "|-----------|--------------|----------------|-----------|"
            "-----------|--------|-----------|\n"
            "| Spread B | source_b | mechanical | Above 600 "
            "| above | 0.40 | Note |\n\n"
            "## activation_thresholds\n"
        )
        entries = parse_activation_table(text)
        assert len(entries) == 2
        assert entries[0]["phase"] == "Phase A: Building"
        assert entries[1]["phase"] == "Phase B: Resolving"
        assert entries[0]["indicator_name"] == "Spread A"
        assert entries[1]["indicator_name"] == "Spread B"

    def test_two_phase_separate_headings(self):
        """Separate ## activation_table — Phase A/B headings (debt_cycle_short style)."""
        text = (
            "## activation_table — Phase A: Expansion\n\n"
            "| Indicator | Metric Source | Data Ownership | Threshold "
            "| Direction | Weight | Rationale |\n"
            "|-----------|--------------|----------------|-----------|"
            "-----------|--------|-----------|\n"
            "| ISM proxy | growth.ism_proxy | mechanical | Above 50 "
            "| above | 0.15 | Expansion |\n\n"
            "## activation_table — Phase B: Contraction\n\n"
            "| Indicator | Metric Source | Data Ownership | Threshold "
            "| Direction | Weight | Rationale |\n"
            "|-----------|--------------|----------------|-----------|"
            "-----------|--------|-----------|\n"
            "| ISM proxy below | growth.ism_proxy | mechanical | Below 48 "
            "| below | 0.20 | Contraction |\n\n"
            "## quadrant_classification\n"
        )
        entries = parse_activation_table(text)
        assert len(entries) == 2
        assert entries[0]["phase"] == "Phase A: Expansion"
        assert entries[1]["phase"] == "Phase B: Contraction"

    def test_qualitative_raises_error(self):
        """Qualitative indicator in activation_table is a hard error."""
        text = (
            "## activation_table\n\n"
            "| Indicator | Metric Source | Data Ownership | Threshold "
            "| Direction | Weight | Rationale |\n"
            "|-----------|--------------|----------------|-----------|"
            "-----------|--------|-----------|\n"
            "| Good indicator | api_source | mechanical | Above 50 "
            "| above | 0.30 | Fine |\n"
            "| Bad indicator | expert judgment | qualitative | Subjective "
            "| above | 0.20 | Should fail |\n"
        )
        with pytest.raises(ValueError, match="[Qq]ualitative.*activation_table"):
            parse_activation_table(text)

    def test_no_section_raises(self):
        text = "## phases\n\nSome content.\n\n## context_flags\n"
        with pytest.raises(ValueError, match="no.*activation_table"):
            parse_activation_table(text)

    def test_empty_table_raises(self):
        text = (
            "## activation_table\n\n"
            "No table here, just prose.\n\n"
            "## activation_thresholds\n"
        )
        with pytest.raises(ValueError, match="no parseable indicator rows"):
            parse_activation_table(text)

    def test_data_ownership_backticks_stripped(self):
        """Data ownership values may be wrapped in backticks."""
        text = (
            "## activation_table\n\n"
            "| Indicator | Metric Source | Data Ownership | Threshold "
            "| Direction | Weight | Rationale |\n"
            "|-----------|--------------|----------------|-----------|"
            "-----------|--------|-----------|\n"
            "| Ind A | source | `mechanical` | Above 10 "
            "| above | 0.30 | Note |\n"
            "| Ind B | source | `computed-mechanical` \u00b7 Dependencies: x, y "
            "| Above 20 | above | 0.25 | Note |\n"
            "| Ind C | source | `web-search` \u2014 preferred source: multpl.com "
            "| Above 30 | above | 0.20 | Note |\n"
        )
        entries = parse_activation_table(text)
        assert len(entries) == 3
        assert entries[0]["data_ownership"] == "mechanical"
        assert entries[1]["data_ownership"] == "computed-mechanical"
        assert entries[2]["data_ownership"] == "web-search"

    def test_weight_with_annotation(self):
        """Weight cells may have [CALIBRATION] annotations (capital_flows pattern)."""
        text = (
            "## activation_table\n\n"
            "| Indicator | Metric Source | Data Ownership | Threshold "
            "| Direction | Weight | Rationale |\n"
            "|-----------|--------------|----------------|-----------|"
            "-----------|--------|-----------|\n"
            "| PE gap | MSCI EM PE | web-search | Above 40% "
            "| above | 0.33 `[CALIBRATION]` | Note |\n"
        )
        entries = parse_activation_table(text)
        assert len(entries) == 1
        assert entries[0]["weight"] == 0.33

    def test_subsection_tables_ignored(self):
        """Non-activation sub-tables (e.g., activation_thresholds) are skipped."""
        text = (
            "## activation_table\n\n"
            "| Indicator | Metric Source | Data Ownership | Threshold "
            "| Direction | Weight | Rationale |\n"
            "|-----------|--------------|----------------|-----------|"
            "-----------|--------|-----------|\n"
            "| Vol level | ^VIX | mechanical | Below 14 "
            "| below | 0.20 | Complacency |\n\n"
            "### Activation thresholds\n\n"
            "| Score Range | Status |\n"
            "|-------------|--------|\n"
            "| >= 0.60 | Active |\n\n"
            "## context_flags\n"
        )
        entries = parse_activation_table(text)
        assert len(entries) == 1
        assert entries[0]["indicator_name"] == "Vol level"

    def test_section_stops_at_next_h2(self):
        """Parser does not include rows from the next ## section."""
        text = (
            "## activation_table\n\n"
            "| Indicator | Metric Source | Data Ownership | Threshold "
            "| Direction | Weight | Rationale |\n"
            "|-----------|--------------|----------------|-----------|"
            "-----------|--------|-----------|\n"
            "| Vol level | ^VIX | mechanical | Below 14 "
            "| below | 0.20 | Note |\n\n"
            "## context_flags\n\n"
            "| Flag | Source | Data Ownership | What to Look For "
            "| Extra | Extra2 | Extra3 |\n"
            "|------|--------|----------------|-------------------|"
            "-------|--------|--------|\n"
            "| Narrative shift | media | qualitative | Sentiment change "
            "| x | 0.10 | y |\n"
        )
        entries = parse_activation_table(text)
        assert len(entries) == 1
        assert entries[0]["indicator_name"] == "Vol level"


# ---------------------------------------------------------------------------
# parse_context_flags — Unit 7
# ---------------------------------------------------------------------------

_VALID_CTX_OWNERSHIPS = {"qualitative", "web-search"}


class TestParseContextFlagsLive:
    """Tests against the real ACTIVATION.md files in the repo."""

    @pytest.fixture()
    def all_activation_texts(self):
        dirs = discover_theory_dirs()
        return {
            load_theory_package(d).theory_id: load_theory_package(d).activation
            for d in dirs
        }

    def test_all_eight_parse_successfully(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            entries = parse_context_flags(text)
            assert len(entries) >= 2, f"{theory_id}: expected at least 2 context flags"

    def test_each_entry_has_nonempty_flag_name(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            for entry in parse_context_flags(text):
                assert entry["flag_name"], (
                    f"{theory_id}: empty flag_name"
                )

    def test_each_entry_has_nonempty_description(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            for entry in parse_context_flags(text):
                assert entry["description"] or entry["usage"], (
                    f"{theory_id} flag {entry['flag_name']!r}: "
                    f"both description and usage empty"
                )

    def test_data_ownership_values_valid(self, all_activation_texts):
        for theory_id, text in all_activation_texts.items():
            for entry in parse_context_flags(text):
                assert entry["data_ownership"] in _VALID_CTX_OWNERSHIPS, (
                    f"{theory_id} flag {entry['flag_name']!r}: "
                    f"bad data_ownership {entry['data_ownership']!r}"
                )

    def test_all_entries_have_required_keys(self, all_activation_texts):
        required = {"flag_name", "source", "data_ownership", "description", "usage"}
        for theory_id, text in all_activation_texts.items():
            for entry in parse_context_flags(text):
                assert set(entry.keys()) == required, (
                    f"{theory_id}: unexpected keys {set(entry.keys())}"
                )

    # --- Theory-specific structural assertions ---

    def test_structural_fragility_has_usage(self, all_activation_texts):
        """structural_fragility: has Usage column populated."""
        entries = parse_context_flags(all_activation_texts["structural_fragility"])
        for entry in entries:
            assert entry["usage"], (
                f"structural_fragility flag {entry['flag_name']!r}: expected non-empty usage"
            )

    def test_capital_flows_no_source_column(self, all_activation_texts):
        """capital_flows: different schema — source empty, description from Description col."""
        entries = parse_context_flags(all_activation_texts["capital_flows"])
        assert len(entries) == 4, f"Expected 4 capital_flows flags, got {len(entries)}"
        for entry in entries:
            assert entry["description"], (
                f"capital_flows flag {entry['flag_name']!r}: expected description"
            )

    def test_monetary_architecture_hybrid_ownership(self, all_activation_texts):
        """monetary_architecture: 'web-search / computed-mechanical' → 'web-search'."""
        entries = parse_context_flags(all_activation_texts["monetary_architecture"])
        plumbing = [e for e in entries if "plumbing" in e["flag_name"].lower()]
        assert len(plumbing) == 1, "Expected 'Plumbing state' flag"
        assert plumbing[0]["data_ownership"] == "web-search"

    def test_fiscal_dominance_liquidity_three_flags(self, all_activation_texts):
        """fiscal_dominance_liquidity: exactly 3 context flags."""
        entries = parse_context_flags(all_activation_texts["fiscal_dominance_liquidity"])
        assert len(entries) == 3

    def test_debt_cycle_short_defaults_qualitative(self, all_activation_texts):
        """debt_cycle_short: no Data Ownership column → all default to qualitative."""
        entries = parse_context_flags(all_activation_texts["debt_cycle_short"])
        for entry in entries:
            assert entry["data_ownership"] == "qualitative", (
                f"debt_cycle_short {entry['flag_name']!r}: expected qualitative default"
            )


class TestParseContextFlagsSynthetic:
    """Tests against synthetic ACTIVATION.md content for edge cases."""

    def test_standard_four_column_table(self):
        text = (
            "## context_flags\n\n"
            "| Flag | Source | Data Ownership | What to Look For |\n"
            "|------|--------|----------------|------------------|\n"
            "| Narrative shift | Financial media | `qualitative` | Sentiment change |\n"
            "| Auction stress | Treasury data | `web-search` | Declining bid-to-cover |\n"
        )
        entries = parse_context_flags(text)
        assert len(entries) == 2
        assert entries[0]["flag_name"] == "Narrative shift"
        assert entries[0]["source"] == "Financial media"
        assert entries[0]["data_ownership"] == "qualitative"
        assert entries[0]["description"] == "Sentiment change"
        assert entries[0]["usage"] == ""
        assert entries[1]["data_ownership"] == "web-search"

    def test_five_column_with_usage(self):
        text = (
            "## context_flags\n\n"
            "Preamble text.\n\n"
            "| Flag | Source | Data Ownership | What to Look For | Usage |\n"
            "|------|--------|----------------|-------------------|-------|\n"
            "| Flag A | Source A | `qualitative` | Description A | Usage A |\n"
        )
        entries = parse_context_flags(text)
        assert len(entries) == 1
        assert entries[0]["usage"] == "Usage A"

    def test_capital_flows_schema(self):
        """capital_flows pattern: Flag | Description | Why Context, Not Scored."""
        text = (
            "## context_flags\n\n"
            "| Flag | Description | Why Context, Not Scored |\n"
            "|------|-------------|-------------------------|\n"
            "| EM catalyst | Composite check | Overlaps with scored |\n"
            "| Geopolitical risk | US-China relations | Inherently qualitative |\n"
        )
        entries = parse_context_flags(text)
        assert len(entries) == 2
        assert entries[0]["flag_name"] == "EM catalyst"
        assert entries[0]["description"] == "Composite check"
        assert entries[0]["usage"] == "Overlaps with scored"
        assert entries[0]["source"] == ""
        assert entries[0]["data_ownership"] == "qualitative"

    def test_swapped_columns(self):
        """fiscal_dominance_liquidity pattern: Data Ownership before Source."""
        text = (
            "## context_flags\n\n"
            "| Flag | Data Ownership | Source | What to Look For |\n"
            "|------|----------------|--------|------------------|\n"
            "| Bipartisan expansion | `web-search` | CBO reports | Neither party reducing deficit |\n"
        )
        entries = parse_context_flags(text)
        assert len(entries) == 1
        assert entries[0]["data_ownership"] == "web-search"
        assert entries[0]["source"] == "CBO reports"

    def test_no_data_ownership_column_defaults_qualitative(self):
        """debt_cycle_short pattern: no Data Ownership column."""
        text = (
            "## context_flags\n\n"
            "| Flag | Source | What to Look For | Usage |\n"
            "|------|--------|-------------------|-------|\n"
            "| Cycle maturity | ISM trajectory | Late cycle signals | Generator context |\n"
        )
        entries = parse_context_flags(text)
        assert len(entries) == 1
        assert entries[0]["data_ownership"] == "qualitative"
        assert entries[0]["source"] == "ISM trajectory"

    def test_hybrid_ownership_extracts_web_search(self):
        """monetary_architecture pattern: 'web-search / computed-mechanical'."""
        text = (
            "## context_flags\n\n"
            "| Flag | Source | Data Ownership | What to Look For |\n"
            "|------|--------|----------------|------------------|\n"
            "| Plumbing state | Basis levels | `web-search / computed-mechanical` | Binary calm/stressed |\n"
        )
        entries = parse_context_flags(text)
        assert len(entries) == 1
        assert entries[0]["data_ownership"] == "web-search"

    def test_missing_section_raises(self):
        with pytest.raises(ValueError, match="no ## context_flags"):
            parse_context_flags("## activation_table\n| a | b |\n")

    def test_empty_table_raises(self):
        text = (
            "## context_flags\n\n"
            "No table here, just prose.\n\n"
            "## next_section\n"
        )
        with pytest.raises(ValueError, match="no parseable table rows"):
            parse_context_flags(text)

    def test_invalid_data_ownership_raises(self):
        text = (
            "## context_flags\n\n"
            "| Flag | Source | Data Ownership | What to Look For |\n"
            "|------|--------|----------------|------------------|\n"
            "| Bad flag | source | `mechanical` | Description |\n"
        )
        with pytest.raises(ValueError, match="invalid data_ownership"):
            parse_context_flags(text)

    def test_section_ends_at_next_h2(self):
        """Parser should stop at the next ## header."""
        text = (
            "## context_flags\n\n"
            "| Flag | Source | Data Ownership | What to Look For |\n"
            "|------|--------|----------------|------------------|\n"
            "| Flag A | source | `qualitative` | Desc A |\n"
            "\n"
            "## falsifier_severity_assignments\n\n"
            "| ID | Classification |\n"
            "|----|---------|\n"
            "| H1 | hard |\n"
        )
        entries = parse_context_flags(text)
        assert len(entries) == 1
        assert entries[0]["flag_name"] == "Flag A"

    def test_weight_column_ignored(self):
        """Extra columns (like weight) should not break parsing."""
        text = (
            "## context_flags\n\n"
            "| Flag | Source | Data Ownership | What to Look For | Weight |\n"
            "|------|--------|----------------|-------------------|--------|\n"
            "| Flag A | source | `qualitative` | Description | 0.15 |\n"
        )
        entries = parse_context_flags(text)
        assert len(entries) == 1
        assert entries[0]["flag_name"] == "Flag A"
        # Weight should not appear in output
        assert "weight" not in entries[0]


# ---------------------------------------------------------------------------
# Unit 8: INTERACTION_MATRIX.md parser
# ---------------------------------------------------------------------------

INTERACTION_MATRIX_PATH = THEORIES_DIR / "INTERACTION_MATRIX.md"


class TestParseInteractionPairwise:

    def test_real_matrix_parses(self):
        """Real INTERACTION_MATRIX.md parses without error."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        entries = parse_interaction_pairwise(text)
        assert len(entries) > 0

    def test_real_matrix_row_count(self):
        """The real matrix has 22 pairwise entries."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        entries = parse_interaction_pairwise(text)
        assert len(entries) == 22

    def test_real_matrix_keys(self):
        """Each entry has all required keys."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        entries = parse_interaction_pairwise(text)
        expected_keys = {
            "theory_a", "theory_a_phase", "theory_b", "theory_b_phase",
            "relationship", "invariant_logic", "expression_detail_location",
        }
        for entry in entries:
            assert set(entry.keys()) == expected_keys

    def test_real_matrix_all_theory_ids_valid(self):
        """Every theory_id in the pairwise table is a known theory."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        entries = parse_interaction_pairwise(text)
        for entry in entries:
            assert entry["theory_a"] in EXPECTED_THEORY_IDS, (
                f"Unknown theory_a: {entry['theory_a']}"
            )
            assert entry["theory_b"] in EXPECTED_THEORY_IDS, (
                f"Unknown theory_b: {entry['theory_b']}"
            )

    def test_phase_annotations_stripped(self):
        """Phase annotations like (Building) are parsed into separate field."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        entries = parse_interaction_pairwise(text)
        # structural_fragility (Building) should appear in the first row
        first = entries[0]
        assert first["theory_a"] == "structural_fragility"
        assert first["theory_a_phase"] == "Building"

    def test_no_bold_markers_in_relationship(self):
        """Bold ** markers should be stripped from relationship text."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        entries = parse_interaction_pairwise(text)
        for entry in entries:
            assert "**" not in entry["relationship"]

    def test_invariant_logic_not_empty(self):
        """Every row has non-empty invariant logic."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        entries = parse_interaction_pairwise(text)
        for entry in entries:
            assert len(entry["invariant_logic"]) > 10

    def test_synthetic_basic(self):
        """Minimal synthetic table parses correctly."""
        text = (
            "## Pairwise Interaction Table\n\n"
            "| Theory A | Theory B | Relationship | Invariant Logic | Expression Detail Location |\n"
            "|----------|----------|-------------|-----------------|---------------------------|\n"
            "| alpha | beta | **A triggers B** | Alpha causes beta | alpha/TACTICAL.md |\n"
        )
        entries = parse_interaction_pairwise(text)
        assert len(entries) == 1
        assert entries[0]["theory_a"] == "alpha"
        assert entries[0]["theory_a_phase"] is None
        assert entries[0]["theory_b"] == "beta"
        assert entries[0]["relationship"] == "A triggers B"

    def test_synthetic_with_phase_annotations(self):
        """Phase annotations in both columns parse correctly."""
        text = (
            "## Pairwise Interaction Table\n\n"
            "| Theory A | Theory B | Relationship | Invariant Logic | Expression Detail Location |\n"
            "|----------|----------|-------------|-----------------|---------------------------|\n"
            "| alpha (Building) | beta (Contraction) | **A modifies B** | Logic here | paths |\n"
        )
        entries = parse_interaction_pairwise(text)
        assert entries[0]["theory_a"] == "alpha"
        assert entries[0]["theory_a_phase"] == "Building"
        assert entries[0]["theory_b"] == "beta"
        assert entries[0]["theory_b_phase"] == "Contraction"

    def test_missing_section_raises(self):
        """Missing section header raises ValueError."""
        with pytest.raises(ValueError, match="Pairwise Interaction Table"):
            parse_interaction_pairwise("## Notes\nSome text\n")

    def test_empty_table_raises(self):
        """Section with no data rows raises ValueError."""
        text = (
            "## Pairwise Interaction Table\n\n"
            "| Theory A | Theory B | Relationship | Invariant Logic | Expression Detail Location |\n"
            "|----------|----------|-------------|-----------------|---------------------------|\n"
        )
        with pytest.raises(ValueError, match="no parseable rows"):
            parse_interaction_pairwise(text)

    def test_section_ends_at_next_h2(self):
        """Parser stops at the next ## header."""
        text = (
            "## Pairwise Interaction Table\n\n"
            "| Theory A | Theory B | Relationship | Invariant Logic | Expression Detail Location |\n"
            "|----------|----------|-------------|-----------------|---------------------------|\n"
            "| alpha | beta | **A triggers B** | Logic | paths |\n"
            "\n"
            "## Shared Upstream Cause Warnings\n\n"
            "| Shared Cause | Theories Affected | Discounting Note |\n"
            "|-------------|-------------------|------------------|\n"
            "| Cause X | alpha, beta | Note |\n"
        )
        entries = parse_interaction_pairwise(text)
        assert len(entries) == 1


class TestParseSharedUpstreamWarnings:

    def test_real_matrix_parses(self):
        """Real shared upstream warnings parse without error."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        entries = parse_shared_upstream_warnings(text)
        assert len(entries) > 0

    def test_real_matrix_warning_count(self):
        """The real matrix has 6 shared upstream warnings."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        entries = parse_shared_upstream_warnings(text)
        assert len(entries) == 6

    def test_real_matrix_keys(self):
        """Each warning has all required keys."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        entries = parse_shared_upstream_warnings(text)
        expected_keys = {"shared_cause", "theories_affected", "discounting_note"}
        for entry in entries:
            assert set(entry.keys()) == expected_keys

    def test_real_matrix_theories_are_lists(self):
        """theories_affected is a list of strings."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        entries = parse_shared_upstream_warnings(text)
        for entry in entries:
            assert isinstance(entry["theories_affected"], list)
            assert all(isinstance(t, str) for t in entry["theories_affected"])
            assert len(entry["theories_affected"]) >= 2

    def test_real_matrix_all_theory_ids_valid(self):
        """Every theory_id in warnings is a known theory."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        entries = parse_shared_upstream_warnings(text)
        for entry in entries:
            for tid in entry["theories_affected"]:
                assert tid in EXPECTED_THEORY_IDS, (
                    f"Unknown theory in warnings: {tid}"
                )

    def test_synthetic_basic(self):
        """Minimal synthetic warnings table parses correctly."""
        text = (
            "## Shared Upstream Cause Warnings\n\n"
            "| Shared Cause | Theories Affected | Discounting Note |\n"
            "|-------------|-------------------|------------------|\n"
            "| Low rates | alpha (indicator), beta (mechanism) | Do not double count |\n"
        )
        entries = parse_shared_upstream_warnings(text)
        assert len(entries) == 1
        assert entries[0]["shared_cause"] == "Low rates"
        assert entries[0]["theories_affected"] == ["alpha", "beta"]
        assert "double count" in entries[0]["discounting_note"]

    def test_missing_section_raises(self):
        """Missing section header raises ValueError."""
        with pytest.raises(ValueError, match="Shared Upstream Cause Warnings"):
            parse_shared_upstream_warnings("## Notes\nSome text\n")

    def test_empty_table_raises(self):
        """Section with no data rows raises ValueError."""
        text = (
            "## Shared Upstream Cause Warnings\n\n"
            "| Shared Cause | Theories Affected | Discounting Note |\n"
            "|-------------|-------------------|------------------|\n"
        )
        with pytest.raises(ValueError, match="no parseable rows"):
            parse_shared_upstream_warnings(text)


class TestParseInteractionMatrix:

    def test_real_matrix_full_parse(self):
        """Full parse of real INTERACTION_MATRIX.md succeeds."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        result = parse_interaction_matrix(text, known_theory_ids=EXPECTED_THEORY_IDS)
        assert len(result["pairwise"]) == 22
        assert len(result["shared_upstream_warnings"]) == 6

    def test_real_matrix_validation_passes(self):
        """All theory_ids in real matrix pass validation against known set."""
        text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        # Should not raise
        parse_interaction_matrix(text, known_theory_ids=EXPECTED_THEORY_IDS)

    def test_unknown_theory_id_raises(self):
        """Unknown theory_id in pairwise table raises ValueError."""
        text = (
            "## Pairwise Interaction Table\n\n"
            "| Theory A | Theory B | Relationship | Invariant Logic | Expression Detail Location |\n"
            "|----------|----------|-------------|-----------------|---------------------------|\n"
            "| alpha | beta | **A triggers B** | Logic | paths |\n"
            "\n"
            "## Shared Upstream Cause Warnings\n\n"
            "| Shared Cause | Theories Affected | Discounting Note |\n"
            "|-------------|-------------------|------------------|\n"
            "| Cause | alpha, beta | Note |\n"
        )
        with pytest.raises(ValueError, match="unknown theory_ids"):
            parse_interaction_matrix(text, known_theory_ids={"alpha"})

    def test_unknown_theory_in_warnings_raises(self):
        """Unknown theory_id in warnings table raises ValueError."""
        text = (
            "## Pairwise Interaction Table\n\n"
            "| Theory A | Theory B | Relationship | Invariant Logic | Expression Detail Location |\n"
            "|----------|----------|-------------|-----------------|---------------------------|\n"
            "| alpha | beta | **A triggers B** | Logic | paths |\n"
            "\n"
            "## Shared Upstream Cause Warnings\n\n"
            "| Shared Cause | Theories Affected | Discounting Note |\n"
            "|-------------|-------------------|------------------|\n"
            "| Cause | alpha, gamma | Note |\n"
        )
        with pytest.raises(ValueError, match="unknown theory_ids"):
            parse_interaction_matrix(
                text, known_theory_ids={"alpha", "beta"},
            )

    def test_no_validation_when_none(self):
        """When known_theory_ids is None, no validation occurs."""
        text = (
            "## Pairwise Interaction Table\n\n"
            "| Theory A | Theory B | Relationship | Invariant Logic | Expression Detail Location |\n"
            "|----------|----------|-------------|-----------------|---------------------------|\n"
            "| unknown_a | unknown_b | **A triggers B** | Logic | paths |\n"
            "\n"
            "## Shared Upstream Cause Warnings\n\n"
            "| Shared Cause | Theories Affected | Discounting Note |\n"
            "|-------------|-------------------|------------------|\n"
            "| Cause | unknown_x, unknown_y | Note |\n"
        )
        # Should not raise
        result = parse_interaction_matrix(text)
        assert len(result["pairwise"]) == 1
        assert len(result["shared_upstream_warnings"]) == 1
