# v8 Implementation State

## Current Phase: Phase 1 (Loader + Parsers)
## Current Task: Unit 1 complete — data models defined
## Last Completed: Unit 1 (TheoryPackage + FalsifierEntry data models)
## Last Commit: v8 Unit 1

## Phase Status
- [ ] Phase 1: Loader + Parsers (Components 1-5)
  - [x] Unit 1: TheoryPackage + FalsifierEntry data models in backend/schemas/theory.py
  - [ ] Unit 2: Directory discovery + 4-file loading + missing file validation
  - [ ] Unit 3: CORE.md deep_falsifiers parser
  - [ ] Unit 4: ACTIVATION.md falsifier_severity_assignments parser (theory-level + state-level)
  - [ ] Unit 5: Falsifier registry join logic + orphan validation
  - [ ] Unit 6: ACTIVATION.md activation_table parser with data_ownership column
  - [ ] Unit 7: ACTIVATION.md context_flags parser + qualitative exclusion validation
  - [ ] Unit 8: INTERACTION_MATRIX.md parser (pairwise table + shared upstream cause warnings)
  - [ ] Unit 9: INTERACTION_MATRIX filtering by activation status
  - [ ] Unit 10: Adapter layer (TheoryPackage → monolithic format for parallel validation)
- [ ] Phase 2: Prompt wiring (Components 6-9)
- [ ] Phase 3: Validation (Components 10-13)
- [ ] Phase 4: Cleanup (Components 14-16)

## Repo Inspection Findings

### Where theory files are currently loaded
- **File:** `backend/engine/theory_parser.py`
- **Function:** `load_all_theories()` line 31 — globs `THEORIES_DIR` for `THEORY_MODULE_*.md`
- **Function:** `parse_theory_module()` line 42 — parses monolithic markdown → `TheoryModule`
- **Config:** `backend/config.py` line 8 — `THEORIES_DIR = BASE_DIR / "theories"`

### Where prompt assembly happens
- **File:** `backend/engine/prompt_builder.py`
- **Generation (Pass 2):** `build_generation_prompt()` line 29 — uses `t.raw_markdown[:8000]` for Active, `[:4000]` for Adjacent
- **Elimination (Pass 3):** `build_elimination_prompt()` line 185 — uses `_extract_falsifier_section(t)` for structured falsifier info

### Where activation scoring reads theory thresholds
- **File:** `backend/engine/activation.py`
- **Function:** `score_all_theories()` line 90 — takes `list[TheoryModule]` + `BriefingPacket`
- Reads from `TheoryModule.phases[].indicators[]` (already parsed from monolithic)

### Where conviction scoring reads severity
- **File:** `backend/engine/conviction.py`
- `SEVERITY_WEIGHTS` dict line 34 — minor: 0.10, medium: 0.25, major: 0.45
- `_stage2_discounts()` line 279 — reads severity from `inp.triggered_soft_falsifiers` (hypothesis dict, not theory files)
- Conviction does NOT read theory files directly — it reads severity from LLM elimination output

### Key data flow
```
theories/THEORY_MODULE_*.md → theory_parser.load_all_theories() → list[TheoryModule]
  → activation.score_all_theories() → reads phases/indicators
  → prompt_builder.build_generation_prompt() → reads raw_markdown
  → prompt_builder.build_elimination_prompt() → reads hard_falsifiers/soft_falsifiers
  → conviction.py → reads severity from hypothesis dicts (not theory files)
```

### New v2 file format observations
- ACTIVATION.md sections: phases, transition_logic, activation_table (has Data Ownership column), activation_thresholds, context_flags, falsifier_severity_assignments (theory-level + state-level), state_falsifiers
- CORE.md sections: theory_id, core_claim, causal_mechanism, scope_limits, key_assumptions, deep_falsifiers (# | Condition | Logic), stability_class, revision_triggers, historical_episodes
- INTERACTION_MATRIX.md: Pairwise Interaction Table + Shared Upstream Cause Warnings
- Note: state_falsifiers in ACTIVATION.md are self-contained (condition + severity both in ACTIVATION.md)
- Note: structural_fragility uses different section name "falsifier_severity_assignments → Theory-level falsifiers" and places state-level falsifiers inline; valuation_mean_reversion uses "state_falsifiers" as separate section

### Directory naming
- Pattern: `theories/THEORY_MODULE_{theory_id}_v2/` (8 dirs)
- Typo: `fiscal_dominance_arithmatic_v2` (arithmatic → arithmetic). theory_id inside CORE.md says `fiscal_dominance_arithmetic`. Loader must use theory_id from file content, not directory name.

## Decisions & Notes
- The new file `backend/theory_loader.py` (or `backend/engine/theory_loader.py`) is the new module per plan
- Existing `theory_parser.py` stays untouched until Phase 2 wiring
- Need to verify all 8 ACTIVATION.md formats for section naming consistency before building parser

## Ambiguities to Flag
1. ACTIVATION.md format varies between theories: structural_fragility has falsifier_severity_assignments with inline state-level falsifiers; valuation_mean_reversion has separate state_falsifiers section. Parser must handle both.
2. Directory naming typo (arithmatic). The loader should discover by directory pattern but extract theory_id from CORE.md content.
