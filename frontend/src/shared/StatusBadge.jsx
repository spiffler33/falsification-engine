/**
 * StatusBadge — displays SURVIVED / WOUNDED / KILLED.
 * JetBrains Mono 9px, colored border by status.
 */
export default function StatusBadge({ status }) {
  const cls = `status-badge status-badge--${(status || '').toLowerCase()}`
  return <span className={cls}>{status}</span>
}
