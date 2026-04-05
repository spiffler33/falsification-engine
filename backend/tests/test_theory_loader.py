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
    parse_falsifier_severity,
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
