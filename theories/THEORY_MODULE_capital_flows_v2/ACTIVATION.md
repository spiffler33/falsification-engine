# ACTIVATION.md — Capital Flow Dynamics & Multipolar Rebalancing

*Theory Package: capital_flows*

---

## phases

Two-phase theory with sequential activation logic. The phases represent different stages of the same cycle, not mutually exclusive states.

- **Phase A: Accumulation** — The valuation setup is present (EM cheap relative to DM, PE gap wide, EM has underperformed for years) but the catalysts are absent or ambiguous (dollar strong or sideways, China credit impulse flat or negative, RMB not strengthening). Investment implication: MONITOR. Build the watchlist, size positions to deploy later, identify trigger levels. Do not deploy significant capital — EM value traps can persist for years without a catalyst.

- **Phase B: Rotation** — The catalysts have arrived. Dollar is weakening, China credit impulse is positive, RMB is strengthening. Capital is actively rotating from DM to EM. Investment implication: DEPLOY.

---

## transition_logic

**Check Phase B first.** If Phase B is Active, classify as Rotation regardless of Phase A score. This is because Phase B's conditions subsume Phase A's setup — the valuation gap is still present during Rotation (it hasn't closed yet), but the investment implication has shifted from monitor to deploy.

**Sequential, not mutually exclusive.** Accumulation typically precedes Rotation. The valuation gap builds during Accumulation and gets monetised during Rotation.

**Most valuable transitional state:** Adjacent (Rotation) while Accumulation is clearly Active. This means the valuation setup is fully present AND catalysts are emerging but not yet confirmed. This is the "early rotation" window where risk/reward is most favourable — EM is still cheap, catalysts are appearing, but the crowd hasn't positioned. The generator should produce hypotheses about both "rotation confirms" and "false start" in this state.

**Precedence:** Phase B > Phase A. If Phase B ≥ 0.30 (Adjacent), use Phase B as the active classification. If Phase B < 0.30 (Inactive), fall back to Phase A classification.

---

## activation_table

### Phase A: Accumulation

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| EM vs. DM PE gap at extremes | MSCI EM PE vs. MSCI World PE, or broad EM vs. broad DM PE ratios | `web-search` — no single API provides standardised cross-index PE comparisons; preferred sources: MSCI, Bloomberg, Yardeni Research | EM PE discount to DM exceeding 40% (e.g., EM at 12x, DM at 20x+) | above | 0.33 `[CALIBRATION]` | The fundamental setup. A 40%+ PE discount implies 3–5% annualised forward return advantage from multiple normalisation alone, before earnings growth differential. The gap was ~15–20% during 2002–2007 (wide but not extreme), and 40–50%+ during 2022–2025 (historically extreme). Width determines MAGNITUDE of eventual rotation, not TIMING. Weight redistributed from 0.25 after two qualitative indicators moved to context flags. |
| EM rolling 3-year underperformance | Computed: `eem_spy_3y_relative` (EEM vs. SPY cumulative rolling 3-year relative return) | `computed-mechanical` — Dependencies: EEM price series (Yahoo Finance), SPY price series (Yahoo Finance). Both must be current; if either is stale, computation is silently wrong. | EEM underperformed SPY by 30%+ cumulative on rolling 3-year basis | Below | 0.27 `[CALIBRATION]` | Mean reversion in relative performance. Underperformance compresses EM valuations (capital outflows → selling → lower prices → lower multiples → higher expected returns) while DM outperformance inflates DM valuations. The 30% threshold has been exceeded five times since 1988 — each time, subsequent 3-year EM relative return was positive. Sample size caveat: 5 observations. Weight redistributed from 0.20 after two qualitative indicators moved to context flags. |
| Dollar strong or sideways | `dxy_index` (DXY Dollar Index via Yahoo Finance DX-Y.NYB) | `mechanical` — DXY available via Yahoo Finance (`DX-Y.NYB`), exposed as computed field `dxy_index` | DXY above 100 OR flat-to-rising over the prior 12 months | above | 0.20 `[CALIBRATION]` | The dollar is the gravity field. A strong dollar PREVENTS rotation: dollar-denominated EM debt becomes more expensive, DM investors face no incentive to take EM currency risk, strong dollar tightens EM financial conditions. Accumulation requires that the dollar is STILL strong — it's the reason the gap persists despite the valuation setup. Weight redistributed from 0.15 after two qualitative indicators moved to context flags. |
| China credit impulse flat or negative | China total social financing growth, credit impulse calculation | `web-search` — no single mechanical API; preferred sources: PBoC data, Bloomberg, MacroMicro | Credit impulse at or below 0% (decelerating credit growth) | below | 0.20 `[CALIBRATION]` | China is the swing variable for global EM. Negative credit impulse = primary catalyst absent. The credit impulse leads Chinese GDP by ~6 months and global commodity prices by ~9–12 months. Flat or negative during Accumulation means: setup building but engine hasn't started. Weight redistributed from 0.15 after two qualitative indicators moved to context flags. |

**Phase A scoring:**
- Weighted score ≥ 0.60 → **Active (Accumulation)**
- Weighted score 0.30–0.59 → **Adjacent (Accumulation)**
- Weighted score < 0.30 → **Inactive**

### Phase B: Rotation

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| Dollar weakening | `dxy_index` (DXY Dollar Index via Yahoo Finance DX-Y.NYB) | `mechanical` — Yahoo Finance (`DX-Y.NYB`), exposed as computed field `dxy_index` | DXY declining for 3+ months AND below its 12-month moving average | Below and falling | 0.25 | THE most important rotation catalyst. Dollar weakening eases EM financial conditions, improves EM terms of trade, and incentivises DM investors to seek EM returns. Persistent weakness — not a one-month blip — is what turns the valuation gap into actual capital movement. The 12-month MA crossover filters short-term noise. |
| China credit impulse positive and accelerating | China total social financing, credit impulse | `web-search` — no mechanical API; preferred sources: PBoC, Bloomberg, MacroMicro | Credit impulse positive (above 0%) for 3+ months AND accelerating | Above and rising | 0.20 | The engine has started. Positive impulse means China is easing. The impulse leads Chinese GDP by ~6 months and global commodity prices by ~9–12 months. Accelerating impulse is the strongest signal. The 2002, 2009, and 2016–2017 EM rotations all began within 6–12 months of China credit impulse turning positive. |
| RMB strengthening | `usdcny` (USD/CNY spot rate) | `mechanical` — USD/CNY available via Yahoo Finance (`CNY=X`) or similar FX feeds | USD/CNY declining (fewer yuan per dollar) for 3+ months | Falling | 0.20 | Gave's primary signal. RMB strengthening means capital is flowing toward China. RMB direction is both cause and effect: strengthening RMB attracts more capital (self-reinforcing), and signals that Chinese authorities are comfortable with currency appreciation. When RMB is weakening, even if other catalysts are present, the rotation is fragile. |
| EM outperforming DM on relative basis | Computed: `eem_spy_3m_relative` (EEM vs. SPY 3-month relative return) | `computed-mechanical` — Dependencies: EEM price series (Yahoo Finance), SPY price series (Yahoo Finance) | EEM outperforming SPY for 3+ consecutive months | Above | 0.15 | Price confirmation. Capital is actually moving. This is a LAGGING indicator — confirms rotation rather than predicting it. But it serves a critical filter: without price confirmation, the other catalysts may be present but capital is not actually flowing. |
| Commodity prices rising | `commodity_index_3m_change` (broad commodity index, DBC or equivalent) | `mechanical` — DBC available via Yahoo Finance | Broad commodity index rising for 3+ months | Above | 0.10 | Commodity demand confirms the China/EM growth story. Rising commodity prices benefit EM commodity exporters, improve EM terms of trade, and signal global demand recovery. Commodities also confirm the dollar-weakening channel. |
| Chinese equities leading | `fxi_3m_return` (FXI 3-month return from low) | `mechanical` — FXI available via Yahoo Finance | FXI up 15%+ from 3-month low | Above | 0.10 | China leads the rotation. In every historical EM rotation, Chinese equities moved first and most aggressively. If China is NOT leading, the rotation is either narrow or unconvincing. Provides regional specificity: China goes first, then broad EM follows with a 2–6 month lag. |

**Phase B scoring:**
- Weighted score ≥ 0.60 → **Active (Rotation)**
- Weighted score 0.30–0.59 → **Adjacent (Rotation)**
- Weighted score < 0.30 → **Inactive**

---

## activation_thresholds

| Phase | Active | Adjacent | Inactive |
|-------|--------|----------|----------|
| Phase A: Accumulation | ≥ 0.60 | 0.30–0.59 | < 0.30 |
| Phase B: Rotation | ≥ 0.60 | 0.30–0.59 | < 0.30 |

---

## context_flags

These qualitative assessments are NOT scored but are surfaced to the generator for hypothesis formation.

| Flag | Description | Why Context, Not Scored |
|------|-------------|------------------------|
| EM catalyst absence composite | Composite check: RMB NOT strengthening, China PMI NOT accelerating, commodities NOT in uptrend, no major EM reform catalyst. Defines the boundary between Accumulation and Rotation. | Originally scored at 0.15 weight in Phase A. Reclassified: this is a composite qualitative check that overlaps with multiple scored indicators (China credit impulse, dollar direction, commodity prices). As scored, it double-counted signals already captured by individual indicators. As context, it provides the generator with a useful summary of catalyst status without inflating the activation score. |
| Geopolitical risk level | Assessment of US-China relations, Taiwan risk, sanctions risk, and whether the geopolitical environment permits eventual rotation. Specifically: is China investable for Western capital? | Originally scored at 0.10 weight in Phase A. Reclassified: this is inherently qualitative judgment dressed up as a scored indicator. There is no mechanical threshold for "geopolitical risk." The assessment requires interpretation of diplomatic signals, policy statements, and military postures. Moving to context preserves its value as a blocking-condition check without pretending it is mechanically scorable. |
| India independent cycle | Assessment of whether India's domestic demand story, demographic dividend, and structural reform trajectory provide an independent investment case separate from the China-driven EM rotation thesis. | India can work during Accumulation when broad EM does not. The generator should consider India-specific hypotheses separately from the broad EM rotation thesis. |
| China balance sheet recession risk | Assessment of whether China is entering a Japan-style lost decade: property investment declining multi-year, housing prices down 30%+ nationally, bank NPLs rising. If yes, the credit impulse catalyst is impotent even when formally positive — banks create credit but it doesn't transmit to demand. | Not scorable mechanically but critical for interpretation of the China credit impulse indicator. A formally positive credit impulse in a balance sheet recession has no transmission to the real economy. |

---

## falsifier_severity_assignments

### Theory-Level Falsifiers (from CORE.md)

These severity assignments are scoring pipeline parameters. The conditions are defined in CORE.md; only severity classification lives here.

| Falsifier | Severity | Rationale |
|-----------|----------|-----------|
| H1: EM PE discount widens to 60%+ and persists 5+ years without rotation | N/A — hard falsifier | Hard falsifiers kill the theory. No severity discount; if triggered, the theory is invalidated. |
| H2: China becomes genuinely uninvestable | N/A — hard falsifier | Hard falsifier. If triggered, theory's magnitude predictions collapse. |
| H3: Dollar strengthens 10+ years with favourable rotation conditions present | N/A — hard falsifier | Hard falsifier. If triggered, the dollar gravity field cannot be overcome by valuation arbitrage. |

### Soft Falsifiers (State-Level)

| Falsifier | Severity | Discount | Rationale |
|-----------|----------|----------|-----------|
| S1: China property crisis deepens into Japan-style balance sheet recession (property investment declining 5+ years, housing prices down 30%+, bank NPLs above 5%) | **major** | 0.45 | Directly caps predicted magnitude and removes the primary catalyst mechanism. Credit impulse activation conditions remain formally triggered but TRANSMISSION is broken. Broad EM predictions reduce to non-China contribution only. |
| S2: Trade war / tariffs structurally reduce EM earnings potential (US tariffs on China exceed 50% average AND evidence of meaningful supply chain relocation) | **medium** | 0.25 | Weakens mechanism for China specifically. Changes the GEOGRAPHY of rotation (away from China, toward India/Vietnam/Mexico) without eliminating the fundamental dynamic. PE gap for non-China EM may still close. |
| S3: US productivity miracle makes PE premium genuinely justified (US nonfarm productivity growth above 3% for 3+ years AND S&P earnings growth above 15% annualised for 3+ years, driven by verifiable technology deployment) | **major** | 0.45 | Directly challenges core mechanism. If PE gap is fundamentally justified by superior growth, mean reversion prediction is wrong. Theory reduces from "structural rotation inevitable" to "tactical rotation possible when catalysts align, but PE gap should persist or widen over full cycle." |
| S4: EM governance or institutional failures undermine the asset class (multiple markets representing 30%+ of broad EM index impose capital controls, experience governance crackdowns, or have institutional deterioration impairing property rights) | **medium** | 0.25 | Weakens theory by reducing investable universe. Some rotation still possible among remaining investable EM. Country selection becomes more important than broad allocation. |
| S5: Dollar weakens but EM does NOT outperform for 18+ months (DXY down 10%+ over 18 months while broad EM underperforms DM) | **medium** | 0.25 | The catalyst is firing but the trade isn't working. Either transmission mechanism is broken or other factors are overwhelming the dollar signal. Does not invalidate theory entirely but impairs trading utility. May indicate wrong EM expression rather than wrong theory. |

---

## state_falsifiers

| Condition | Applicable Phase | Severity | Description |
|-----------|-----------------|----------|-------------|
| Dollar reversal during early Rotation | Phase B | **major** (0.45) | If the dollar re-strengthens within the first 6 months of Phase B activation (before the reflexive loop has established), the rotation is a false start. The 2017–2018 experience: catalysts fired, rotation began, trade war aborted it. Dollar reversal before the loop is self-sustaining forces reclassification back to Phase A. |
| China credit impulse reversal during Rotation | Phase B | **major** (0.45) | If China credit impulse turns negative within the first 12 months of Phase B activation, the primary catalyst has been withdrawn. Rotation may stall or reverse. Requires reassessment of whether Phase B conditions are genuinely met or were temporary. |
| Premature Rotation declaration | Phase A → Phase B | **medium** (0.25) | If Phase B is declared Active based on one month of dollar weakness or one positive China PMI print without meeting the DURATION requirements (3+ months for each catalyst), the classification is premature. This is a state-detection error, not a theory failure. The evaluator must enforce duration thresholds. |

---
