/**
 * BriefingGrid — renders the structured briefing packet as a 6-panel grid.
 * Panels: Growth, Inflation, Rates, Liquidity, Credit, Sentiment.
 * Each field shows name, current value, direction/trend tag.
 * Stale fields (>24h) shown with gold warning.
 */

const PANELS = [
  {
    title: 'Growth',
    fields: [
      { key: 'growth.real_gdp', label: 'Real GDP' },
      { key: 'growth.ism_proxy', label: 'ISM Mfg' },
      { key: 'growth.unemployment', label: 'Unemployment' },
      { key: 'growth.nonfarm_payrolls', label: 'Payrolls' },
      { key: 'growth.initial_claims', label: 'Initial Claims' },
    ],
  },
  {
    title: 'Inflation',
    fields: [
      { key: 'inflation.cpi_yoy', label: 'CPI YoY' },
      { key: 'inflation.core_pce', label: 'Core PCE' },
      { key: 'inflation.breakeven_5y', label: '5Y Breakeven' },
      { key: 'inflation.breakeven_10y', label: '10Y Breakeven' },
    ],
  },
  {
    title: 'Rates',
    fields: [
      { key: 'rates.fed_funds', label: 'Fed Funds' },
      { key: 'rates.treasury_2y', label: '2Y Yield' },
      { key: 'rates.treasury_10y', label: '10Y Yield' },
      { key: 'rates.treasury_30y', label: '30Y Yield' },
      { key: 'rates.curve_2s10s', label: '2s10s Spread' },
      { key: 'computed.real_10y', label: 'Real 10Y' },
    ],
  },
  {
    title: 'Liquidity',
    fields: [
      { key: 'computed.net_liquidity', label: 'Net Liquidity' },
      { key: 'liquidity.fed_balance_sheet', label: 'Fed BS' },
      { key: 'liquidity.tga', label: 'TGA' },
      { key: 'liquidity.reverse_repo', label: 'RRP' },
      { key: 'liquidity.m2', label: 'M2' },
    ],
  },
  {
    title: 'Credit',
    fields: [
      { key: 'credit.hy_spread', label: 'HY Spread' },
      { key: 'credit.ig_spread', label: 'IG Spread' },
    ],
  },
  {
    title: 'Sentiment',
    fields: [
      { key: 'markets.^VIX.price', label: 'VIX' },
      { key: 'computed.vix_vs_realized', label: 'VIX vs Realized' },
      { key: 'computed.spy_drawdown_from_52w_high', label: 'SPY Drawdown' },
      { key: 'computed.qqq_iwm_ratio', label: 'QQQ/IWM Ratio' },
    ],
  },
]

function resolveField(data, path) {
  if (!data || !path) return null
  const parts = path.split('.')
  let val = data
  for (const p of parts) {
    if (val == null) return null
    val = val[p]
  }
  return val
}

function formatValue(val) {
  if (val == null) return '--'
  if (typeof val === 'number') {
    if (Math.abs(val) >= 1000) return val.toLocaleString(undefined, { maximumFractionDigits: 1 })
    if (Math.abs(val) < 0.1) return val.toFixed(4)
    return val.toFixed(2)
  }
  return String(val)
}

export default function BriefingGrid({ briefing }) {
  if (!briefing) {
    return <div className="empty-state">No briefing data available.</div>
  }

  const data = briefing.data || briefing

  return (
    <div className="briefing-grid">
      {PANELS.map(panel => (
        <div key={panel.title} className="briefing-panel">
          <div className="briefing-panel__title">{panel.title}</div>
          <div className="briefing-panel__fields">
            {panel.fields.map(f => {
              const val = resolveField(data, f.key)
              return (
                <div key={f.key} className="briefing-field">
                  <span className="briefing-field__label">{f.label}</span>
                  <span className="briefing-field__value">{formatValue(val)}</span>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
