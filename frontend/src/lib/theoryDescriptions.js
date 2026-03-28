/**
 * theoryDescriptions.js -- Curated theory module content for the TheoryDetail overlay.
 * Embedded in the frontend so it works on GitHub Pages without a backend.
 * Source of truth: theories/THEORY_MODULE_*_v1.md
 */

const theories = {
  valuation_mean_reversion: {
    title: 'Valuation Mean Reversion & Margin of Safety',
    summary:
      'Identifies when equity valuations have expanded beyond what future cash flows can support. High multiples mechanically compress forward real returns and amplify drawdown magnitude when catalysts arrive. The mechanism is arithmetic: paying a high price today borrows returns from the future.',
    horizon: '7-10 years (aggregate), 1-3 years (sector rotation)',
    twoPhase: false,
    coreMechanism: [
      'Asset prices rise over an extended period, driven by earnings growth, multiple expansion, passive inflows, momentum, and narrative.',
      'Price detaches from cash flow: PE expansion, CAPE above 30, equity risk premium compresses toward zero.',
      'Opportunity cost becomes measurable: when SHY yields more than the S&P earnings yield, cash is the superior risk-adjusted holding.',
      'This state can persist for years -- momentum, FOMO, fiscal liquidity, and narrative sustain it.',
      'Resolution arrives via one of three channels: price decline (crash), earnings growth (soft landing), or inflationary grind (nominal prices flat, real value erodes).',
    ],
    indicators: [
      { name: 'Equity risk premium compressed', threshold: 'Below 1.0%', weight: 0.25 },
      { name: 'Shiller CAPE elevated', threshold: 'Above 30', weight: 0.20 },
      { name: 'Buffett Indicator extreme', threshold: 'Above 1.5x GDP', weight: 0.15 },
      { name: 'Cash yield exceeds earnings yield', threshold: 'SHY yield > SPY earnings yield', weight: 0.15 },
      { name: 'Corporate profit margins at cycle highs', threshold: 'Net margins above 12%', weight: 0.10 },
      { name: 'Market breadth narrow', threshold: 'QQQ/IWM ratio at 2yr high, RSP underperforming', weight: 0.10 },
      { name: 'Insider selling elevated', threshold: 'Sell/buy ratio above 5:1 for 3+ months', weight: 0.05 },
    ],
    predictions: [
      { asset: 'SPY', direction: 'Poor forward real returns', magnitude: '+0% to +4% annualized real over 7-10yr' },
      { asset: 'SPY', direction: 'Elevated drawdown magnitude', magnitude: '-25% to -50% (conditional on catalyst)' },
      { asset: 'SHY', direction: 'Outperform on risk-adjusted basis', magnitude: '+4% to +5.5% annualized' },
      { asset: 'GLD', direction: 'Benefits from inflationary resolution', magnitude: '+10% to +25%/yr' },
      { asset: 'Sector rotation', direction: 'Cheap sectors outperform index', magnitude: '+5% to +15% relative' },
      { asset: 'EFA/VGK', direction: 'Outperform SPY on relative basis', magnitude: '+3% to +7% annualized over 5yr' },
    ],
    hardFalsifiers: [
      'Forward 10-year real returns from CAPE 30+ exceed 7%',
      'Equity risk premium below 0.5% for 10+ years without a drawdown exceeding 20%',
      'Profit margins do NOT revert over a full business cycle (stay above 11% through recession)',
    ],
    softFalsifiers: [
      { condition: 'Rates decline substantially, improving ERP from denominator', severity: 'major' },
      { condition: 'Earnings growth exceeds 15% annualized for 3+ years', severity: 'medium' },
      { condition: 'Financial repression makes cash a losing proposition in real terms', severity: 'medium' },
      { condition: 'Market broadening reduces concentration-driven overvaluation', severity: 'minor' },
      { condition: 'International valuations converge upward rather than US converging down', severity: 'minor' },
    ],
  },

  debt_cycle_short: {
    title: 'Short-Term Debt Cycle',
    summary:
      'Tracks the credit expansion-contraction oscillation that drives the 3-7 year business cycle. Credit growth amplifies economic expansion; credit contraction triggers downturn. The cycle operates through four quadrants (Goldilocks, Reflation, Stagflation, Deflation) based on growth and inflation direction.',
    horizon: '3-7 years (full cycle), 6-18 months (phase transition)',
    twoPhase: true,
    phases: ['Expansion', 'Contraction'],
    coreMechanism: [
      'Credit expands: banks lend more freely, consumers and businesses borrow, spending accelerates beyond income growth.',
      'Growth begets confidence begets more credit -- reflexive loop drives expansion beyond sustainable levels.',
      'Central bank tightens (raises rates, restricts credit) to slow inflation or cool speculation.',
      'Credit contracts: lending standards tighten, borrowers retrench, spending falls below income growth.',
      'Contraction feeds on itself until policy response (rate cuts, fiscal stimulus) restarts the cycle.',
    ],
    indicators: [
      { name: 'ISM Manufacturing proxy', threshold: 'Expansion: above 50 / Contraction: below 48', weight: 0.15 },
      { name: 'Unemployment rate', threshold: 'Expansion: below 5% / Contraction: Sahm Rule triggered (+0.5% from trough)', weight: 0.175 },
      { name: 'Credit spreads (HY OAS)', threshold: 'Expansion: below 450bp / Contraction: above 500bp, widening', weight: 0.15 },
      { name: 'Yield curve (10Y-2Y)', threshold: 'Expansion: not deeply inverted / Contraction: re-steepening from inversion', weight: 0.125 },
      { name: 'Initial jobless claims', threshold: 'Expansion: below 250K / Contraction: above 280K, rising 8+ weeks', weight: 0.10 },
      { name: 'Fed funds vs nominal GDP', threshold: 'Expansion: below GDP growth / Contraction: above GDP by 1%+ for 6+ months', weight: 0.10 },
      { name: 'Credit growth (SLOOS)', threshold: 'Expansion: positive / Contraction: broad tightening 2+ quarters', weight: 0.15 },
    ],
    predictions: [
      { asset: 'SPY', direction: 'LONG (Expansion)', magnitude: '+10% to +20% annualized' },
      { asset: 'SPY', direction: 'Drawdown (Contraction)', magnitude: '-20% to -40%' },
      { asset: 'TLT', direction: 'LONG (Contraction, deflationary)', magnitude: '+15% to +30%' },
      { asset: 'SHY', direction: 'Outperform in Contraction', magnitude: '+4% to +5.5%' },
      { asset: 'GLD', direction: 'LONG (Stagflation quadrant)', magnitude: '+10% to +25%' },
      { asset: 'HYG', direction: 'SHORT (Contraction)', magnitude: '-10% to -25%' },
    ],
    hardFalsifiers: [
      'Credit contracts for 18+ months without recession materializing',
      'Recession occurs without prior credit cycle tightening (exogenous cause invalidates cycle model)',
      'Yield curve inversion ceases to predict recessions (3 consecutive false signals)',
    ],
    softFalsifiers: [
      { condition: 'Central bank preemptive easing prevents full contraction', severity: 'major' },
      { condition: 'Fiscal stimulus offsets credit contraction', severity: 'medium' },
      { condition: 'Global cycle desynchronization (US expansion while peers contract)', severity: 'medium' },
      { condition: 'Shadow banking credit substitutes for traditional lending', severity: 'minor' },
    ],
  },

  debt_cycle_long: {
    title: 'Long-Term Debt Cycle',
    summary:
      'Describes the multi-decade accumulation of debt where each recession is resolved with MORE debt rather than deleveraging. The system progressively transitions from rate cuts (MP1) to QE (MP2) to fiscal-monetary coordination (MP3), culminating in devaluation as the resolution mechanism.',
    horizon: '10-30 years (structural backdrop)',
    twoPhase: false,
    coreMechanism: [
      'Each short-cycle recession is resolved by adding more debt and lowering rates, preventing full deleveraging.',
      'Over decades, total debt/GDP ratchets upward: each recovery starts from a higher debt base.',
      'Policy tools exhaust in sequence: rate cuts (MP1) hit zero → QE (MP2) expands balance sheet → fiscal dominance (MP3) coordinates spending.',
      'Eventually the debt burden can only be resolved by devaluation: inflation erodes the real value of nominal claims.',
      'This is the structural backdrop against which all shorter-horizon theories operate.',
    ],
    indicators: [
      { name: 'Total debt/GDP', threshold: 'Above 250%', weight: 0.20 },
      { name: 'Fed balance sheet / GDP', threshold: 'Above 20%', weight: 0.20 },
      { name: 'Rates near effective lower bound', threshold: 'Within recent memory of zero bound', weight: 0.15 },
      { name: 'Fiscal deficit with weak private credit', threshold: 'Deficit >5% GDP, private credit <3%', weight: 0.15 },
      { name: 'Wealth inequality at extremes', threshold: 'Top 10% own >70% of wealth', weight: 0.10 },
      { name: 'Negative real rates during expansion', threshold: 'Fed funds - CPI < 0 during growth', weight: 0.10 },
      { name: 'Escalating intervention scale', threshold: 'Each crisis requires larger response', weight: 0.10 },
    ],
    predictions: [
      { asset: 'GLD', direction: 'Structural LONG', magnitude: 'Appreciates as devaluation progresses' },
      { asset: 'TLT', direction: 'Negative real returns', magnitude: 'Nominal returns < inflation over decade' },
      { asset: 'TIP', direction: 'Outperform nominal bonds', magnitude: '+3% to +5% relative to TLT' },
      { asset: 'SPY', direction: 'Nominal gains, poor real returns', magnitude: '+3% to +7% nominal, 0-3% real' },
    ],
    hardFalsifiers: [
      'Genuine deleveraging occurs: total debt/GDP declines by 30%+ without hyperinflation or depression',
      'Productivity revolution grows out of the debt (GDP growth exceeds debt growth for a decade)',
      'Political will produces sustained fiscal surplus (surplus >1% GDP for 5+ years)',
    ],
    softFalsifiers: [
      { condition: 'Reserve currency status allows indefinite deficit financing', severity: 'major' },
      { condition: 'AI productivity gains permanently raise GDP growth above interest cost', severity: 'medium' },
      { condition: 'Demographic tailwind from immigration supports tax base', severity: 'minor' },
    ],
  },

  structural_fragility: {
    title: 'Structural Fragility (Minsky Dynamics)',
    summary:
      'Diagnoses accumulating structural risk from concentration, leverage, passive flows, and illiquidity masquerading as stability. Markets appear calm but systemic fragility builds. When catalysts arrive, forced selling cascades override fundamental values, producing overshoots in both directions.',
    horizon: '6-24 months (phase transition)',
    twoPhase: true,
    phases: ['Building', 'Resolving'],
    coreMechanism: [
      'Stability breeds complacency: low volatility encourages higher leverage and concentrated positions.',
      'Passive indexing amplifies concentration -- capital flows into the same names regardless of valuation.',
      'Capex/revenue mismatches build (currently: AI infrastructure spending exceeds revenue by 3x+).',
      'When a catalyst arrives, forced selling cascades: margin calls, passive rebalancing, and risk parity unwinds all hit simultaneously.',
      'The break overshoots fair value on the downside (Resolving phase), creating deployment opportunities.',
    ],
    indicators: [
      { name: 'VIX level', threshold: 'Building: below 14 / Resolving: above 35', weight: 0.15 },
      { name: 'VIX-realized vol gap', threshold: 'Building: above 5 points', weight: 0.10 },
      { name: 'HY spread', threshold: 'Building: below 300bp / Resolving: above 600bp', weight: 0.175 },
      { name: 'Top-10 concentration in S&P 500', threshold: 'Above 30%', weight: 0.20 },
      { name: 'Capex/revenue mismatch (AI)', threshold: 'Capex exceeding revenue by 3x+', weight: 0.15 },
      { name: 'Margin debt', threshold: 'At or within 10% of record highs', weight: 0.10 },
      { name: 'Passive fund share of equity AUM', threshold: 'Above 50%', weight: 0.10 },
    ],
    predictions: [
      { asset: 'SPY', direction: 'Vulnerable to sharp drawdown', magnitude: '-25% to -40%' },
      { asset: 'QQQ', direction: 'Underperform (concentration unwind)', magnitude: '-30% to -50%' },
      { asset: 'IWM', direction: 'Outperform in recovery', magnitude: 'Recovers faster than QQQ' },
      { asset: 'VIX', direction: 'Spike', magnitude: '35 to 80+' },
      { asset: 'SHY', direction: 'Safe haven', magnitude: '+2% to +5%' },
    ],
    hardFalsifiers: [
      'Market concentration declines organically below 25% without preceding drawdown',
      'Capex generates proportional revenue (revenue-to-capex >0.5x within 18 months)',
      'VIX sustained above 20 during rising market (volatility without fragility)',
      'Leverage declining despite rising prices',
    ],
    softFalsifiers: [
      { condition: 'Central bank backstop becomes explicit/formal', severity: 'major' },
      { condition: 'AI earnings delivering (revenue growing 25%+ YoY broadly)', severity: 'medium' },
      { condition: 'Market broadening underway (equal-weight outperforming)', severity: 'minor' },
      { condition: 'Short-term debt cycle in early expansion', severity: 'minor' },
    ],
  },

  fiscal_dominance_liquidity: {
    title: 'Fiscal Dominance -- Net Liquidity Transmission',
    summary:
      'Captures the mechanism where fiscal deficit spending injects reserves into the financial system faster than the Fed can drain them via QT. Net liquidity becomes the dominant driver of asset prices; monetary policy is subordinate. Rate hikes become paradoxically stimulative through interest expense expansion.',
    horizon: '1-6 months (tactical)',
    twoPhase: false,
    coreMechanism: [
      'Government runs large deficits, spending money into the private sector faster than taxes remove it.',
      'Treasury issuance drains reserves, but deficit spending adds them back -- net effect depends on TGA, RRP, and Fed balance sheet.',
      'When net liquidity expands, it flows into financial assets: equities, crypto, gold.',
      'Rate hikes paradoxically stimulate via interest expense: higher rates → more interest paid to bondholders → more income → more spending/investing.',
      'Monetary policy is subordinate to fiscal dominance: the Fed cannot tighten enough to offset the fiscal impulse without breaking something.',
    ],
    indicators: [
      { name: 'Net liquidity expanding', threshold: 'Positive for 2+ of last 3 months', weight: 0.20 },
      { name: 'Deficit pace', threshold: 'Above $1.5T annualized', weight: 0.20 },
      { name: 'Economy resisting tightening', threshold: 'Unemployment <5% AND ISM >45 after 12+ months of rates >4%', weight: 0.15 },
      { name: 'Hard assets outperforming', threshold: 'GLD/BTC outperforming TLT by 10%+', weight: 0.15 },
      { name: 'RRP draining', threshold: 'Below $250B', weight: 0.10 },
      { name: 'Fed balance sheet pace', threshold: 'QT slower than announced or flat/expanding', weight: 0.10 },
      { name: 'TGA drawdown', threshold: 'Below $500B or declining $100B+ over 60 days', weight: 0.10 },
    ],
    predictions: [
      { asset: 'GLD', direction: 'LONG', magnitude: '+10% to +25%/yr' },
      { asset: 'IBIT', direction: 'LONG (high vol)', magnitude: '+15% to +50%/yr with +/-30% drawdowns' },
      { asset: 'SPY', direction: 'Nominal gains, lags hard assets real', magnitude: '+5% to +15%/yr nominal' },
      { asset: 'TLT', direction: 'Underperform', magnitude: '-5% to -15% nominal or flat real' },
      { asset: 'TIP', direction: 'Outperform TLT', magnitude: '+5% to +15% relative' },
      { asset: 'DBC', direction: 'LONG', magnitude: '+5% to +15%/yr' },
    ],
    hardFalsifiers: [
      'Net liquidity contracts for 3+ months despite large deficit (>$1.5T)',
      'Rate hikes produce recession within 12 months despite deficit >$1.5T',
      'Genuine fiscal consolidation: deficit falls below $800B for 2+ consecutive quarters',
    ],
    softFalsifiers: [
      { condition: 'Net liquidity and asset prices decorrelate (3-month r < 0.30)', severity: 'major' },
      { condition: 'Dollar strengthens despite fiscal dominance conditions', severity: 'major' },
      { condition: 'QT pace accelerating beyond announced schedule', severity: 'medium' },
      { condition: 'Hard assets underperforming despite rising net liquidity', severity: 'medium' },
      { condition: 'RRP re-expanding above $500B', severity: 'minor' },
    ],
  },

  fiscal_dominance_arithmetic: {
    title: 'Fiscal Dominance -- Devaluation Arithmetic',
    summary:
      'Examines the cumulative debt trajectory and its arithmetic endpoint. When interest expense consumes >20% of tax receipts, the system faces three options: austerity (politically near-impossible), default (system-destroying), or devaluation (path of least resistance). Devaluation erodes purchasing power of nominal claims, making hard assets structurally preferable.',
    horizon: '3-10 years (structural)',
    twoPhase: false,
    coreMechanism: [
      'Federal debt grows faster than GDP. Each year the deficit adds to the stock of debt.',
      'Interest expense is now the function of both the stock of debt AND the average coupon rate as old low-rate debt rolls into higher rates.',
      'Interest expense exceeding defense spending (~$886B) and consuming >20% of tax receipts triggers the arithmetic trap.',
      'The only politically viable resolution is devaluation: inflation erodes the real value of the outstanding debt stock.',
      'Speed of devaluation is the open question: slow (2-4% sustained) or fast (6-10% spike).',
    ],
    indicators: [
      { name: 'Interest expense / tax receipts', threshold: 'Above 20%', weight: 0.25 },
      { name: 'Interest expense vs defense spending', threshold: 'Exceeds ~$886B', weight: 0.15 },
      { name: 'Deficit pace during full employment', threshold: '>$1.5T annualized with unemployment <5%', weight: 0.20 },
      { name: 'Credible deficit reduction plan', threshold: 'None exists', weight: 0.10 },
      { name: 'Debt rollover at higher rates', threshold: 'Average coupon rising as old debt matures', weight: 0.15 },
      { name: 'Gold/oil ratio', threshold: 'Above 25', weight: 0.10 },
      { name: 'Central bank gold purchases', threshold: '>800 tonnes/yr for 2+ years', weight: 0.05 },
    ],
    predictions: [
      { asset: 'GLD', direction: 'Structural LONG', magnitude: 'Maintains/increases real value' },
      { asset: 'TLT', direction: 'Negative real returns', magnitude: 'Nominal coupon < inflation' },
      { asset: 'TIP', direction: 'Outperform nominal bonds', magnitude: 'Inflation protection accrues' },
      { asset: 'SPY', direction: 'Nominal positive, real poor', magnitude: 'Lags inflation over decade' },
      { asset: 'DBC', direction: 'LONG', magnitude: 'Real assets preserve purchasing power' },
    ],
    hardFalsifiers: [
      'Genuine fiscal consolidation: deficit below 2% of GDP for 3+ years',
      'Interest expense declines as share of revenue for 2+ years without rate manipulation',
      'Productivity miracle: GDP growth exceeds 4% real for 5+ years, growing out of the debt',
    ],
    softFalsifiers: [
      { condition: 'Reserve currency privilege allows indefinite deficit financing at low rates', severity: 'major' },
      { condition: 'AI-driven productivity permanently raises GDP growth above interest cost', severity: 'medium' },
      { condition: 'Political will produces bipartisan deficit reduction (unlikely but possible)', severity: 'medium' },
      { condition: 'Immigration-driven demographic tailwind supports tax base', severity: 'minor' },
    ],
  },

  capital_flows: {
    title: 'Capital Flow Dynamics & Multipolar Rebalancing',
    summary:
      'Identifies when extreme EM-DM valuation gaps (EM 40%+ cheaper) combined with catalysts (dollar weakness, positive China credit impulse, RMB strengthening) trigger capital rotation from developed to emerging markets. The rotation cycle runs 2-5 years once catalysts fire.',
    horizon: '2-5 years (rotation cycle)',
    twoPhase: true,
    phases: ['Accumulation', 'Rotation'],
    coreMechanism: [
      'Valuation gap builds over years: US outperformance inflates US multiples while EM stagnates.',
      'Catalyst arrives: dollar weakens, easing EM financial conditions (cheaper debt service, better terms of trade).',
      'China credit impulse transmits globally with 6-18 month lag: credit → PMI → commodities → earnings → flows.',
      'Reflexive loop activates: flows strengthen EM currencies → eases conditions further → attracts more flows.',
      'Regional sequencing: China first → broad EM → India → Europe → Japan.',
    ],
    indicators: [
      { name: 'EM vs DM PE gap', threshold: 'Accumulation: exceeding 40% discount', weight: 0.25 },
      { name: 'EM 3-year underperformance', threshold: 'Accumulation: >30% vs DM', weight: 0.20 },
      { name: 'Dollar direction (DXY)', threshold: 'Accumulation: >100 / Rotation: declining 3+ months', weight: 0.20 },
      { name: 'China credit impulse', threshold: 'Accumulation: flat/negative / Rotation: positive, accelerating', weight: 0.175 },
      { name: 'RMB direction', threshold: 'Rotation: USD/CNY declining 3+ months', weight: 0.20 },
      { name: 'EM outperforming DM', threshold: 'Rotation: 3+ consecutive months', weight: 0.15 },
    ],
    predictions: [
      { asset: 'FXI', direction: 'LONG (Rotation lead)', magnitude: '+30% to +50% year 1' },
      { asset: 'KWEB', direction: 'LONG (high beta)', magnitude: '+40% to +70% year 1' },
      { asset: 'EEM', direction: 'LONG (broad rally)', magnitude: '+20% to +30% year 1' },
      { asset: 'INDA', direction: 'LONG (independent cycle)', magnitude: '+15% to +25%' },
      { asset: 'DBC', direction: 'LONG (commodity demand)', magnitude: '+15% to +30%' },
      { asset: 'SPY/QQQ', direction: 'Relative underperform', magnitude: '+5% to +10% but EM +20-30%' },
    ],
    hardFalsifiers: [
      'EM PE discount persists 5+ years without rotation despite catalysts firing',
      'China becomes uninvestable (Taiwan conflict, sanctions, capital controls)',
      'Dollar strengthens for 10+ years while all rotation conditions are present',
    ],
    softFalsifiers: [
      { condition: 'China balance sheet recession deepens (housing starts -15% YoY)', severity: 'medium' },
      { condition: 'Trade war/tariffs escalate (>40% tariff, China PMI <49)', severity: 'medium' },
      { condition: 'US productivity miracle makes PE premium justified', severity: 'medium' },
      { condition: 'EM governance failures (capital controls in >5% of EEM)', severity: 'medium' },
      { condition: 'Dollar weakens but EM does not outperform for 2+ months', severity: 'minor' },
    ],
  },

  monetary_architecture: {
    title: 'Monetary Architecture & Collateral Regime Transition',
    summary:
      'Tracks the structural transition in global monetary collateral from US Treasuries to gold. The 2022 Russia sanctions demonstrated that sovereign reserves carry counterparty risk. Central banks are diversifying reserves away from Treasuries toward gold at an accelerating pace, creating a structural bid independent of cycles.',
    horizon: 'Multi-decade (structural transition)',
    twoPhase: false,
    coreMechanism: [
      'Post-1971, US Treasuries became the foundational collateral asset of the global monetary system.',
      'The 2022 Russia sanctions demonstrated that Treasury holdings carry political counterparty risk -- reserves can be frozen.',
      'Central banks respond by accumulating gold: 800+ tonnes/year purchased since 2022, well above historical norms.',
      'Foreign official Treasury holdings decline as percentage of outstanding debt, even as total debt grows.',
      'This is not a speculative move but a structural reallocation of sovereign reserves -- slow, persistent, and difficult to reverse.',
    ],
    indicators: [
      { name: 'Central bank gold purchases', threshold: '>800 tonnes/yr for 2+ years', weight: 0.25 },
      { name: 'Foreign official Treasury holdings declining', threshold: 'Declining as % of outstanding for 3+ years', weight: 0.20 },
      { name: 'Gold/oil ratio', threshold: 'Above 25 and rising on 12-month basis', weight: 0.15 },
      { name: 'Non-dollar trade settlement growing', threshold: 'RMB >4% of SWIFT or bilateral agreements expanding', weight: 0.15 },
      { name: 'Sanctions weaponization', threshold: 'Continuing or expanding beyond Russia', weight: 0.10 },
      { name: 'Cross-currency basis stress', threshold: 'Episodic spikes to -50bp+', weight: 0.10 },
      { name: 'Institutional adoption of thesis', threshold: 'Pozsar/Gromen framework gaining mainstream traction', weight: 0.05 },
    ],
    predictions: [
      { asset: 'GLD', direction: 'Structural LONG', magnitude: 'Appreciates as CB reallocation continues' },
      { asset: 'GDX', direction: 'LONG (leveraged gold)', magnitude: 'Gold miners benefit from sustained high prices' },
      { asset: 'TLT', direction: 'Structural headwind', magnitude: 'Declining demand from official sector' },
      { asset: 'UUP', direction: 'Gradual erosion', magnitude: 'Dollar reserve status erodes at margin' },
    ],
    hardFalsifiers: [
      'Central bank gold purchases fall below 400 tonnes/yr for 2+ years (return to pre-2022 norms)',
      'Foreign official Treasury holdings increase as % of outstanding for 3+ years',
      'Sanctions regime reversed or credibly constrained by treaty/legislation',
    ],
    softFalsifiers: [
      { condition: 'Gold price declines 20%+ without CB purchase slowdown (speculative unwind)', severity: 'major' },
      { condition: 'Dollar strengthens structurally despite reserve diversification', severity: 'medium' },
      { condition: 'Alternative digital settlement systems fail to gain traction', severity: 'minor' },
      { condition: 'US fiscal consolidation restores Treasury creditworthiness', severity: 'medium' },
    ],
  },
}

export function getTheoryDescription(theoryId) {
  return theories[theoryId] || null
}

export function getAllTheoryDescriptions() {
  return theories
}
