// freshness.js — Client-side freshness label computation from realization primitives.
// Mirrors backend/realization.py policy layer.
// Backend stores facts (expression_return, realization ratios, time_elapsed_pct),
// frontend computes derived values (freshness label, realization cap).

// [CALIBRATION] — must match backend/realization.py TIME_THRESHOLD
const TIME_THRESHOLD = 0.50

// [CALIBRATION] — must match backend/realization.py REALIZATION_CAPS
const REALIZATION_CAPS = {
  FRESH:            null,
  WORKING:          null,
  ACCELERATING:     null,
  UNDERPERFORMING:  null,
  MATURE:           7.0,
  EXPRESSED:        5.0,
  INDETERMINATE:    null,
}

/**
 * Compute freshness label from realization primitives.
 *
 * Two axes:
 *   Magnitude: R < L (below lower) | L <= R < U (within band) | R >= U (above upper)
 *   Time:      early (< TIME_THRESHOLD) | late (>= TIME_THRESHOLD)
 *
 * Returns one of: FRESH, WORKING, ACCELERATING, UNDERPERFORMING, MATURE, EXPRESSED, INDETERMINATE
 */
export function computeFreshnessLabel(realization_vs_lower, realization_vs_upper, time_elapsed_pct) {
  if (realization_vs_lower == null || realization_vs_upper == null) {
    return 'INDETERMINATE'
  }

  const late = time_elapsed_pct >= TIME_THRESHOLD

  if (realization_vs_upper >= 1.0) {
    return late ? 'EXPRESSED' : 'ACCELERATING'
  } else if (realization_vs_lower >= 1.0) {
    return late ? 'MATURE' : 'WORKING'
  } else {
    return late ? 'UNDERPERFORMING' : 'FRESH'
  }
}

/**
 * Return the conviction cap for a freshness label, or null if no cap applies.
 */
export function getRealizationCap(freshnessLabel) {
  return REALIZATION_CAPS[freshnessLabel] ?? null
}

/**
 * CSS class suffix for each freshness label.
 */
export const FRESHNESS_CLASS = {
  FRESH:            'freshness--fresh',
  WORKING:          'freshness--working',
  ACCELERATING:     'freshness--accelerating',
  UNDERPERFORMING:  'freshness--underperforming',
  MATURE:           'freshness--mature',
  EXPRESSED:        'freshness--expressed',
  INDETERMINATE:    'freshness--indeterminate',
}

/**
 * Human-readable action hint per freshness label (from plan_v6.md action model).
 */
export const FRESHNESS_ACTION = {
  FRESH:            'Evaluate for new entry',
  WORKING:          'Hold, monitor',
  ACCELERATING:     'Review: best trade or crowded overshoot?',
  UNDERPERFORMING:  'Review: thesis wrong, expression wrong, or timing wrong?',
  MATURE:           'Tighten risk, consider partial exit',
  EXPRESSED:        'No new entry, exit existing position',
  INDETERMINATE:    'Legacy hypothesis -- no payoff band data',
}
