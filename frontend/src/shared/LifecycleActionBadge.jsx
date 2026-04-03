/**
 * LifecycleActionBadge -- displays CONFIRM / UPDATE / RENEW / RETIRE / NEW.
 * JetBrains Mono 9px, colored by action type.
 */

const ACTION_CLASS = {
  CONFIRM: 'lifecycle-badge--confirm',
  UPDATE: 'lifecycle-badge--update',
  RENEW: 'lifecycle-badge--renew',
  RETIRE: 'lifecycle-badge--retire',
  NEW: 'lifecycle-badge--new',
}

export default function LifecycleActionBadge({ action }) {
  if (!action) return null

  const cls = `lifecycle-badge ${ACTION_CLASS[action] || ''}`
  return <span className={cls}>{action}</span>
}
