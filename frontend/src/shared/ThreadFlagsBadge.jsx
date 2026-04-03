/**
 * ThreadFlagsBadge -- displays STALE count, ESCALATED count, emergent risk indicator.
 * JetBrains Mono 9px, warning-colored. Shows nothing if no flags active.
 */
export default function ThreadFlagsBadge({ staleCount, escalatedCount, hasEmergentRisk }) {
  const flags = []

  if (staleCount > 0) {
    flags.push(
      <span key="stale" className="thread-flag thread-flag--stale" title={`${staleCount} STALE falsifier${staleCount > 1 ? 's' : ''}`}>
        S:{staleCount}
      </span>
    )
  }

  if (escalatedCount > 0) {
    flags.push(
      <span key="esc" className="thread-flag thread-flag--escalated" title={`${escalatedCount} ESCALATED_UNTESTABLE falsifier${escalatedCount > 1 ? 's' : ''}`}>
        E:{escalatedCount}
      </span>
    )
  }

  if (hasEmergentRisk) {
    flags.push(
      <span key="emr" className="thread-flag thread-flag--emergent" title="Emergent risk identified">
        EMR
      </span>
    )
  }

  if (flags.length === 0) return null

  return <span className="thread-flags">{flags}</span>
}
