import { computeFreshnessLabel, FRESHNESS_CLASS } from '../lib/freshness'

/**
 * FreshnessBadge — small colored label showing realization state.
 *
 * Follows the StatusBadge pattern: font-data, 9px, uppercase, bordered, no rounded corners.
 *
 * Props:
 *   realization_vs_lower, realization_vs_upper, time_elapsed_pct — primitives for client-side computation
 *   OR
 *   label — pre-computed freshness label (e.g., from conviction_math.stage3.freshness_label)
 *
 * Returns null for INDETERMINATE (legacy hypotheses without payoff bands).
 */
export default function FreshnessBadge({ realization_vs_lower, realization_vs_upper, time_elapsed_pct, label }) {
  const freshnessLabel = label || computeFreshnessLabel(realization_vs_lower, realization_vs_upper, time_elapsed_pct)

  if (freshnessLabel === 'INDETERMINATE' || !freshnessLabel) return null

  const cls = FRESHNESS_CLASS[freshnessLabel] || ''

  return (
    <span className={`freshness-badge ${cls}`} title={freshnessLabel}>
      {freshnessLabel}
    </span>
  )
}
