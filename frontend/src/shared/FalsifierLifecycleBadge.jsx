/**
 * FalsifierLifecycleBadge -- displays lifecycle status for individual falsifiers.
 * Statuses: CLEAR, TRIGGERED, UNTESTABLE, STALE, ESCALATED_UNTESTABLE
 * JetBrains Mono 9px, colored by severity/status.
 */

const STATUS_CLASS = {
  CLEAR: 'falsifier-lifecycle--clear',
  TRIGGERED: 'falsifier-lifecycle--triggered',
  UNTESTABLE: 'falsifier-lifecycle--untestable',
  STALE: 'falsifier-lifecycle--stale',
  ESCALATED_UNTESTABLE: 'falsifier-lifecycle--escalated',
  TRIGGERED_BY_PASSAGE: 'falsifier-lifecycle--triggered',
}

const STATUS_LABEL = {
  CLEAR: 'CLEAR',
  TRIGGERED: 'TRIGGERED',
  UNTESTABLE: 'UNTESTABLE',
  STALE: 'STALE',
  ESCALATED_UNTESTABLE: 'ESCALATED',
  TRIGGERED_BY_PASSAGE: 'PASSAGE',
}

export default function FalsifierLifecycleBadge({ status, consecutiveCount }) {
  if (!status) return null

  const cls = `falsifier-lifecycle ${STATUS_CLASS[status] || ''}`
  const label = STATUS_LABEL[status] || status

  return (
    <span className={cls}>
      {label}
      {status === 'UNTESTABLE' && consecutiveCount > 0 && (
        <span className="falsifier-lifecycle__counter">x{consecutiveCount}</span>
      )}
      {status === 'ESCALATED_UNTESTABLE' && consecutiveCount > 0 && (
        <span className="falsifier-lifecycle__counter">x{consecutiveCount}</span>
      )}
    </span>
  )
}
