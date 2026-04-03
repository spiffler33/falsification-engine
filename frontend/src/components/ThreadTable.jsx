import StatusBadge from '../shared/StatusBadge'
import TheoryTag from '../shared/TheoryTag'
import { AssetTags } from '../shared/AssetTag'
import ConvictionDisplay from '../shared/ConvictionDisplay'
import FalsifierCompact from '../shared/FalsifierCompact'
import FreshnessBadge from '../shared/FreshnessBadge'
import ThreadAgeBadge from '../shared/ThreadAgeBadge'
import LifecycleActionBadge from '../shared/LifecycleActionBadge'
import ThreadFlagsBadge from '../shared/ThreadFlagsBadge'
import ActionMarker from '../shared/ActionMarker'

/**
 * ThreadTable -- the primary data table in the thread-centered Ledger.
 * Rows = threads (not instances). Each row shows the latest instance's state
 * plus thread-level metadata (age, confirmation count, lifecycle action, flags).
 *
 * Row click -> opens hypothesis detail for the latest instance.
 */
export default function ThreadTable({ threads, onSelect }) {
  if (!threads || threads.length === 0) {
    return <div className="empty-state">No threads to display.</div>
  }

  // Split into active and retired for rendering order
  const active = threads.filter(t => t.thread_status !== 'RETIRED')
  const retired = threads.filter(t => t.thread_status === 'RETIRED')

  return (
    <table className="thread-table">
      <thead>
        <tr>
          <th className="col-status">Status</th>
          <th className="col-hypothesis">Thread</th>
          <th className="col-theory">Theory</th>
          <th className="col-conviction">Conv.</th>
          <th className="col-freshness">Freshness</th>
          <th className="col-falsifiers">Fals.</th>
          <th className="col-assets">Assets</th>
          <th className="col-thread-age">Age</th>
          <th className="col-lifecycle">Action</th>
          <th className="col-flags">Flags</th>
          <th className="col-markers"></th>
        </tr>
      </thead>
      <tbody>
        {active.map(t => (
          <ThreadRow key={t.thread_id} thread={t} onSelect={onSelect} />
        ))}
        {retired.length > 0 && active.length > 0 && (
          <tr className="thread-table__divider">
            <td colSpan={11}>
              <span className="thread-table__divider-label">
                RETIRED ({retired.length})
              </span>
            </td>
          </tr>
        )}
        {retired.map(t => (
          <ThreadRow key={t.thread_id} thread={t} onSelect={onSelect} retired />
        ))}
      </tbody>
    </table>
  )
}

function ThreadRow({ thread: t, onSelect, retired = false }) {
  return (
    <tr
      className={threadRowClass(t, retired)}
      onClick={() => onSelect(t)}
    >
      <td className="col-status">
        <StatusBadge status={t.status} />
      </td>
      <td className="col-hypothesis">
        <span className="thread-name">{t.short_name}</span>
        <span className="thread-id">{t.thread_id}</span>
      </td>
      <td className="col-theory">
        <TheoryTag theoryId={t.source_theory} label={t.source_theory_label} />
      </td>
      <td className="col-conviction">
        <ConvictionDisplay
          conviction={t.conviction}
          convictionPrev={t.conviction_prev}
        />
      </td>
      <td className="col-freshness">
        <FreshnessBadge
          realization_vs_lower={t.realization_vs_lower}
          realization_vs_upper={t.realization_vs_upper}
          time_elapsed_pct={t.time_elapsed_pct}
          label={t.freshness_label}
        />
      </td>
      <td className="col-falsifiers">
        <FalsifierCompact
          triggered={t.falsifier_health?.triggered}
          total={t.falsifier_health?.total}
        />
      </td>
      <td className="col-assets">
        <AssetTags
          assets={t.predicted_assets}
          directions={t.asset_direction}
        />
      </td>
      <td className="col-thread-age">
        <ThreadAgeBadge
          days={t.thread_age_days}
          confirmationCount={t.confirmation_count}
        />
      </td>
      <td className="col-lifecycle">
        <LifecycleActionBadge action={t.lifecycle_action} />
      </td>
      <td className="col-flags">
        <ThreadFlagsBadge
          staleCount={t.stale_count}
          escalatedCount={t.escalated_count}
          hasEmergentRisk={t.has_emergent_risk}
        />
      </td>
      <td className="col-markers">
        <ActionMarker
          hasAction={t.has_action}
          hasNotes={false}
        />
      </td>
    </tr>
  )
}

function threadRowClass(t, retired) {
  const classes = []
  if (retired) classes.push('row--retired')
  if (t.status === 'KILLED') classes.push('row--killed')
  if (t.status === 'WOUNDED') classes.push('row--wounded')
  return classes.join(' ')
}
