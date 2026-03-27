/**
 * FalsifierCompact — "1/3" or "0/4" display.
 * Green if 0 triggered, gold if >0.
 */
export default function FalsifierCompact({ triggered, total }) {
  if (triggered == null || total == null) return <span className="falsifier-compact">--</span>
  const cls = triggered > 0 ? 'falsifier-compact--warning' : 'falsifier-compact--healthy'
  return (
    <span className={`falsifier-compact ${cls}`}>
      {triggered}/{total}
    </span>
  )
}
