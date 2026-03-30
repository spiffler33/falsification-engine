# Theory Module: Capital Flow Dynamics & Multipolar Rebalancing

*Version 1.0 — March 2026*
*Status: Prototype — thresholds calibrated against the 2002-2007 EM supercycle, the 2017-2018 mini-rotation, and the 2020-2024 US dominance period. China-specific indicators less tested due to regime change in Chinese economic policymaking post-2020. Pending live testing.*

---

## theory_id

`capital_flows`

---

## activation_conditions

This theory has two distinct activation phases. The system must determine which phase is operative — they have different investment implications (one is watchlist, the other is deployment).

### Phase A: Accumulation

The valuation setup is present: EM is cheap relative to DM, the PE gap is wide, EM has underperformed for years. BUT the catalysts are absent or ambiguous — dollar is still strong or sideways, China credit impulse is flat or negative, RMB is not strengthening. The implication is MONITOR: build the watchlist, size the positions you WOULD take, identify the trigger levels — but don't deploy significant capital yet because EM value traps can persist for years without a catalyst.

| Indicator | Metric Source | Threshold | Direction | Weight | Rationale |
|-----------|--------------|-----------|-----------|--------|-----------|
| EM vs. DM PE gap at extremes | Web search: MSCI EM PE vs. MSCI World PE, or EEM PE vs. SPY PE | EM PE discount to DM exceeding 40% (e.g., EM at 12x, DM at 20x+) | gap widening or at extreme | 0.25 | The fundamental setup. Capital flows theory is a VALUATION ARBITRAGE mechanism — it requires that expected returns from EM meaningfully exceed DM. A 40%+ PE discount implies 3-5% annualized forward return advantage from multiple normalization alone, before earnings growth differential. The gap was ~15-20% during 2002-2007 (wide but not extreme). It has been 40-50%+ during 2022-2025 (historically extreme). The wider the gap, the larger the eventual rotation — but the gap can persist or widen further before closing. Width determines MAGNITUDE of eventual rotation. It does NOT determine TIMING. |
| EM rolling 3-year underperformance | computed: `eem_spy_3y_relative` | EEM underperformed SPY by 30%+ on a cumulative rolling 3-year basis | below | 0.20 | Mean reversion in relative performance. When EM has underperformed DM by 30%+ over rolling 3 years, subsequent 3-year relative returns have historically favored EM. The mechanism: underperformance compresses EM valuations (capital outflows → selling → lower prices → lower multiples → higher expected returns) while DM outperformance inflates DM valuations (inflows → buying → higher prices → higher multiples → lower expected returns). The relative return pendulum swings. The 30% threshold has been exceeded five times since 1988 — each time, subsequent 3-year EM relative return was positive. Sample size caveat: 5 observations. |
| Dollar strong or sideways | `DX-Y.NYB` (DXY) or `UUP` | DXY above 100 OR flat-to-rising over the prior 12 months | above or flat | 0.15 | The dollar is the gravity field. A strong dollar PREVENTS rotation even when valuations favor EM, because: (a) dollar-denominated EM debt becomes more expensive to service, (b) DM investors earning returns in appreciating dollar currency face no incentive to take EM currency risk, (c) strong dollar tightens EM financial conditions through the dollar funding channel. Accumulation phase requires that the dollar is STILL strong — it's the reason the gap persists despite the valuation setup being present. Once the dollar weakens, Phase B activates. |
| China credit impulse flat or negative | Web search: China credit impulse data, total social financing | China credit impulse at or below 0% (decelerating credit growth) | flat or negative | 0.15 | China is the swing variable for global EM. When China's credit impulse is negative (credit growth decelerating), Chinese domestic demand weakens, commodity demand declines, Asian supply chains slow, and capital flows out of EM broadly. Negative credit impulse = the primary catalyst is absent. The credit impulse is a LEADING indicator with 6-12 month transmission lag to global activity and asset prices. Flat or negative impulse during Accumulation means: the setup is building but the engine hasn't started. |
| No EM-positive catalysts firing yet | Composite qualitative check | RMB NOT strengthening, China PMI NOT accelerating, commodities NOT in uptrend, no major EM reform catalyst | qualitative | 0.15 | The absence of catalysts is what defines Accumulation vs. Rotation. If valuations are extreme but NO catalyst is present, capital will not rotate regardless of how cheap EM is. Value traps persist because the REASON EM is cheap (strong dollar, weak China, EM-specific risks) has not changed. This indicator is a composite check — all of the Phase B catalysts must be absent or ambiguous. |
| Geopolitical risk not escalating | Web search: US-China relations, Taiwan risk assessment, sanctions risk | No active escalation in US-China relations that would make China uninvestable for Western capital | not escalating | 0.10 | The geopolitical overlay. Even with perfect valuation and catalyst conditions, an acute geopolitical crisis (Taiwan conflict, severe sanctions, capital controls) would make the rotation trade uninvestable. During Accumulation, this indicator confirms that the geopolitical environment PERMITS eventual rotation — it's not a positive catalyst, it's the absence of a blocking condition. |

**Activation scoring for Phase A:**
- Weighted score ≥ 0.60 → **Active (Accumulation)**
- Weighted score 0.30–0.59 → **Adjacent (Accumulation)**
- Weighted score < 0.30 → **Inactive**

### Phase B: Rotation

The catalysts have arrived. Dollar is weakening, China credit impulse is positive, RMB is strengthening. Capital is actively rotating from DM to EM. The implication is DEPLOY: allocate to EM ETFs with conviction, funded by reducing DM equity overweight.

| Indicator | Metric Source | Threshold | Direction | Weight | Rationale |
|-----------|--------------|-----------|-----------|--------|-----------|
| Dollar weakening | `DX-Y.NYB` (DXY) or `UUP` | DXY declining for 3+ months AND below its 12-month moving average | below and falling | 0.25 | THE most important rotation catalyst. Dollar weakening eases EM financial conditions (dollar debt cheaper to service), improves EM terms of trade (commodity exporters earn more in local currency), and incentivizes DM investors to seek EM returns (declining dollar means EM currency appreciation adds to total return). Persistent dollar weakness — not a one-month blip — is what turns the valuation gap into actual capital movement. The 12-month MA crossover filters out short-term noise. |
| China credit impulse positive and accelerating | Web search: China credit impulse, total social financing growth | Credit impulse positive (above 0%) for 3+ months AND accelerating | above and rising | 0.20 | The engine has started. Positive credit impulse means China is easing — more credit creation, more domestic demand, more commodity consumption, more supply chain activity. The impulse leads Chinese GDP by ~6 months and global commodity prices by ~9-12 months. Accelerating impulse (not just positive but getting MORE positive) is the strongest signal — it means the easing is gaining momentum. The 2002, 2009, and 2016-2017 EM rotations all began within 6-12 months of China credit impulse turning positive. |
| RMB strengthening | Web search: USD/CNY spot rate, CNH offshore rate | USD/CNY declining (fewer yuan per dollar) for 3+ months | falling | 0.20 | Gave's #1 signal. RMB strengthening means capital is flowing TOWARD China — either through trade surplus, portfolio inflows, or deliberate PBOC policy. RMB direction is both a cause and an effect: strengthening RMB attracts more capital (self-reinforcing), and it signals that Chinese authorities are comfortable with currency appreciation (which implies confidence in the domestic economy). When RMB is weakening, even if other catalysts are present, the rotation is fragile because the currency signal contradicts the flow. |
| EM outperforming DM on relative basis | computed: `eem_spy_3m_relative` | EEM outperforming SPY for 3+ consecutive months | above | 0.15 | Price confirmation. Capital is actually moving. Relative outperformance over 3+ months eliminates one-month noise (positioning squeezes, index rebalancing) and confirms that real money is rotating. This is a LAGGING indicator — it confirms the rotation rather than predicting it. But it serves a critical filtering function: without price confirmation, the other catalysts may be present but capital is not actually flowing (the catalysts may be insufficiently strong). |
| Commodity prices rising | `DBC` or computed: `commodity_index_3m_change` | DBC or equivalent broad commodity index rising for 3+ months | above | 0.10 | Commodity demand confirms the China/EM growth story. Rising commodity prices benefit EM commodity exporters (Brazil, Russia, Australia, Middle East, Africa), improve EM terms of trade, and signal global demand recovery. Commodities also confirm the dollar-weakening channel (commodities priced in dollars tend to rise when dollar weakens). The 2002-2007 commodity supercycle was both a CAUSE and a SYMPTOM of the EM rotation. |
| FXI/KWEB leading | computed: `fxi_3m_return` or `kweb_3m_return` | FXI or KWEB up 15%+ from 3-month low | above | 0.10 | China leads the rotation. In every historical EM rotation, Chinese equities moved first and most aggressively (FXI +45% in 2017, +75% in 2009, +150% in 2006-2007). If China is NOT leading, the rotation is either narrow (India-only, which is a different thesis) or unconvincing. FXI/KWEB as lead indicators provide the regional specificity: China goes first, then broad EM follows with a 2-6 month lag. |

**Activation scoring for Phase B:**
- Weighted score ≥ 0.60 → **Active (Rotation)**
- Weighted score 0.30–0.59 → **Adjacent (Rotation)**
- Weighted score < 0.30 → **Inactive**

**Important:** Phases A and B are sequential, not mutually exclusive in the way fragility's phases are. Accumulation typically PRECEDES Rotation — the valuation gap builds during Accumulation and gets monetized during Rotation. If Phase B is Active, Phase A's conditions are also likely met (the valuation gap is still present — it hasn't fully closed). But the PHASE determination should be Phase B when the catalysts are firing, because the investment implication shifts from "monitor" to "deploy." Check Phase B first — if Active, classify as Rotation regardless of Phase A score.

**Transitional logic:** Adjacent (Rotation) while Accumulation is clearly Active is the most valuable state for the generator. It means: the valuation setup is fully present AND the catalysts are starting to appear but not yet confirmed. This is the "early rotation" window where the risk/reward is most favorable — EM is still cheap, catalysts are emerging, but the crowd hasn't piled in yet. The generator should produce hypotheses about both "rotation confirms" and "false start" in this state.

---

## core_mechanism

### Causal Chain

```
1. VALUATION GAP BUILDS (Accumulation Phase):
   Extended period of US outperformance creates extreme valuation gap.
   This happens because:
   (a) US tech earnings growth justifies US premium initially
   (b) Passive US inflows compound the premium (money flows into
       market-cap-weighted indices dominated by US mega-caps)
   (c) Strong dollar discourages EM allocation (currency headwind)
   (d) EM-specific events depress EM prices (China property crisis,
       regulatory crackdowns, commodity downturns, geopolitical risk)
   NET: EM at 11-12x PE, US at 22-24x PE. The gap is real, wide,
   and has been widening for 5+ years (2020-2025).
   ↓
2. CATALYST ARRIVES:
   The dollar weakens. Multiple possible triggers:
   (a) US growth disappoints → rate cut expectations → dollar declines
   (b) Fiscal dominance erodes dollar confidence → gradual weakening
   (c) EM growth accelerates (China easing) → relative growth gap
       narrows → capital rotates → dollar weakens reflexively
   (d) Geopolitical diversification → foreign central banks reduce
       dollar holdings → structural dollar demand declines
   
   The trigger matters less than the FACT of dollar weakness.
   Once the dollar weakens, everything downstream follows.
   ↓
3. DOLLAR WEAKNESS EASES EM FINANCIAL CONDITIONS:
   
   (a) Dollar-denominated debt becomes cheaper to service
       (EM governments and corporates with dollar bonds benefit)
   (b) Commodity export revenues increase in local currency
       (Brazil, Middle East, Australia, Africa benefit)
   (c) Currency mismatch risk declines
       (EM banking systems with dollar liabilities and local
       currency assets are less stressed)
   (d) Central banks gain room to ease domestically
       (no longer defending currency against dollar strength)
   ↓
4. CHINA CREDIT IMPULSE TRANSMITS GLOBALLY:
   
   When China eases credit:
   Month 0: Credit impulse turns positive. Visible in total social
            financing data.
   Month 3-6: Chinese domestic demand recovers. PMIs improve.
              Property starts stabilize. Commodity import volumes rise.
   Month 6-9: Global commodity prices rise (iron ore, copper, oil).
              Commodity-exporting EM countries benefit.
              Asian supply chain activity accelerates.
   Month 9-12: EM earnings revisions turn positive.
               Portfolio flows begin (visible in TIC data, fund flows).
              EEM starts outperforming SPY.
   Month 12-18: Rotation becomes consensus. Flows accelerate.
                FXI and KWEB lead. Broad EM follows.
   ↓
5. REFLEXIVE LOOP ACTIVATES:
   
   Capital flowing into EM → EM currencies strengthen → EM financial
   conditions ease further → EM growth accelerates → more capital
   flows in → EM currencies strengthen further.
   
   SIMULTANEOUSLY:
   Capital flowing out of US → US equities underperform on relative
   basis → dollar weakens further → more capital flows to EM.
   
   The reflexive loop is SELF-REINFORCING until it exhausts.
   It typically runs 2-5 years before reversing.
   The 2002-2007 loop ran 5 years.
   The 2017-2018 loop ran ~18 months before trade war disrupted it.
   ↓
6. REGIONAL SEQUENCING:
   
   (a) CHINA FIRST: FXI, KWEB. Highest beta, highest conviction
       when credit impulse is positive. Moves first and most.
       +30% to +50% in first year of rotation.
   (b) BROAD EM FOLLOWS: EEM. Broad exposure including Korea,
       Taiwan (tech supply chain), Brazil (commodities), India
       (domestic growth). +20% to +30% in first year.
   (c) INDIA on its own cycle: INDA. Less China-dependent,
       more domestic-demand driven. Participates in rotation
       but has its own structural growth story. Can outperform
       even without China rotation. +15% to +25%.
   (d) EUROPE as derivative play: VGK. European exporters
       (luxury goods, autos, industrials) with significant
       China revenue exposure benefit from China recovery.
       +10% to +20%.
   (e) JAPAN complicated: EWJ. Benefits from Asian growth recovery
       but yen dynamics can offset equity gains for USD-based
       investors. Lower conviction. +5% to +15%.
   ↓
7. ROTATION EXHAUSTS AND REVERSES:
   
   EM multiples normalize (PE gap narrows from 50% to 15-20%).
   Dollar stabilizes or re-strengthens (US growth reaccelerates
   or EM overheats and tightens). China credit impulse turns
   negative again (policy normalizes after easing). Capital
   rotates BACK to DM. The cycle resets to Accumulation.
   Duration of rotation phase: 2-5 years historically.
```

### The Dollar as Gravity Field

The dollar deserves special attention because it is the SINGLE MOST IMPORTANT VARIABLE in this theory. Everything else — China credit impulse, EM valuations, commodity prices — is downstream of or conditioned on dollar direction.

**Why the dollar is gravity:**

1. **Dollar-denominated debt:** Approximately $13T of dollar-denominated debt exists outside the US (BIS data). When the dollar strengthens, this debt becomes more expensive to service in local currency. This is a TIGHTENING of global financial conditions that the Fed does not control and may not intend. Conversely, dollar weakness is a LOOSENING that is arguably more powerful than Fed rate cuts for global conditions.

2. **Commodity pricing:** Most global commodities are priced in dollars. Dollar strength suppresses commodity prices (in dollar terms), hurting commodity exporters (most EM). Dollar weakness boosts commodity prices, helping the same countries.

3. **Portfolio return mechanics:** A DM investor holding EM assets earns returns in two components: local currency asset return + currency return. When the dollar is strengthening, the currency return is NEGATIVE (offsetting any local currency gains). When the dollar is weakening, currency return is POSITIVE (adding to local currency gains). This mechanical effect alone can add or subtract 5-15% per year to EM returns for a dollar-based investor.

4. **Reflexivity:** Dollar direction and capital flows are mutually reinforcing. Dollar weakness → capital flows to EM → EM currencies strengthen → dollar weakens further. Dollar strength → capital flows to US → EM currencies weaken → dollar strengthens further. The system has two stable equilibria (strong dollar / US dominance, and weak dollar / EM rotation) and transitions between them are non-linear.

### Time Horizon

**Full rotation cycle:** 8-15 years. US dominance phase (strong dollar, US outperformance): typically 5-8 years. EM rotation phase (weak dollar, EM outperformance): typically 2-5 years. The asymmetry exists because the US has structural advantages (deeper capital markets, better governance, tech innovation) that make US dominance the "default" state, while EM rotation requires specific catalysts.

**Accumulation phase:** Can persist 3-7 years. EM can be cheap and stay cheap for extended periods. The valuation gap is a necessary but not sufficient condition — without the catalyst (dollar weakening, China easing), the gap persists or widens.

**Rotation phase:** Typically 2-5 years once catalysts confirm. The first 12-18 months offer the best risk/reward (EM still cheap, catalysts freshly confirmed, crowd not yet positioned). After 18 months, the trade becomes consensus and the easy returns are captured.

**Tactically relevant window:** 1-3 months for Phase B confirmation (watching dollar, RMB, credit impulse), then 12-18 months of deployment once confirmed.

---

## predictions_when_active

### Directional (Phase A — Accumulation)

| Asset | Direction | Magnitude Range | Timeframe | Mechanism |
|-------|-----------|----------------|-----------|-----------|
| EEM | Underperform SPY (continue) | -5% to -15% relative per year | While Accumulation persists | No catalyst = no rotation. EM continues to underperform because the REASONS for underperformance (strong dollar, weak China, EM-specific risks) have not changed. The valuation gap may widen further. This is the value trap risk — cheap can get cheaper. |
| FXI, KWEB | Flat or declining | -10% to +5% | While China credit impulse is flat/negative | Chinese equities need the domestic credit cycle to turn. Without it, regulatory overhang, property stress, and demographic headwinds dominate. FXI/KWEB at current valuations (8-10x PE) are interesting but not actionable without the credit impulse catalyst. |
| INDA | Relative outperformer within EM | +5% to +15% | Rolling 12 months | India is the least China-dependent major EM market. Domestic demand growth, demographic dividend, and structural reform story (UPI, GST, manufacturing push) can drive India even without broader EM rotation. INDA can work during Accumulation phase when EEM doesn't — it's on its own cycle. |
| UUP | Flat or rising | +0% to +5% | While dollar is strong/sideways | Dollar remains supported by: US growth exceptionalism, yield advantage, safe haven status. No weakening catalyst yet. |
| GLD | Positive but driven by other theories | See fiscal_dominance modules | — | Gold during Accumulation is driven by fiscal dominance arithmetic and monetary architecture, NOT by capital flows theory. The dollar channel (gold benefits from weak dollar) is inactive during Accumulation because the dollar is still strong. |

### Directional (Phase B — Rotation)

| Asset | Direction | Magnitude Range | Timeframe | Mechanism |
|-------|-----------|----------------|-----------|-----------|
| FXI | Lead outperformer | +30% to +50% in first year | First 12-18 months of rotation | China leads every EM rotation. FXI's beta to China credit impulse is the highest in the EM complex. At current valuations (8-10x PE), the upside from multiple normalization alone is 50-80% (to 14-16x, which is still below historical average). Add earnings recovery from credit impulse and total return potential is 40-70% in a full rotation cycle. |
| KWEB | High-beta China play | +40% to +70% in first year | First 12-18 months | Chinese internet stocks are higher beta than FXI (more growth-oriented, more sentiment-driven). KWEB leads in the early rotation (risk-on, momentum, short covering) and can lag in late rotation (growth concerns resurface). Best as an EARLY rotation play, scaling down as rotation matures. |
| EEM | Broad EM rally | +20% to +30% in first year | First 12-18 months | EEM follows FXI with a 2-6 month lag. Includes Korea (semiconductors benefit from global recovery), Taiwan (TSMC benefits from demand recovery), Brazil (commodity exposure), South Africa, and others. The breadth of the EEM rally depends on whether the rotation is China-driven (narrow, Asia-heavy) or dollar-driven (broad, commodity exporters benefit equally). |
| INDA | Participates, may lag if already outperforming | +15% to +25% in first year | First 12-18 months | India benefits from rotation but may actually UNDERPERFORM FXI during Phase B because FXI is starting from lower valuations and higher beta. India's outperformance window is during Accumulation (when it works independently) and during late Rotation (when China-specific risks resurface but India's domestic story continues). |
| VGK | Derivative play via European exporters | +10% to +20% in first year | First 12-18 months | European luxury goods (LVMH, Hermès, Kering), autos (BMW, Mercedes, VW), and industrials (Siemens, Schneider) have significant China revenue exposure (20-40% for luxury). China recovery directly boosts European corporate earnings. VGK benefits without requiring direct EM allocation — useful for investors who want EM exposure with DM governance and liquidity. |
| EWJ | Mixed — yen complicates | +5% to +15% for equity, net return depends on yen | First 12-18 months | Japanese equities benefit from Asian growth recovery. BUT: yen strengthening (which typically accompanies dollar weakening) offsets equity gains for USD-based investors. If yen appreciates 10% while Nikkei rises 15%, the USD total return is ~5%. Lower conviction than other EM/Asia plays. Hedged EWJ (currency-hedged Japan ETF) may be appropriate. |
| SPY, QQQ | Underperform EM on relative basis | SPY +5% to +10%, but EEM +20% to +30% | During rotation | US equities don't necessarily DECLINE during EM rotation — they just lag. The 2003-2007 period: SPY +12% annualized while EEM +35% annualized. US equities still delivered positive returns; capital rotation doesn't require US decline, just relative underperformance. QQQ underperforms more than SPY because growth/tech premium compresses when global growth broadens. |
| UUP | Decline | -5% to -15% | During rotation | Dollar weakness IS the catalyst. DXY typically declines 10-20% during a full EM rotation cycle (DXY fell from 120 to 72 during 2002-2008). The decline is gradual, not a crash. |
| GLD | Benefits from dollar weakness channel | +10% to +20% per year (additional to fiscal dominance thesis) | During rotation | Gold gets a DOUBLE tailwind during rotation: the fiscal dominance/debasement channel (structural) PLUS the dollar weakness channel (cyclical). If both `fiscal_dominance_arithmetic` and `capital_flows` rotation are Active simultaneously, gold is structurally bid from multiple directions. |
| DBC | Outperform | +15% to +30% | During rotation | Commodities benefit from: (a) dollar weakness (pricing effect), (b) China demand recovery (fundamental demand), (c) EM growth acceleration (broader demand). Commodities are the purest play on the China credit impulse transmission after Chinese equities themselves. |

### Conditional (interaction with other theories)

| Condition | Prediction | Specificity Gain |
|-----------|-----------|-----------------|
| If `structural_fragility` is Active (Resolving) — a US equity break has occurred | A US equity correction is THE most powerful catalyst for EM rotation. The US premium (which kept capital in US assets despite higher EM expected returns) evaporates during the break. Prediction: EM initially declines WITH the US (correlated selloff, 1-3 months) then DIVERGES and outperforms the US recovery because: (a) EM didn't have the fragility buildup, (b) EM valuations were already cheap, (c) policy response in the US (rate cuts, QE) weakens the dollar, which is EM-positive. The sequencing: sell together → EM recovers faster → relative rotation begins. FXI leads the divergence. | Provides the TRIGGER that Accumulation phase was waiting for. A US fragility break converts Accumulation to Rotation by destroying the US premium and weakening the dollar. The specificity gain: the sequencing (correlated selloff → divergence → rotation) is tradeable. Buy EM AFTER the initial correlated decline, not before. |
| If `fiscal_dominance_liquidity` is Active and producing dollar weakness | Fiscal dominance creating dollar weakness IS the rotation catalyst. The mechanism: large deficits → abundant dollar supply → dollar depreciates → EM financial conditions ease → rotation begins. Prediction: this is a SLOWER, more gradual rotation than the fragility-break-driven version. FXI +20-30% over 12-18 months rather than +40-50% in 6 months. But it's MORE SUSTAINABLE because it's driven by a structural force (fiscal policy) rather than a one-time event (fragility break). | Distinguishes between fast rotation (US crisis-driven) and slow rotation (fiscal-dominance-driven). The trade expression is similar but the SIZING and URGENCY differ. Slow rotation: build positions gradually over 3-6 months. Fast rotation: deploy quickly within weeks of the break. |
| If `valuation_mean_reversion` is Active (US expensive) | The US-EM valuation gap means that BOTH theories point in the same direction: reduce US, add EM. Valuation theory says "US forward returns are poor." Capital flows theory says "EM forward returns are superior." Combined: fund the EM rotation by reducing US exposure. The portfolio construction is: underweight SPY/QQQ (valuation theory), overweight EEM/FXI/INDA (capital flows theory), hedge with GLD (benefits from dollar weakness that accompanies both). | Aligns two independent theories into a single portfolio expression. The confidence is higher than either theory alone because the case for EM overweight is supported by BOTH the domestic US valuation argument AND the international capital flow argument. |
| If `debt_cycle_short` is Active (Contraction) in the US but EM is expanding | US recession + EM growth = maximum rotation force. The growth differential (EM positive, US negative) is the widest possible, and capital follows growth differentials. Prediction: this produces the most powerful rotation — similar in magnitude to 2002-2007 (EEM +35% annualized vs. SPY +12%). Requires confirmation that EM IS actually expanding (China credit impulse positive, EM PMIs above 50) — if EM is also contracting, no rotation occurs and the thesis is invalidated for the cycle. | The critical CONDITIONALITY. Capital flows theory requires that EM is RECEIVING the capital — not just that the US is losing it. A global recession where both US and EM contract does NOT produce rotation. The evaluator must verify that EM growth indicators are genuinely positive, not just that US growth indicators are negative. |

---

## downstream_implications

### affects[]

| Target Theory | Relationship | Description |
|--------------|-------------|-------------|
| `valuation_mean_reversion` | **reinforces** | Capital flow rotation provides the MECHANISM for US valuation mean reversion. When capital rotates from US to EM, the selling pressure on US equities contributes to multiple compression. The rotation is one possible catalyst for US valuation to normalize. Conversely, extreme US valuations provide the fundamental REASON for capital to seek higher returns elsewhere. The two theories create a virtuous circle for the EM trade: US expensive (valuation theory) → capital seeks alternatives (capital flows) → US sells off (valuation reversion) → more capital flows to EM (capital flows accelerate). |
| `fiscal_dominance_liquidity` | **modifies** | Capital flow rotation, if it produces sustained dollar weakness, CHANGES the transmission of fiscal dominance. A weaker dollar means imported inflation rises (goods priced in other currencies become more expensive for US consumers). This accelerates the inflationary channel of fiscal dominance. The evaluator should check: when both theories are active, the inflation prediction should be at the upper end of the fiscal dominance range because dollar weakness adds an imported-inflation channel to the domestic-fiscal-inflation channel. |
| `monetary_architecture` | **reinforces** | Capital flow rotation toward EM is consistent with the multipolar monetary system that `monetary_architecture` describes. Capital diversifying from dollar assets to EM is the portfolio-level expression of the collateral diversification from Treasuries to gold and non-dollar reserves that monetary architecture identifies at the institutional level. Both theories describe the same underlying phenomenon (dollar system losing monopoly) from different perspectives (portfolio flows vs. central bank reserves). |
| `structural_fragility` | **triggered_by** | A US fragility break is one of the most powerful catalysts for capital flow rotation. The break destroys the US premium that was keeping capital at home. This is a one-directional dependency: fragility breaking TRIGGERS rotation, but rotation does not trigger fragility (capital slowly leaving the US doesn't cause a Minsky moment — it's a gradual rebalancing, not a forced liquidation). |

---

## falsifiers

### Hard Falsifiers

These conditions, if met, indicate that the capital flow rotation mechanism is NOT operative or that EM cannot capture the flows the theory predicts.

| # | Condition | Metric | Threshold | Rationale |
|---|-----------|--------|-----------|-----------|
| H1 | EM PE discount widens to 60%+ and persists for 5+ years without ANY rotation | Web search: MSCI EM PE vs. MSCI World PE | EM PE discount above 60% sustained for 5 years with no period of EM outperformance exceeding 6 months | If the valuation gap reaches historically unprecedented extremes AND persists without ANY rotation, the mean reversion mechanism may be broken. Possible explanations: structural EM discount is justified (governance, rule of law, capital controls permanently impair EM returns), or the US has achieved genuine permanent growth superiority (AI productivity revolution). Either explanation falsifies the theory. This has NEVER occurred in the historical record (EM has always outperformed at some point following extreme PE discounts), which is why the threshold is deliberately extreme (60%, 5 years). |
| H2 | China becomes genuinely uninvestable for Western capital | Geopolitical events | Taiwan conflict, comprehensive sanctions on Chinese financial system, or China imposes capital controls preventing foreign portfolio investment | If China — which represents ~30% of EEM and is the LEAD indicator for rotation — becomes uninvestable, the theory's magnitude predictions collapse. EM rotation without China is possible (India, Brazil, SE Asia) but the magnitude is 40-60% smaller. The theory as specified depends on China being investable. This falsifier doesn't kill the CONCEPT of capital flow rotation but kills the MAGNITUDE predictions. A China-ex rotation module would need to be built separately. |
| H3 | Dollar strengthens for 10+ years while all other rotation conditions are present | DXY trajectory + EM PE gap + China credit impulse | DXY appreciates for 10+ consecutive years while EM PE discount exceeds 40% and China credit impulse has been positive in at least 3 of those years | If the dollar strengthens persistently despite ALL the conditions that should weaken it (fiscal deficits, EM undervaluation, China easing), the dollar gravity field is too strong for valuation mean reversion to overcome. The dollar's reserve status, safe haven premium, and US growth superiority create a structural floor that rotation dynamics cannot breach. This would mean the theory is wrong about the relative power of valuation arbitrage vs. dollar gravity. 10 years is a demanding threshold but justified: 5-year dollar strength cycles are normal (1995-2002, 2011-2016, 2018-2024). Only 10+ years with simultaneously favorable rotation conditions would constitute genuine falsification. |

### Soft Falsifiers

| # | Condition | Metric | Threshold | Implication | Severity |
|---|-----------|--------|-----------|-------------|----------|
| S1 | China property crisis deepens into Japan-style balance sheet recession | Web search: China property starts, housing prices, bank NPLs, developer defaults | China new housing starts YoY declining 15%+ for 2+ months AND at least one major developer defaults or restructures AND RMB weakens past 7.40/USD | China's credit impulse becomes IMPOTENT even when positive: banks create credit but it doesn't transmit to demand because households and developers are repairing balance sheets (Japan 1990-2005 template). The credit impulse — the theory's primary catalyst — stops working. Rotation can still occur via non-China EM (India, Brazil, SE Asia) but the magnitude is 40-60% smaller and the lead indicator (RMB strengthening) becomes unreliable. | **medium** — early indicators of property distress wound the China catalyst channel but do not confirm a full Japan-style balance sheet recession and removes the primary catalyst mechanism. The theory's activation conditions (China credit impulse) remain formally triggered but the TRANSMISSION is broken. FXI/KWEB predictions are invalidated. EEM predictions reduce to the non-China EM contribution only. |
| S2 | Trade war / tariffs structurally reduce EM earnings potential | Web search: trade policy developments, tariff schedules, supply chain reshoring data | US effective tariff rate on China exceeds 40% AND China manufacturing PMI below 49 for 2+ months | Tariffs structurally impair the earnings base of EM exporters, particularly China. The valuation discount may be JUSTIFIED by permanently lower earnings potential rather than representing a temporary mispricing. The gap is a feature, not a bug. Reduces conviction in the "gap will close" prediction. India and Vietnam may benefit as alternative manufacturing destinations — the rotation redirects rather than disappears. | **medium** — weakens the mechanism for China specifically. The trade changes the GEOGRAPHY of rotation (away from China, toward India/Vietnam/Mexico) without eliminating the fundamental dynamic (capital seeks cheaper assets). The PE gap for non-China EM may still close. |
| S3 | US productivity miracle makes the PE premium genuinely justified | Web search: US productivity growth, AI implementation data, corporate earnings growth | US nonfarm productivity above 2.5% for latest quarter AND forward S&P 500 earnings revised up 5%+ within the quarter | If US growth is genuinely superior due to a productivity revolution, the US PE premium is not overvaluation — it's correct pricing of superior growth. EM's discount is justified because EM growth CANNOT match US growth. The valuation gap is rational. This doesn't prevent tactical rotations (EM can still rally on cyclical catalysts) but the STRUCTURAL case for EM convergence weakens. | **medium** — one quarter of strong productivity and earnings data wounds the convergence thesis but does not confirm a sustained US productivity miracle. If the PE gap is fundamentally justified rather than cyclically excessive, the mean reversion prediction is wrong. The theory reduces from "structural rotation inevitable" to "tactical rotation possible when catalysts align, but the PE gap should persist or widen over a full cycle." |
| S4 | EM-specific governance or institutional failures undermine the asset class | Web search: EM governance indicators, rule of law indices, capital controls | At least 1 EM market with >5% of EEM weight imposes capital controls or experiences governance crackdown within trailing 2 months | The EM discount is not a MISPRICING — it is correct compensation for genuine institutional risk. Capital doesn't rotate because the risks that created the discount are real and persistent. This is the "EM deserves to be cheap" counter-argument. Each country-specific failure (China regulatory crackdowns 2021, Russia sanctions 2022, Turkey institutional breakdown) narrows the investable EM universe. | **medium** — weakens the theory by reducing the investable universe. Some rotation is still possible among the "good" EM countries (India, select SE Asia, Poland, etc.), but the EEM-level thesis loses breadth. Country selection becomes more important than broad EM allocation. |
| S5 | Dollar weakens but EM does NOT outperform for 18+ months | DXY declining + EEM vs. SPY relative return | DXY declines 3%+ over trailing 2 months while EEM underperforms SPY in the same period | If the primary catalyst (dollar weakness) is present but the predicted response (EM outperformance) does not materialize, either the transmission mechanism is broken or other factors are overwhelming the dollar signal. Possible explanations: EM-specific risks dominating, dollar weakness driven by US fiscal crisis rather than EM strength (everyone sells dollars but nobody buys EM), or the dollar-to-EM-flows linkage has weakened structurally. | **minor** — a 2-month divergence between dollar weakness and EM performance may be noise; reduces diagnostic value but flags potential mechanism impairment. Either the mechanism has changed or the specific expression (EEM) is wrong. The theory may need recalibration of which EM markets benefit from dollar weakness (it may be commodity EM, not tech/manufacturing EM). Does not invalidate the theory entirely but impairs its trading utility for 12-18 months. |

| S6 | Primary predicted asset moves 15%+ against the hypothesis direction within the hypothesis holding window, without a corresponding fundamental falsifier triggering | Price of primary `predicted_assets` ticker(s) | 15% adverse move from hypothesis entry point within stated timeframe | The market is pricing information the hypothesis mechanism does not capture. Either the mechanism is wrong, the timeframe is wrong, or an unmodeled force is dominant. Does NOT automatically invalidate the mechanism — forced liquidations, positioning squeezes, and liquidity events can produce temporary adverse moves that reverse. But the hypothesis must explain the adverse move or accept the discount. | **medium** |

---

## metadata

```json
{
  "theory_id": "capital_flows",
  "version": 1,
  "last_updated": "2026-03-30",
  "update_type": "refinement",
  "confidence_in_specification": "medium",
  "notes": "This theory has the strongest historical mean-reversion evidence (EM has outperformed DM following every period of extreme PE discount) but the weakest catalyst-timing evidence (the waiting period in Accumulation can last 3-7 years, destroying carry and patience). Confidence in the STRUCTURAL setup (EM cheap, PE gap extreme) is high. Confidence in the CATALYST identification (dollar weakness + China credit impulse) is medium — the 2017-2018 rotation showed these catalysts can fire and then REVERSE (trade war). The China risk is the biggest uncertainty: if China is genuinely entering a Japan-style lost decade, the theory's magnitude predictions collapse by 40-60% (China is the lead indicator AND the largest weight in EEM). India partially offsets but cannot replace China's role in the mechanism. The geopolitical overlay (US-China competition, Taiwan risk) introduces a tail risk that cannot be mechanically scored — it is qualitative and binary (investable vs. not investable). Severity calibrations: S1 (China balance sheet recession) and S3 (US productivity miracle) are major because they directly challenge the core mechanism or cap predicted magnitude. S2 (trade war), S4 (governance), and S5 (decorrelation) are medium because they weaken or redirect the mechanism without eliminating it. The theory is most useful when combined with other theories: valuation_mean_reversion provides the US-side argument for why capital should leave, fiscal_dominance provides the dollar-weakening catalyst, and structural_fragility provides the potential trigger event. Added price action soft falsifier (medium severity, 0.25 discount) to close the gap where adverse price action was not captured by any pre-registered falsifier, forcing the LLM elimination pass to freelance on status assignment. The 15% threshold is calibrated above normal ETF monthly ranges (3-8%) to avoid triggering on noise.",
  "historical_episodes_referenced": [
    "2002-2007 EM supercycle (EEM ~35% annualized vs. SPY ~12% annualized for 5 years. DXY declined from 120 to 72. China credit impulse massively positive (WTO entry + infrastructure boom). Commodity supercycle. PE gap narrowed from ~40% to ~10%. The strongest and longest EM rotation in modern history.)",
    "2009-2010 post-GFC EM bounce (EEM +75% in 2009 vs. SPY +26%. China deployed massive fiscal stimulus (4T RMB). Credit impulse surge. Dollar weakened. Rotation was strong but brief — QE2 in the US re-strengthened the dollar by 2011 and EM underperformed again.)",
    "2017-2018 mini-rotation (FXI +45% in 2017. Dollar weakened. China credit impulse positive. EM PE gap wide. Looked like the start of a multi-year rotation. INTERRUPTED by US-China trade war beginning in 2018. DXY re-strengthened. FXI gave back most gains. Lesson: geopolitical risk can abort a rotation that has strong valuation and catalyst support.)",
    "2020-2024 US dominance (SPY +100%+ cumulative. EEM +15%. Massive underperformance. Drivers: US tech earnings growth (AI), strong dollar, China regulatory crackdown + property crisis, COVID policy divergence. PE gap widened to historical extremes (EM ~11x vs. US ~22x). This IS the Accumulation phase — the setup for the next rotation.)",
    "1997-1998 Asian crisis (the counter-example: EM was cheap and capital flowed OUT, not in. Dollar strengthened dramatically. EM currencies collapsed. Lesson: EM cheapness alone is NOT sufficient — the dollar direction is the binding constraint. Cheap EM + strong dollar = value trap, not rotation.)"
  ]
}
```

---

## Usage Notes for Generator and Evaluator

### For the Generator

When Phase A (Accumulation) is Active, generate hypotheses about:

- **The specific PE gap.** State the EM PE, DM PE, and the discount percentage. Compare to historical episodes: is the current gap wider or narrower than the pre-2002-2007 gap? How does it compare to the pre-2009 gap? Wider gap = larger potential magnitude of rotation.

- **Why the catalysts are absent.** Name the specific reasons rotation isn't happening yet: dollar is at X level and rising/flat because Y, China credit impulse is negative because Z, geopolitical risk is elevated because W. This matters because each absent catalyst has different implications for WHEN it might arrive.

- **India as independent play.** During Accumulation, INDA may work independently of the broader EM thesis. Generate India-specific hypotheses separately from the EEM/FXI thesis. India's domestic demand story, demographic dividend, and structural reform trajectory provide an independent case that doesn't require dollar weakness or China recovery.

- **Watchlist levels.** Specify the trigger levels that would shift from Accumulation to Rotation: DXY below X, USD/CNY below Y, China credit impulse above Z, FXI above W. These give the system concrete thresholds to monitor rather than vague "watch for catalysts."

When Phase B (Rotation) is Active, generate hypotheses about:

- **Regional sequencing and sizing.** Which EM markets first? What percentage allocation? China leads → broad EM follows → derivative plays (VGK, EWJ). Sizing should reflect conviction: FXI highest (20-30% of EM allocation), EEM next (30-40%), INDA (15-25%), VGK (10-15%), EWJ (5-10%).

- **Duration of the rotation.** Is this a 2-year or 5-year rotation? The credit impulse cycle and dollar cycle determine duration. If China credit impulse is likely to be positive for only 12-18 months (policy normalization), the rotation is shorter. If fiscal dominance is structurally weakening the dollar, the rotation is longer.

- **What would KILL the rotation.** Trade war escalation, China credit impulse reversal, dollar re-strengthening, geopolitical crisis (Taiwan). State the kill conditions explicitly so the system knows when to exit.

**What NOT to claim:**

- Do NOT claim EM will outperform just because it's cheap. Cheapness without catalyst = value trap. The 1997-1998 Asian crisis shows that EM can be cheap and get destroyed. ALWAYS require a catalyst (dollar weakening, China easing) before generating rotation hypotheses.
- Do NOT treat all EM as homogeneous. China, India, Brazil, Korea, Taiwan are different economies with different drivers. A China credit impulse helps China and commodity EM but may not help India. A dollar weakening helps all EM but benefits commodity exporters more than manufacturing exporters. The generator must specify which EM markets and why.
- Do NOT ignore the geopolitical overlay. The 2017-2018 experience shows that a trade war can abort a rotation that has strong fundamental and catalyst support. Every rotation hypothesis should include a geopolitical risk assessment, even if it concludes "risk is manageable."
- Do NOT assume rotation means US decline. During 2003-2007, SPY returned +12% annualized — a perfectly fine result. EM just returned +35%. Rotation is about RELATIVE performance, not absolute US losses. The generator should frame rotation as "add EM, reduce US overweight" not "sell US, buy EM."

### For the Evaluator

Priority checks:

1. **Did the generator specify the phase correctly?** Is the system really in Rotation (catalysts confirmed) or still in Accumulation (catalysts absent)? The temptation is to declare Rotation prematurely based on one month of dollar weakness or one positive China PMI print. Check the DURATION requirements: dollar weakening for 3+ months, credit impulse positive for 3+ months, EEM outperforming for 3+ months. Premature Rotation calls lead to value trap losses.

2. **Is the China risk addressed?** Every FXI/KWEB hypothesis must address: is China in a Japan-style balance sheet recession? If yes, the credit impulse catalyst is impotent even if formally positive. If no, what's the evidence? The evaluator should require specific evidence on China housing, bank NPLs, and credit transmission — not just the credit impulse number.

3. **Is the dollar direction call credible?** Dollar direction is the binding constraint. If the generator predicts rotation while the dollar is strengthening, challenge it. The generator must explain why the dollar will weaken (fiscal dominance, relative growth shift, policy divergence). "Dollar should weaken because it's overvalued" is insufficient — the dollar can stay overvalued for years.

4. **Are magnitude estimates realistic?** FXI +50% in year one is historically achievable during strong rotation (2009, 2006-2007). But it requires confirmed catalysts, not Accumulation-phase positioning. If the generator claims +50% FXI during Accumulation, that's an error — Accumulation produces +/-10% with no clear direction. Magnitude must match the phase.

5. **Composition quality check.** The most valuable compositions: capital_flows + structural_fragility (fragility break triggers rotation — the sequencing is tradeable), capital_flows + valuation_mean_reversion (US expensive + EM cheap = fund rotation by reducing US), capital_flows + fiscal_dominance (deficit-driven dollar weakness = structural catalyst for rotation). If the composition doesn't identify a specific trigger, sequencing, or sizing recommendation beyond "add EM," it's not adding value.

6. **Is India treated separately?** India has its own cycle and can work during Accumulation. A hypothesis that lumps India with broad EM ("EEM will outperform") may miss the India-specific opportunity. The evaluator should check whether INDA deserves its own hypothesis independent of the FXI/EEM thesis.
