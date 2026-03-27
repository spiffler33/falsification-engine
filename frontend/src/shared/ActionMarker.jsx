/**
 * ActionMarker — dot for position, diamond for research notes.
 * SVG shapes, 8px, centered in column.
 */
export default function ActionMarker({ hasAction, hasNotes }) {
  if (!hasAction && !hasNotes) return null

  return (
    <span className="action-markers">
      {hasAction && (
        <svg width="8" height="8" viewBox="0 0 8 8">
          <circle cx="4" cy="4" r="3.5" fill="var(--accent-high)" />
        </svg>
      )}
      {hasNotes && (
        <svg width="8" height="8" viewBox="0 0 8 8">
          <rect x="1" y="1" width="6" height="6" fill="var(--text-tertiary)"
            transform="rotate(45 4 4)" />
        </svg>
      )}
    </span>
  )
}
