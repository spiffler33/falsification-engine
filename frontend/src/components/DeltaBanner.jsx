import { api } from '../lib/api'

/**
 * DeltaBanner — shows changes since last review.
 * Categories: KILLED, DETERIORATED, IMPROVED, NEW, STABLE (hidden).
 * Each item clickable -> opens hypothesis detail.
 * "MARK REVIEWED" dismisses the banner.
 */
export default function DeltaBanner({ delta, onSelectHypothesis, onMarkReviewed }) {
  if (!delta) return null

  const { killed, deteriorated, improved, new_hypotheses } = delta
  const hasChanges = killed.length + deteriorated.length + improved.length + new_hypotheses.length > 0

  if (!hasChanges) return null

  return (
    <div className="delta-banner">
      <div className="delta-banner__header">
        <span className="delta-banner__title">Changes Since Last Review</span>
        <button className="btn btn--primary" onClick={onMarkReviewed}>
          MARK REVIEWED
        </button>
      </div>

      {killed.length > 0 && (
        <DeltaSection
          label="KILLED"
          labelClass="delta-banner__label--killed"
          items={killed}
          onSelect={onSelectHypothesis}
          renderItem={h => (
            <span className="delta-banner__item delta-banner__item--killed">
              {h.short_name} -- {h.elimination_notes?.slice(0, 60) || 'Hard falsifier triggered'}
            </span>
          )}
        />
      )}

      {deteriorated.length > 0 && (
        <DeltaSection
          label="DETERIORATED"
          labelClass="delta-banner__label--deteriorated"
          items={deteriorated}
          onSelect={onSelectHypothesis}
          renderItem={h => (
            <span className="delta-banner__item">
              {h.short_name} ({(h.conviction - h.conviction_prev).toFixed(1)})
            </span>
          )}
        />
      )}

      {improved.length > 0 && (
        <DeltaSection
          label="IMPROVED"
          labelClass="delta-banner__label--improved"
          items={improved}
          onSelect={onSelectHypothesis}
          renderItem={h => (
            <span className="delta-banner__item">
              {h.short_name} (+{(h.conviction - h.conviction_prev).toFixed(1)})
            </span>
          )}
        />
      )}

      {new_hypotheses.length > 0 && (
        <DeltaSection
          label="NEW"
          labelClass="delta-banner__label--new"
          items={new_hypotheses}
          onSelect={onSelectHypothesis}
          renderItem={h => (
            <span className="delta-banner__item">
              {h.short_name} -- {h.source_theory_label || h.source_theory}
            </span>
          )}
        />
      )}
    </div>
  )
}

function DeltaSection({ label, labelClass, items, onSelect, renderItem }) {
  return (
    <div className="delta-banner__section">
      <div className={`delta-banner__label ${labelClass}`}>{label}</div>
      {items.map(h => (
        <div key={h.id} onClick={() => onSelect(h)}>
          {renderItem(h)}
        </div>
      ))}
    </div>
  )
}
