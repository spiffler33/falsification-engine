/**
 * OutcomeBadge — displays hypothesis outcome status.
 * Symbols: CORRECT (checkmark), INCORRECT (X), PARTIAL (circle), EXPIRED (dash).
 * Colors match Hermes Editorial accent palette.
 */
const OUTCOME_CONFIG = {
  CORRECT:   { symbol: 'V',  label: 'CORRECT',   className: 'outcome-badge--correct' },
  INCORRECT: { symbol: 'X',  label: 'INCORRECT',  className: 'outcome-badge--incorrect' },
  PARTIAL:   { symbol: 'o',  label: 'PARTIAL',    className: 'outcome-badge--partial' },
  EXPIRED:   { symbol: '--', label: 'EXPIRED',    className: 'outcome-badge--expired' },
}

export default function OutcomeBadge({ status, size = 'small' }) {
  if (!status) return null
  const config = OUTCOME_CONFIG[status.toUpperCase()]
  if (!config) return null

  return (
    <span className={`outcome-badge ${config.className} outcome-badge--${size}`}>
      <span className="outcome-badge__symbol">{config.symbol}</span>
      {size === 'large' && <span className="outcome-badge__label">{config.label}</span>}
    </span>
  )
}
