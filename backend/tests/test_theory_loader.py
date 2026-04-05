# test_theory_loader.py — Tests for v8 theory package loader (Units 2-3).
import re
from pathlib import Path

import pytest

from backend.config import THEORIES_DIR
from backend.engine.theory_loader import (
    discover_theory_dirs,
    load_all_theory_packages,
    load_theory_package,
    parse_deep_falsifiers,
)

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
