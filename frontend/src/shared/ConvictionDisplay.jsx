import { fmtConviction, fmtDelta, convictionTier, deltaTier } from '../lib/format'

/**
 * ConvictionDisplay — score + delta, right-aligned.
 * Score: JetBrains Mono 14px/600, colored by tier.
 * Delta: JetBrains Mono 10px, colored by direction.
 */
export default function ConvictionDisplay({ conviction, convictionPrev }) {
  const delta = fmtDelta(conviction, convictionPrev)

  return (
    <div className="conviction-display">
      <div className={`conviction-score ${convictionTier(conviction)}`}>
        {fmtConviction(conviction)}
      </div>
      {delta && (
        <div className={`conviction-delta ${deltaTier(conviction, convictionPrev)}`}>
          {delta}
        </div>
      )}
    </div>
  )
}
