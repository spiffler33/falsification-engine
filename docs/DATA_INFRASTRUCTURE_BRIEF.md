# DATA_INFRASTRUCTURE_BRIEF.md
# Context document for the Data Agent / ETF Universe / Web Search thread
# Add this to the new chat thread's project folder alongside plan_v3.md

---

## What This Thread Is About

The Macro Council v3 architecture is designed (see plan_v3.md). The economics, hypothesis pipeline, agent prompts, and frontend are being built by Claude Code from plan_v3.md + economic_theories.md + BUILD_INSTRUCTIONS.md.

This thread focuses on the DATA LAYER that feeds the system:

1. **ETF Universe Expansion** -- What is the complete set of liquid, IBKR-available ETFs for expressing global macro views? The current list in plan_v3.md was assembled ad hoc. We need a systematic, researched universe.

2. **Data Agent Architecture** -- The data agent fetches FRED + Yahoo data and computes derived metrics. Is this sufficient? What are we missing? Should we add more sources?

3. **Web Search Intelligence Layer** -- Currently each agent does its own web searches (overlapping, uncoordinated). Should there be a dedicated "intelligence gathering" pass that runs BEFORE the theory agents, producing a current events briefing that all agents receive?

4. **IBKR Integration** -- Can we connect to IBKR for real-time portfolio data, available instrument lists, or execution readiness? What's available via their API for free?

---

## Current State (what plan_v3.md specifies)

### Data Sources
- **FRED API** (free key): ~22 macro series (GDP, CPI, rates, yields, liquidity, credit spreads, etc.)
- **Yahoo Finance** (yfinance, free): ETF prices and returns, VIX, FX pairs

### ETF Universe (current -- needs expansion)
```
US Equity:     SPY, QQQ, IWM, DIA, RSP, MDY
International: EFA, EEM, FXI, KWEB, EWJ, EWZ, INDA, VGK, EWG, EWU, EWA, EWT, EWY, EIDO, THD, VWO
Bonds:         TLT, IEF, SHY, HYG, LQD, TIP, EMB, AGG, BND, BNDX, BWX, GOVT, STIP, VTIP
Commodities:   GLD, SLV, DBC, USO, UNG, PDBC, COPX, PPLT, WEAT, CORN, DBA
Sectors:       XLE, XLF, XLK, XLV, XLI, XLP, XLU, XLRE, XLB, XLC, XLY, SMH, XBI, KBE, KRE, XOP, OIH, ITB, XHB, JETS, XME
Currency/Alt:  UUP, FXE, FXY, FXB, IBIT, BITO
REITs:         VNQ, VNQI, IYR, REM
Volatility:    ^VIX
FX Pairs:      CNYUSD=X, DX-Y.NYB, EURUSD=X, JPYUSD=X
```

### Computed Metrics (pre-calculated in briefing packet)
- equity_risk_premium (SPY earnings yield - 10Y yield)
- net_liquidity (Fed BS - TGA - RRP) + 30d change
- gold_oil_ratio (GLD/USO proxy)
- em_us_relative (EEM return - SPY return, 3M and 12M)
- qqq_iwm_ratio (concentration proxy)
- vix_vs_realized (VIX - 20d realized vol)
- yield curves (2s10s, 3m10y)
- real_10y (10Y - breakeven 10Y)
- hard_vs_nominal_12m (avg hard asset returns - avg nominal bond returns)

### What Each Agent Needs from Data

| Agent | Primary Data Needs | Currently Covered? | Gaps |
|-------|-------------------|-------------------|------|
| Buffett | Valuations (CAPE, Buffett Indicator, sector PEs), credit spreads, yields, cash yield | Partially -- CAPE and Buffett Indicator come from web search, not data agent | Sector-level PE/PB ratios, earnings data |
| Dalio | Full macro suite (growth, inflation, rates, liquidity, credit), historical ranges | Mostly covered by FRED + Yahoo | Historical percentile context for cycle positioning |
| Burry | Credit metrics, concentration data, leverage data, VIX/vol, capex/revenue | Credit from FRED, VIX from Yahoo, rest from web search | Margin debt, concentration stats, private credit size |
| Fiscal | Deficit pace, interest expense, net liquidity, Fed BS, hard asset returns | Liquidity from FRED, returns from Yahoo, fiscal data from web search | Monthly deficit figures, interest expense current |
| Gave | RMB, DXY, China PMI, EM/DM relative valuations, capital flow data | FX from Yahoo, rest from web search | China-specific data largely web-search dependent |
| Pozsar | Fed BS, TGA, RRP, term premium, CB gold purchases, SWIFT data | Liquidity from FRED, term premium from FRED, rest from web search | Most Pozsar-specific data is web-search dependent |

---

## Questions to Research in This Thread

### 1. ETF Universe
- What is the FULL set of liquid ETFs on IBKR for expressing macro views?
- Specifically: are there better/more liquid options for EM country exposure, commodity sub-sectors, currency hedging, volatility strategies, credit (long and short), real assets?
- What are the minimum liquidity thresholds (AUM, daily volume, bid-ask spread) for our ~$1.5M AUM?
- Are there inverse ETFs worth including for expressing bearish views without shorting?
- Are there leveraged ETFs that make sense for any tactical use (acknowledging decay)?

### 2. Data Sources Beyond FRED + Yahoo
- Are there free APIs for: sector-level valuations, earnings data, margin debt, fund flows, China PMI, central bank gold purchases?
- MacroMicro.me -- can we scrape or API for computed macro indicators?
- Is there a free source for Treasury auction data (bid-to-cover, foreign participation)?
- IBKR API -- what market data is available for free to account holders?

### 3. Web Search Intelligence Layer
- Should there be a single "intelligence gathering" prompt that runs BEFORE all agents?
- This prompt would search for: major macro events this week, Fed/ECB/BOJ/PBOC actions, earnings season status, geopolitical developments, market structure changes
- Output: a "current events briefing" (structured text) that gets appended to the data briefing for all agents
- Benefit: no duplicate searches, consistent current events context across agents
- Or: is it better to let each agent search independently (different agents care about different news)?

### 4. IBKR Integration
- IBKR API capabilities for account holders: real-time quotes, portfolio positions, available instruments, historical data?
- Is it worth connecting for: auto-populating the ETF universe with what's actually available, pulling current portfolio for position tracking, getting real-time prices for the briefing packet?
- Or is Yahoo Finance sufficient for the briefing packet and IBKR stays as execution-only?

---

## User Context

- ~$1.5M AUM, personal capital, not a fund
- IBKR for execution
- ~1 month holding periods
- Liquid ETFs only (no individual stocks, no options in the system)
- Bloomberg access at work (Deutsche Bank) but this system runs independently at home
- Currently uses: 42 Macro, Lyn Alden newsletter, FT, MacroMicro, Feedly Pro
- Existing data subscriptions that might be leverageable for the data agent
