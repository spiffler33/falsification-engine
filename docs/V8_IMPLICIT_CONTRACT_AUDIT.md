# V8 Implicit Contract Audit

**Date:** 2026-04-06
**Scope:** All code that parses, transforms, or depends on v2 theory package markdown content
**Method:** Adversarial code inspection + data flow tracing across all 8 theory packages

---

## Executive Summary

- **Confirmed bugs:** 6 (3 migration-specific, 3 pre-existing exposed by migration)
- **High-risk fragilities:** 11
- **Safe areas reviewed:** 6

The three migration-specific bugs from the docket (`V8_DIVERGENCE_DOCKET.md`) are not isolated incidents. They are symptoms of a systemic architectural problem: **the activation scoring engine treats human-readable markdown prose as machine-readable identifiers, with no schema enforcement and no loud failures when parsing falls through to silent defaults.**

The audit found 10 additional indicators across 5 theories with non-standard direction strings that silently default to "above", a generic computed-field normalizer that produces garbage field names, threshold extraction that mishandles unit suffixes, and multiple parser paths where malformed input is silently dropped rather than rejected.

---

## Findings

### CONFIRMED BUGS

---

### [BUG-01] metric_source field resolution broken for 3 theories (13 indicators)

- **Severity:** Critical — produces wrong activation scores
- **Area:** Activation scoring, field resolution
- **File / function:** `backend/engine/activation.py` :: `_extract_metric_field()` (lines 257-291), `_entry_to_indicator()` (lines 410-433)
- **Implicit contract:** `computed-mechanical` indicators must have backtick-wrapped field names (e.g., `` `equity_risk_premium` ``). `web-search` indicators must either contain "web search" in the metric_source or have `data_ownership == "web-search"` so the prefix gets re-injected.
- **Failure mode:** When v2 ACTIVATION.md rewrote metric_source strings to human-readable prose, the backticks and "Web search:" prefixes were removed. `_extract_metric_field()` falls through to Strategy 3 (passthrough), returning the entire prose string as a field name. `BriefingPacket.get_field()` returns `None`. The indicator is counted in the scoring denominator but can never trigger.
- **Trigger example:** `"Computed: SPY earnings yield (1/PE) minus 10Y Treasury yield"` resolves to itself instead of `equity_risk_premium`.
- **Current impact:** 13 indicators across `valuation_mean_reversion` (3), `fiscal_dominance_arithmetic` (3), `capital_flows` (7) are permanently untriggered. Scores are 0.294, 0.056, and Inactive respectively instead of 0.882, 0.556, and 0.450.
- **Migration-specific or legacy:** Migration-specific. The v1 monolithic files had backtick field names; the v2 rewrite removed them.
- **Recommended immediate patch:** Restore backtick-wrapped field names in the 3 affected ACTIVATION.md files. Old format in `theories/old_format/` has the correct strings.
- **Recommended architectural fix:** Add a `COMPUTED_FIELD_MAP` (analogous to `WEB_FIELD_MAP`) that maps descriptive metric_source substrings to briefing field names, so resolution doesn't depend on formatting conventions. Add a validation step that checks every indicator resolves to a non-None field or raises loudly.

**Full details:** See `docs/V8_DIVERGENCE_DOCKET.md`

---

### [BUG-02] Non-standard direction strings silently default to "above" (10 indicators, 5 theories)

- **Severity:** Medium — produces incorrect threshold comparisons for some indicators
- **Area:** Activation scoring, direction parsing
- **File / function:** `backend/engine/activation.py` :: `_parse_direction()` (lines 397-407)
- **Implicit contract:** Direction strings must contain one of: "above", "below", "rising", "falling", "between". If none match, defaults to `"above"` without warning.
- **Failure mode:** v2 ACTIVATION.md files use prose directions like "diverging", "positive", "negative", "declining share", "Flat or negative", "Gap widening or at extreme". These either (a) accidentally match a keyword embedded in the string (e.g., "Below and falling" matches "below" — correct by luck), or (b) match nothing and default to "above" (potentially wrong).
- **Trigger examples:**

| Theory | Indicator | Direction String | Parsed As | Correct? |
|--------|-----------|-----------------|-----------|----------|
| `debt_cycle_long` | Negative real rates | "negative" | **"above"** (no keyword match) | Wrong — should be "below" zero |
| `debt_cycle_long` | Rates at ELB | "at or near floor recently" | **"above"** (no keyword match) | Wrong — not a directional check |
| `debt_cycle_long` | Fiscal deficit driver | "above / below respectively" | **"above"** (first keyword match) | Partial — ignores "below" half |
| `capital_flows` (A) | EM PE gap | "Gap widening or at extreme" | **"above"** (no keyword match) | Accidental — "above threshold" happens to work |
| `capital_flows` (A) | Dollar strong | "Above or flat" | "above" | Correct by luck |
| `capital_flows` (A) | China credit impulse | "Flat or negative" | **"above"** (no keyword match) | Wrong — should be "below" zero |
| `monetary_architecture` | Foreign Treasury holdings | "declining share" | **"above"** (no keyword match) | Wrong — should be "falling" |
| `valuation_mean_reversion` | Market breadth | "diverging" | **"above"** (no keyword match) | Accidental — works for ratio check |
| `debt_cycle_short` (A) | Net credit growth | "positive" | **"above"** (no keyword match) | Accidental — "above zero" is same as positive |

- **Current impact:** At least 3 indicators (`debt_cycle_long` indicators 3 and 6, `capital_flows` Phase A indicator 4) have direction checks that are semantically wrong. However, the same parsing existed in v1, so scores match between old and new loaders — this is a pre-existing bug that affects absolute correctness, not migration equivalence.
- **Migration-specific or legacy:** Pre-existing. The old parser used the same keyword-first-match logic. The v2 direction strings are similar to v1.
- **Recommended immediate patch:** Map the 10 non-standard direction strings explicitly in `_DIRECTION_KEYWORDS` or in the ACTIVATION.md files themselves (change "negative" to "below", "declining share" to "falling", etc.).
- **Recommended architectural fix:** Make `_parse_direction()` raise on unrecognized input instead of defaulting to "above". Add a validation pass after loading that rejects theories with unparseable directions.

---

### [BUG-03] RISING/FALLING directions treated as simple threshold comparison

- **Severity:** Medium — semantically incorrect but consistently applied
- **Area:** Activation scoring, threshold checking
- **File / function:** `backend/engine/activation.py` :: `_check_threshold()` (lines 340-344)
- **Implicit contract:** RISING and FALLING should check temporal direction (is the value increasing/decreasing over time). Instead, they are implemented as `value > threshold` (RISING) and `value < threshold` (FALLING) — identical to ABOVE/BELOW.
- **Failure mode:** An indicator like "Weighted average rate rising AND below current market rates" with direction RISING checks if `3.355 > threshold` rather than checking if the rate has been increasing over time.
- **Trigger example:** `fiscal_dominance_arithmetic` indicator "Debt rollover at higher rates" (direction: rising, weight: 0.15). The engine checks `3.355 > extracted_threshold` rather than checking temporal trend.
- **Current impact:** All RISING/FALLING indicators use threshold comparison instead of trend detection. The comment in code (line 341) acknowledges this: "For rising/falling, we'd need historical data. For v1, check against threshold."
- **Migration-specific or legacy:** Pre-existing (v1 design limitation).
- **Recommended immediate patch:** None needed for migration equivalence. Document as known limitation.
- **Recommended architectural fix:** Add temporal data (prior period values) to the briefing packet and implement actual trend checking for RISING/FALLING directions.

---

### [BUG-04] `_normalize_computed_field()` generic fallback produces invalid field names

- **Severity:** Medium — any computed expression not in the hardcoded list produces garbage
- **Area:** Activation scoring, field resolution
- **File / function:** `backend/engine/activation.py` :: `_normalize_computed_field()` (lines 307-322)
- **Implicit contract:** Computed expressions like `"VIX - 20d_realized_vol"` must match one of three hardcoded patterns. Anything else gets a generic normalization (lowercase, strip non-alphanumeric, collapse underscores) that almost never produces a valid briefing field name.
- **Failure mode:** Expression `"gold price / oil price"` normalizes to `"gold_price_oil_price"`, which doesn't exist in the briefing. The indicator is counted in the denominator but can never trigger.
- **Trigger example:** `fiscal_dominance_arithmetic` v2 indicator "Gold/oil ratio elevated" has metric_source `"Computed: gold price / oil price (Yahoo Finance)"`. If this reached `_normalize_computed_field()`, it would produce `"gold_price_oil_price"` (invalid). In practice, this indicator's bug is caught upstream by BUG-01 (no backticks → passthrough → None), so the generic fallback is not reached. But the fallback is architecturally dangerous.
- **Current impact:** Low (masked by BUG-01 catching failures upstream). Would become a live bug if BUG-01 is partially fixed.
- **Migration-specific or legacy:** Pre-existing code, but migration-relevant because v2 expressions are more likely to be written as prose.
- **Recommended immediate patch:** Add explicit mappings for `gold_oil_ratio` and any other known computed fields.
- **Recommended architectural fix:** Replace the generic normalizer with a strict lookup table. Raise on unrecognized expressions.

---

### [BUG-05] `_extract_number()` strips unit suffixes without scaling

- **Severity:** Low-Medium — produces threshold values in wrong units for some indicators
- **Area:** Activation scoring, threshold checking
- **File / function:** `backend/engine/activation.py` :: `_extract_number()` (lines 356-371)
- **Implicit contract:** Threshold strings like `"Above $1.5T"` are parsed by removing `$`, `T`, `B`, `M`, `x`, `bp`, `%` characters, then extracting the first number. The suffix removal does not scale the number: `$1.5T` becomes `1.5`, not `1,500,000,000,000`.
- **Failure mode:** Thresholds denominated in trillions, billions, or basis points are compared against briefing values without unit conversion. Whether this produces correct results depends on whether the briefing value is in the same units as the stripped number.
- **Trigger examples:**

| Threshold String | Extracted | Briefing Value | Units Match? | Result |
|-----------------|-----------|---------------|-------------|--------|
| "Above $1.5T annualized" | 1.5 | `deficit_pace_annualized` = 3690.0 (billions) | No — 1.5 vs 3690 | Triggers (3690 > 1.5) — **correct by accident** |
| "Below 300bp" | 300 | `credit.hy_spread` = 316.0 (basis points) | Yes | Correct |
| "Above 1.5x" | 1.5 | `buffett_indicator` (ratio) | Yes | Correct |
| "Below $250B and declining" | 250 | `liquidity.reverse_repo` = 327.0 (billions) | Yes | Correct |
| "Annual interest > defense ($886B)" | 886 | `interest_exceeds_defense` = 287.0 (difference in $B) | No — 886 is the defense budget, not the threshold | Wrong — checks 287 > 886 instead of 287 > 0 |

- **Current impact:** Most thresholds work by coincidence because the briefing values and threshold numbers happen to be in compatible units. The `interest_exceeds_defense` indicator is an exception: it extracts 886 (the defense budget number from the parenthetical) instead of 0 (the actual threshold), producing a false negative.
- **Migration-specific or legacy:** Pre-existing.
- **Recommended immediate patch:** Fix `interest_exceeds_defense` threshold to `"Annual interest expense exceeds defense spending"` (remove the parenthetical dollar amount). Or add a special case for threshold strings that contain `>` or `<` operators.
- **Recommended architectural fix:** Store thresholds as structured data (numeric value + unit + direction) in ACTIVATION.md rather than as prose strings. Parse at load time, not at check time.

---

### [BUG-06] `data_ownership` silent fallback to first token on parse failure

- **Severity:** Low — not currently triggered but dangerous
- **Area:** Theory loader, activation table parsing
- **File / function:** `backend/engine/theory_loader.py` :: `_parse_activation_rows()` (lines 639-645)
- **Implicit contract:** The Data Ownership cell must contain one of: `computed-mechanical`, `web-search`, `mechanical`, `qualitative`. The regex `_OWNERSHIP_KW_RE` extracts the first match. If no match, the fallback takes the first whitespace-delimited token of the cell.
- **Failure mode:** A Data Ownership cell written as `"computed and mechanical"` would have no regex match. The fallback extracts `"computed"` (first token), which is not a valid ownership value. No validation catches this — it propagates silently. The `_entry_to_indicator()` function checks `data_ownership == "web-search"` to decide prefix re-injection; an invalid value like `"computed"` would bypass re-injection for an indicator that needs it.
- **Trigger example:** Not currently triggered (all v2 files use correct format).
- **Current impact:** None. All 8 v2 files use correctly formatted data_ownership values.
- **Migration-specific or legacy:** Pre-existing code path, but migration-relevant because future theory file edits could trigger it.
- **Recommended immediate patch:** Add validation after parsing: reject any entry whose `data_ownership` is not in the canonical set.
- **Recommended architectural fix:** Same as patch — make it loud.

---

### HIGH-RISK FRAGILITIES

---

### [FRAGILITY-01] Section header dependencies use exact underscore format

- **Area:** Theory loader, section finding
- **File / function:** `backend/engine/theory_loader.py` :: multiple section-finding regexes
- **Implicit contract:** Section headers must match exact patterns:
  - `## activation_table` (underscores, case-insensitive)
  - `## falsifier_severity_assignments` (underscores)
  - `## state_falsifiers` (underscores)
  - `## context_flags` (underscores)
  - `## deep_falsifiers` (underscores, trailing `$` anchor)
- **What would break it:** Rewriting `## falsifier_severity_assignments` to `## Falsifier Severity Assignments` (spaces). The regex `re.match(rf"^##\s+{re.escape(section_name)}\s*$"...)` would fail.
- **Current status:** All 8 v2 files use correct underscore format.
- **Why high-risk:** This is exactly the class of change that a human editor would make — replacing underscores with spaces for readability.
- **Recommended fix:** Normalize section headers before matching (strip, lowercase, collapse whitespace/underscores). Or validate at load time that all expected sections are found.

---

### [FRAGILITY-02] Activation table assumes fixed column positions

- **Area:** Theory loader, activation table parsing
- **File / function:** `backend/engine/theory_loader.py` :: `_parse_activation_rows()` (lines 625-636)
- **Implicit contract:** Activation table columns are assumed to be in order: `Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | ...`. The parser uses positional indices (cells[0], cells[1], etc.) rather than header-name mapping.
- **What would break it:** Reordering columns (e.g., putting Weight before Direction).
- **Why high-risk:** The context_flags parser uses header-name mapping (`_map_context_flag_columns`), proving the codebase knows how to do this correctly. The activation table parser does not, creating an inconsistency.
- **Current status:** All 8 files use consistent column order.
- **Recommended fix:** Add column-name mapping to activation table parsing, matching the context_flags pattern.

---

### [FRAGILITY-03] Phase naming regex requires exact "Phase A:" / "Phase B:" format

- **Area:** Theory loader + activation scoring
- **File / function:** `theory_loader.py` :: `_PHASE_SUBSECTION_RE` (line 573), `activation.py` :: `_build_phases_from_package()` (lines 455-463)
- **Implicit contract:** Phase subsection headers must match `### Phase [AB]: ...` (case-sensitive letter, colon required). Phase detection regex requires `Phase\s*A\b` or `Phase\s*B\b`.
- **What would break it:** `### Phase 1: Expansion` or `### phase a: Building` or `### Expansion Phase`.
- **Current status:** All three two-phase theories use correct format.
- **Recommended fix:** Accept numeric phase identifiers and normalize to canonical names. Add validation that two-phase theories have exactly 2 phases with distinct names.

---

### [FRAGILITY-04] Context flags default to "qualitative" when Data Ownership column absent

- **Area:** Theory loader, context flags parsing
- **File / function:** `backend/engine/theory_loader.py` :: `parse_context_flags()` (lines 868-871)
- **Implicit contract:** If the Data Ownership column is missing from the context_flags table, all flags silently default to `"qualitative"`.
- **What would break it:** A theory with `web-search` context flags in a table that lacks the Data Ownership column — the flags would be misclassified.
- **Current status:** `debt_cycle_short_v2` intentionally omits this column (all flags are qualitative). Other theories include it.
- **Recommended fix:** Require the column and raise on absence. Or document the default behavior explicitly.

---

### [FRAGILITY-05] Falsifier severity inferred from free text in any cell

- **Area:** Theory loader, falsifier severity classification
- **File / function:** `backend/engine/theory_loader.py` :: `_classify_severity_text()` (lines 256-272)
- **Implicit contract:** Severity keywords (`minor`, `medium`, `major`, `hard`, `theory-kill`) are searched for in ANY cell of a falsifier table row. If the keyword appears in narrative text (e.g., "This is a major economic event"), it is treated as the severity classification.
- **What would break it:** A falsifier condition containing the word "minor" in its description being classified as `severity=minor` when it should be `major`.
- **Current status:** No false positives in current data (severity keywords appear only in the Severity column).
- **Recommended fix:** Restrict keyword search to the Severity column only. Require column-name mapping.

---

### [FRAGILITY-06] Falsifier ID extraction searches all cells as fallback

- **Area:** Theory loader, falsifier parsing
- **File / function:** `backend/engine/theory_loader.py` :: falsifier table parsing (lines 344-354)
- **Implicit contract:** If the ID column cell is empty or unparseable, the parser searches ALL cells for a pattern matching `(H|S|DF|SF)\d+`. This could match an ID mentioned in narrative text of a different column.
- **What would break it:** A falsifier condition saying "Consider H2 conditions if..." in a row where the ID column is malformed — the parser would extract `H2` from the condition text.
- **Current status:** All v2 files have well-formed ID columns.
- **Recommended fix:** Require the ID to be in the designated column. Raise on empty or unparseable ID cells instead of searching other cells.

---

### [FRAGILITY-07] `_extract_metric_field()` passthrough fallback returns whole strings

- **Area:** Activation scoring, field resolution
- **File / function:** `backend/engine/activation.py` :: `_extract_metric_field()` (lines 288-289)
- **Implicit contract:** If no web-search keyword or backtick pattern is found, the entire metric_source string is returned as a field name. `BriefingPacket.get_field()` then tries to look up a field named (e.g.) `"DXY index"` or `"FXI 3-month return from low"`.
- **What would break it:** Already broken for 13 indicators (BUG-01). Any future `computed-mechanical` or `mechanical` indicator written without backtick field names will hit this path.
- **Why high-risk:** The passthrough is the root cause of BUG-01. It ensures silent failure rather than loud rejection.
- **Recommended fix:** Make this path raise instead of passing through. Every indicator should resolve to a known briefing field or be explicitly flagged as unresolvable.

---

### [FRAGILITY-08] Weight parsing silently drops indicators with non-numeric weights

- **Area:** Theory loader, activation table parsing
- **File / function:** `backend/engine/theory_loader.py` :: `_parse_activation_rows()` (lines 648-650)
- **Implicit contract:** The Weight column must contain a parseable number. If `_WEIGHT_NUM_RE.search()` finds no number, the entire indicator row is silently skipped.
- **What would break it:** A weight written as `"ten percent"` or an empty weight cell.
- **Current status:** All v2 files use numeric weights. Some have annotations like `0.33 [CALIBRATION]` — the regex correctly extracts `0.33` and ignores `[CALIBRATION]`.
- **Recommended fix:** Raise on unparseable weights instead of silently skipping.

---

### [FRAGILITY-09] Row length check silently drops short table rows

- **Area:** Theory loader, activation table parsing
- **File / function:** `backend/engine/theory_loader.py` :: `_parse_activation_rows()` (line 616)
- **Implicit contract:** Table rows must have at least 6 pipe-delimited cells. Shorter rows are silently skipped.
- **What would break it:** A malformed markdown table row (missing column, broken pipe).
- **Recommended fix:** Log a warning or raise when rows are dropped.

---

### [FRAGILITY-10] `theory_id` extraction depends on specific markdown patterns

- **Area:** Theory loader, theory identification
- **File / function:** `backend/engine/theory_loader.py` :: `_extract_theory_id()` (lines 45-67)
- **Implicit contract:** theory_id is extracted via two patterns: (1) a `## theory_id` section header with the ID on the next line in backticks, or (2) a frontmatter line `*theory_id: \`...\`*`. If neither matches, raises ValueError.
- **What would break it:** Rewriting the CORE.md header as `## Theory ID` (space, capitalized) or removing the backticks around the ID value.
- **Current status:** All 8 CORE.md files use a consistent format. The function is case-insensitive on the header (`line.strip().lower()`) but requires backtick-wrapped ID on the next line.
- **Recommended fix:** Accept the ID without backticks as well. Or add the theory_id as structured frontmatter.

---

### [FRAGILITY-11] Debt cycle short uses two-heading activation table format unique to it

- **Area:** Theory loader, phase detection
- **File / function:** `backend/engine/theory_loader.py` :: `_ACTIVATION_TABLE_RE` (line 577)
- **Implicit contract:** `debt_cycle_short` uses `## activation_table -- Phase A: Expansion` and `## activation_table -- Phase B: Contraction` as TWO separate `##` headers. All other two-phase theories use ONE `## activation_table` header with `### Phase A/B:` subsections inside.
- **What would break it:** If someone edits `debt_cycle_short` to use the subsection pattern instead, or edits another theory to use the two-header pattern, the phase detection could produce wrong results.
- **Current status:** Works correctly because the regex handles both patterns. But the two patterns are not interchangeable in edge cases (the two-header pattern embeds the phase name in the header; the subsection pattern uses `###` inside the section).
- **Recommended fix:** Standardize all two-phase theories on one format. Add a validator that rejects mixed patterns.

---

## Areas Reviewed With No Issues

1. **Falsifier registry matching (CORE.md to ACTIVATION.md):** All 8 theories have perfect 1:1 ID matches. Orphan validation is loud (raises ValueError). No string mismatches found.

2. **Prompt builder (`prompt_builder.py`):** Injects CORE.md, TACTICAL.md, PLAYBOOK.md as raw markdown with no parsing. No implicit formatting contracts. Changes to theory content pass through transparently to the LLM.

3. **Regime flag computation (`regime.py`):** Uses exact enum string comparison (`== "Active"`). No markdown parsing. No silent fallbacks.

4. **Web-search prefix re-injection (`_entry_to_indicator`):** Works correctly for all indicators where `data_ownership == "web-search"`. The re-injection is case-insensitive and handles double-prefix prevention.

5. **`[CALIBRATION]` weight annotations:** The weight regex (`_WEIGHT_NUM_RE`) correctly extracts the numeric value and ignores bracketed annotations. All 4 annotated weights in `capital_flows_v2` Phase A parse correctly.

6. **INTERACTION_MATRIX parsing:** Uses structured table parsing with column-name mapping. Handles known_ids filtering correctly. No implicit formatting dependencies found.

---

## Priority Order: Top 10 Fixes

| # | Finding | Why First | Effort |
|---|---------|-----------|--------|
| 1 | **BUG-01**: Restore backtick field names in 3 ACTIVATION.md files | Directly wrong scores on 3 theories. Blocks accurate pipeline runs. | Low — edit 3 markdown files |
| 2 | **FRAGILITY-07**: Make `_extract_metric_field()` passthrough raise instead of return | Prevents BUG-01 from ever recurring silently. Every future ACTIVATION.md edit that breaks field names will fail loudly. | Low — change 2 lines |
| 3 | **BUG-02**: Fix 10 non-standard direction strings | 3 indicators have semantically wrong comparisons. | Low — edit 5 ACTIVATION.md files |
| 4 | **BUG-06 + FRAGILITY-08 + FRAGILITY-09**: Add validation for data_ownership, weights, row length | Silent data loss. One validation function catches all three. | Low-Medium |
| 5 | **FRAGILITY-02**: Add column-name mapping to activation table parser | Fixed column positions are the most likely thing to break on a human edit. | Medium |
| 6 | **FRAGILITY-01**: Normalize section headers (underscore/space equivalence) | Second most likely human-edit breakage. | Low |
| 7 | **FRAGILITY-05 + FRAGILITY-06**: Restrict severity/ID extraction to designated columns | Prevents false matches from narrative text. | Medium |
| 8 | **BUG-05**: Fix `interest_exceeds_defense` threshold extraction | Currently produces a false negative on this indicator. | Low — edit threshold string |
| 9 | **BUG-04**: Replace `_normalize_computed_field()` generic fallback with strict lookup | Masked by BUG-01 today but becomes live when BUG-01 is fixed. | Low |
| 10 | **FRAGILITY-03 + FRAGILITY-10 + FRAGILITY-11**: Standardize and validate phase/header formats | Defensive. Prevents drift as theory files are edited over time. | Medium |

---

## Systemic Recommendation

The root issue across all findings is: **the engine parses prose as data without a schema.** Markdown tables are treated as structured input, but there is no validation layer between "text in a table cell" and "value used in scoring arithmetic."

The long-term fix is a **validation pass at load time** that checks every theory package against an explicit schema before any scoring runs. This pass would:

1. Verify every indicator's metric_source resolves to a known briefing field (or is explicitly marked unresolvable)
2. Verify every direction string is in the canonical set
3. Verify every data_ownership value is in the canonical set
4. Verify every weight is numeric
5. Verify every threshold has an extractable number
6. Verify all expected sections exist
7. Verify falsifier IDs are well-formed and matched 1:1
8. Verify phase structure matches declared `is_two_phase`

This validation should run as a pre-flight check before activation scoring and should fail loudly with specific error messages naming the theory, indicator, and field that failed.
