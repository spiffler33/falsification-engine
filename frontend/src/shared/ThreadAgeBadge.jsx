/**
 * ThreadAgeBadge -- displays thread age as "3d" or "12d".
 * JetBrains Mono 9px, subtle background.
 * Long-lived threads (>14d) get distinct styling.
 */
export default function ThreadAgeBadge({ days, confirmationCount }) {
  if (days == null) return null

  const label = `${days}d`
  const cls = days >= 14 ? 'thread-age-badge thread-age-badge--mature' : 'thread-age-badge'

  return (
    <span className={cls} title={`Thread age: ${days} days, ${confirmationCount || 0} confirmations`}>
      {label}
      {confirmationCount > 0 && (
        <span className="thread-age-badge__confirms">x{confirmationCount}</span>
      )}
    </span>
  )
}
