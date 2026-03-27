/**
 * JournalEntry — a single journal entry card.
 * Shows action, linked hypothesis, conviction at entry vs current, status.
 * Hypothesis name is clickable to open detail.
 */
import { fmtConviction, fmtDate } from '../lib/format'

export default function JournalEntry({ entry, onHypothesisClick, onClose }) {
  const statusClass = entry.status === 'OPEN'
    ? 'journal-entry__status--open'
    : 'journal-entry__status--closed'

  return (
    <div className="journal-entry">
      <div className="journal-entry__header">
        <span className="journal-entry__action">{entry.action}</span>
        <span className="journal-entry__date">{fmtDate(entry.date)}</span>
      </div>

      {entry.hypothesis_name && (
        <div
          className="journal-entry__hypothesis"
          onClick={() => onHypothesisClick && onHypothesisClick(entry.hypothesis_id)}
        >
          {entry.hypothesis_name}
        </div>
      )}

      <div className="journal-entry__meta">
        {entry.size && (
          <span className="journal-entry__field">
            <span className="journal-entry__field-label">Size: </span>
            {entry.size}
          </span>
        )}
        <span className="journal-entry__field">
          <span className="journal-entry__field-label">Entry conv: </span>
          {fmtConviction(entry.conviction_at_entry)}
        </span>
        {entry.conviction_current != null && (
          <span className="journal-entry__field">
            <span className="journal-entry__field-label">Current: </span>
            {fmtConviction(entry.conviction_current)}
          </span>
        )}
        <span className={`journal-entry__status ${statusClass}`}>
          {entry.status}
        </span>
      </div>

      {entry.reasoning && (
        <div className="journal-entry__reasoning">{entry.reasoning}</div>
      )}

      {entry.outcome && (
        <div className="journal-entry__outcome">
          <span className="journal-entry__outcome-label">Outcome: </span>
          {entry.outcome}
        </div>
      )}

      {entry.status === 'OPEN' && onClose && (
        <button className="btn journal-entry__close-btn" onClick={() => onClose(entry)}>
          CLOSE POSITION
        </button>
      )}
    </div>
  )
}
