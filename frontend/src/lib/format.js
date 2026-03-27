// Formatting utilities for the Falsification Engine frontend.

/**
 * Format a conviction score for display (e.g., "7.8").
 */
export function fmtConviction(score) {
  if (score == null) return '--'
  return Number(score).toFixed(1)
}

/**
 * Format a conviction delta (e.g., "+0.6", "-1.2").
 */
export function fmtDelta(current, prev) {
  if (current == null || prev == null) return ''
  const d = current - prev
  if (Math.abs(d) < 0.05) return ''
  const sign = d > 0 ? '+' : ''
  return `${sign}${d.toFixed(1)}`
}

/**
 * Get CSS class for conviction score tier.
 */
export function convictionTier(score) {
  if (score == null) return 'conviction-score--low'
  if (score >= 7) return 'conviction-score--high'
  if (score >= 5) return 'conviction-score--mid'
  return 'conviction-score--low'
}

/**
 * Get CSS class for conviction delta direction.
 */
export function deltaTier(current, prev) {
  if (current == null || prev == null) return 'conviction-delta--neutral'
  const d = current - prev
  if (d > 0.05) return 'conviction-delta--positive'
  if (d < -0.05) return 'conviction-delta--negative'
  return 'conviction-delta--neutral'
}

/**
 * Format age in days (e.g., "12d").
 */
export function fmtAge(days) {
  if (days == null) return '--'
  return `${days}d`
}

/**
 * Format a date string to short display (e.g., "2026-03-18").
 */
export function fmtDate(isoDate) {
  if (!isoDate) return '--'
  return isoDate.slice(0, 10)
}

/**
 * Shorten theory_id for display as a tag.
 * e.g., "fiscal_dominance_liquidity" -> "fisc_dom_liq"
 */
const THEORY_SHORT = {
  valuation_mean_reversion: 'val_mean_rev',
  debt_cycle_short: 'debt_short',
  debt_cycle_long: 'debt_long',
  structural_fragility: 'struct_frag',
  fiscal_dominance_liquidity: 'fisc_dom_liq',
  fiscal_dominance_arithmetic: 'fisc_dom_arith',
  capital_flows: 'cap_flows',
  monetary_architecture: 'mon_arch',
}

export function shortTheory(theoryId) {
  return THEORY_SHORT[theoryId] || theoryId
}
