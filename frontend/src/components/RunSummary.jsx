/**
 * RunSummary -- post-run output for the Pipeline Run Mode.
 * Shows lifecycle action counts and thread-based results after conviction scoring.
 *
 * Spec (plan_v7.md "Pipeline Run View Changes"):
 *   Action summary line: "5 CONFIRM | 1 UPDATE | 0 RENEW | 1 RETIRE | 2 NEW"
 *   Thread rows: thread_id, name, lifecycle action, conviction before/after
 *
 * Depends on: GET /api/runs/{run_id} (hypotheses include thread_id, lifecycle_action)
 */
import { useApi } from '../hooks/useApi'
import LifecycleActionBadge from '../shared/LifecycleActionBadge'
import { fmtConviction, fmtDate } from '../lib/format'


const ACTION_ORDER = ['CONFIRM', 'UPDATE', 'RENEW', 'RETIRE', 'NEW']

export default function RunSummary({ runId }) {
  const { data: run, loading } = useApi(runId ? `/api/runs/${runId}` : null, [runId])

  if (!runId || loading || !run) return null

  const hypotheses = run.hypotheses || []
  if (hypotheses.length === 0) return null

  // Count actions by type
  const counts = {}
  for (const a of ACTION_ORDER) counts[a] = 0
  for (const h of hypotheses) {
    const action = h.lifecycle_action || 'NEW'
    counts[action] = (counts[action] || 0) + 1
  }

  // Sort hypotheses: ACTION_ORDER priority, then by conviction descending
  const sorted = [...hypotheses].sort((a, b) => {
    const ai = ACTION_ORDER.indexOf(a.lifecycle_action || 'NEW')
    const bi = ACTION_ORDER.indexOf(b.lifecycle_action || 'NEW')
    if (ai !== bi) return ai - bi
    return (b.conviction || 0) - (a.conviction || 0)
  })

  return (
    <div className="run-summary">
      <div className="run-summary__header">
        <span className="run-summary__title">
          Run {run.id} — {fmtDate(run.timestamp)}
        </span>
      </div>

      <div className="run-summary__actions">
        <span className="run-summary__actions-label">Thread Actions:</span>
        <div className="run-summary__action-counts">
          {ACTION_ORDER.map((action, i) => (
            <span key={action} className="run-summary__action-count">
              {i > 0 && <span className="run-summary__action-sep">|</span>}
              <span className={`run-summary__count ${counts[action] > 0 ? `run-summary__count--${action.toLowerCase()}` : 'run-summary__count--zero'}`}>
                {counts[action]}
              </span>
              {' '}
              <span className="run-summary__action-label">{action}</span>
            </span>
          ))}
        </div>
      </div>

      <table className="run-summary__table">
        <thead>
          <tr>
            <th>Thread</th>
            <th>Hypothesis</th>
            <th>Action</th>
            <th className="run-summary__col-conviction">Conviction</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map(h => (
            <RunSummaryRow key={h.id} hypothesis={h} />
          ))}
        </tbody>
      </table>
    </div>
  )
}


function RunSummaryRow({ hypothesis: h }) {
  const action = h.lifecycle_action || 'NEW'
  const isRetire = action === 'RETIRE'
  const isNew = action === 'NEW'

  const before = isNew ? null : h.conviction_prev
  const after = isRetire ? null : h.conviction

  return (
    <tr className={`run-summary__row ${isRetire ? 'run-summary__row--retire' : ''}`}>
      <td className="run-summary__cell-thread">
        {h.thread_id || '--'}
      </td>
      <td className="run-summary__cell-name">
        {h.short_name}
      </td>
      <td className="run-summary__cell-action">
        <LifecycleActionBadge action={action} />
      </td>
      <td className="run-summary__cell-conviction">
        <ConvictionArrow before={before} after={after} />
      </td>
    </tr>
  )
}


function ConvictionArrow({ before, after }) {
  const left = before != null ? fmtConviction(before) : '--'
  const right = after != null ? fmtConviction(after) : '--'

  // Determine direction class for the "after" value
  let dirClass = ''
  if (before != null && after != null) {
    const delta = after - before
    if (delta > 0.05) dirClass = 'conviction-arrow--up'
    else if (delta < -0.05) dirClass = 'conviction-arrow--down'
  }

  return (
    <span className={`conviction-arrow ${dirClass}`}>
      <span className="conviction-arrow__before">{left}</span>
      <span className="conviction-arrow__sep">&rarr;</span>
      <span className="conviction-arrow__after">{right}</span>
    </span>
  )
}
