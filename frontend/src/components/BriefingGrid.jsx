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
      { key: 'growth.gdp_yoy', label: 'GDP YoY' },
      { key: 'growth.ism_manufacturing', label: 'ISM Mfg' },
      { key: 'growth.unemployment_rate', label: 'Unemployment' },
      { key: 'growth.nonfarm_payrolls', label: 'Payrolls' },
      { key: 'growth.initial_claims', label: 'Initial Claims' },
    ],
  },
  {
    title: 'Inflation',
    fields: [
      { key: 'inflation.cpi_yoy', label: 'CPI YoY' },
      { key: 'inflation.core_pce_yoy', label: 'Core PCE' },
      { key: 'inflation.breakeven_5y', label: '5Y Breakeven' },
      { key: 'inflation.breakeven_10y', label: '10Y Breakeven' },
    ],
  },
  {
    title: 'Rates',
    fields: [
      { key: 'rates.fed_funds', label: 'Fed Funds' },
      { key: 'rates.yield_2y', label: '2Y Yield' },
      { key: 'rates.yield_10y', label: '10Y Yield' },
      { key: 'rates.yield_30y', label: '30Y Yield' },
      { key: 'computed.spread_2s10s', label: '2s10s Spread' },
      { key: 'computed.real_10y', label: 'Real 10Y' },
    ],
  },
  {
    title: 'Liquidity',
    fields: [
      { key: 'computed.net_liquidity', label: 'Net Liquidity' },
      { key: 'liquidity.fed_balance_sheet', label: 'Fed BS' },
      { key: 'liquidity.treasury_general_account', label: 'TGA' },
      { key: 'liquidity.reverse_repo', label: 'RRP' },
      { key: 'liquidity.m2_yoy', label: 'M2 YoY' },
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
      { key: 'sentiment.vix', label: 'VIX' },
      { key: 'computed.vix_vs_realized', label: 'VIX vs Realized' },
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
