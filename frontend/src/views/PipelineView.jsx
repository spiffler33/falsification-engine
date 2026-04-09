/**
 * PipelineView — operational workflow for the five-pass pipeline.
 * Two modes:
 *   Run Mode: 5-step vertical workflow with prompt preview, copy, import
 *   Audit Mode: read-only trace of a completed run's stages
 *
 * Depends on: GET /api/pipeline/status, GET /api/pipeline/prompt/generation,
 *             GET /api/pipeline/prompt/elimination, POST /api/pipeline/import/generation,
 *             POST /api/pipeline/import/elimination, GET /api/runs/latest,
 *             GET /api/inbox/queued
 */
import { useState, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import PipelineStep from '../components/PipelineStep'
import PromptPreview from '../components/PromptPreview'
import ImportPanel from '../components/ImportPanel'
import RunSummary from '../components/RunSummary'
import StatusBadge from '../shared/StatusBadge'
import TheoryTag from '../shared/TheoryTag'
import FreshnessBadge from '../shared/FreshnessBadge'
import LifecycleActionBadge from '../shared/LifecycleActionBadge'
import { fmtConviction, fmtDate } from '../lib/format'

export default function PipelineView({ onSelectHypothesis }) {
  const [mode, setMode] = useState('run') // 'run' | 'audit'

  return (
    <div className="pipeline-view">
      <div className="pipeline-view__header">
        <h2>Pipeline</h2>
        <div className="btn-group">
          <button
            className={`btn ${mode === 'run' ? 'btn--active' : ''}`}
            onClick={() => setMode('run')}
          >
            RUN MODE
          </button>
          <button
            className={`btn ${mode === 'audit' ? 'btn--active' : ''}`}
            onClick={() => setMode('audit')}
          >
            AUDIT MODE
          </button>
        </div>
      </div>

      {mode === 'run' ? <RunMode onSelectHypothesis={onSelectHypothesis} /> : <AuditMode onSelectHypothesis={onSelectHypothesis} />}
    </div>
  )
}


function RunMode({ onSelectHypothesis }) {
  const { data: status, loading, refetch: refetchStatus } = useApi('/api/pipeline/status')
  const { data: queuedItems } = useApi('/api/inbox/queued')

  const [showPrompt, setShowPrompt] = useState(null) // 'generation' | 'elimination' | null
  const [showImport, setShowImport] = useState(null) // 'generation' | 'elimination' | null
  const [promptText, setPromptText] = useState('')
  const [copied, setCopied] = useState(false)
  const [apiRunning, setApiRunning] = useState(null) // 'data' | null
  const [apiError, setApiError] = useState(null)
  const [dataProgress, setDataProgress] = useState([]) // progress log lines for data agent

  const loadPrompt = useCallback((stage) => {
    setShowPrompt(prev => {
      if (prev === stage) return null  // toggle off
      // toggle on — fetch prompt
      api.get(`/api/pipeline/prompt/${stage}`).then(data => {
        setPromptText(typeof data === 'string' ? data : (data?.prompt || JSON.stringify(data, null, 2)))
      }).catch(err => {
        setPromptText('Failed to load prompt: ' + err.message)
      })
      return stage
    })
  }, [])

  const copyPrompt = useCallback(async (stage) => {
    try {
      const data = await api.get(`/api/pipeline/prompt/${stage}`)
      const text = typeof data === 'string' ? data : (data?.prompt || JSON.stringify(data, null, 2))
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [])

  const handleImport = useCallback(async (stage, rawText) => {
    await api.post(`/api/pipeline/import/${stage}`, { json_text: rawText })
    setShowImport(null)
    refetchStatus()
  }, [refetchStatus])

  const refreshData = useCallback(() => {
    setApiRunning('data')
    setApiError(null)
    setDataProgress([])

    const evtSource = new EventSource('/api/briefing/refresh')

    evtSource.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)

        if (msg.stage === 'error') {
          setApiError(msg.detail)
          evtSource.close()
          setApiRunning(null)
          return
        }

        // For yahoo ticker-by-ticker updates, replace the last yahoo line
        // instead of appending every single ticker
        setDataProgress(prev => {
          if (msg.stage === 'yahoo' && prev.length > 0 && prev[prev.length - 1].stage === 'yahoo') {
            return [...prev.slice(0, -1), msg]
          }
          return [...prev, msg]
        })

        if (msg.stage === 'complete') {
          evtSource.close()
          setApiRunning(null)
          refetchStatus()
        }
      } catch {
        // ignore malformed events
      }
    }

    evtSource.onerror = () => {
      evtSource.close()
      // Only set error if we're still running (not already completed)
      setApiRunning(prev => {
        if (prev === 'data') {
          setApiError('Connection to data agent lost')
          return null
        }
        return prev
      })
    }
  }, [refetchStatus])

  if (loading) return <div className="loading">Loading pipeline status...</div>

  // Derive step states from status
  const steps = status?.steps || []
  const getState = (idx) => {
    const step = steps[idx]
    if (!step) return 'waiting'
    return step.state || 'waiting'
  }

  const STEP_DEFS = [
    { label: 'Data Briefing', type: 'Automated' },
    { label: 'Activation Scoring', type: 'Automated' },
    { label: 'Generation Pass', type: 'Human-in-loop' },
    { label: 'Elimination Pass', type: 'Human-in-loop' },
    { label: 'Conviction Scoring', type: 'Automated' },
  ]

  return (
    <div className="pipeline-run">
      <div className="pipeline-steps">
        {STEP_DEFS.map((def, i) => (
          <PipelineStep
            key={i}
            number={i + 1}
            label={def.label}
            type={def.type}
            state={getState(i)}
          >
            {/* Step 1: Data Briefing — refresh button + data quality warning + progress log */}
            {i === 0 && (
              <>
                {status?.briefing_timestamp && (
                  <div className="pipeline-step__meta">
                    Briefing data from: {new Date(status.briefing_timestamp).toLocaleString()}
                  </div>
                )}
                {status?.data_quality && status.data_quality.status !== 'ok' && (
                  <div className={`data-quality-warning data-quality-warning--${status.data_quality.status}`}>
                    {status.data_quality.message}
                  </div>
                )}
                {status?.data_quality && status.data_quality.status === 'ok' && (
                  <div className="data-quality-ok">
                    {status.data_quality.message}
                  </div>
                )}
                <div className="pipeline-step__buttons">
                  <button
                    className="btn btn--primary"
                    onClick={refreshData}
                    disabled={apiRunning !== null}
                  >
                    {apiRunning === 'data' ? 'REFRESHING...' : 'REFRESH DATA'}
                  </button>
                </div>
                {dataProgress.length > 0 && (
                  <div className="data-progress">
                    {dataProgress.map((p, idx) => (
                      <div
                        key={idx}
                        className={`data-progress__line ${p.stage === 'complete' ? 'data-progress__line--done' : ''} ${p.stage === 'error' ? 'data-progress__line--error' : ''}`}
                      >
                        {p.detail}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
            {/* Step 2: Activation — runs fresh every time prompt is built */}
            {i === 1 && (
              <div className="pipeline-step__meta">
                Runs automatically on latest briefing data when you generate a prompt.
              </div>
            )}
            {/* Step 3: Generation — show prompt/copy/import buttons */}
            {i === 2 && (
              <div className="pipeline-step__buttons">
                <button className="btn" onClick={() => loadPrompt('generation')}>
                  {showPrompt === 'generation' ? 'HIDE PROMPT' : 'SHOW PROMPT'}
                </button>
                <button className="btn" onClick={() => copyPrompt('generation')}>
                  {copied ? 'COPIED' : 'COPY TO CLIPBOARD'}
                </button>
                <button className="btn btn--primary" onClick={() => setShowImport(showImport === 'generation' ? null : 'generation')}>
                  IMPORT RESULT
                </button>
              </div>
            )}
            {/* Step 4: Elimination — same pattern */}
            {i === 3 && (
              <div className="pipeline-step__buttons">
                <button className="btn" onClick={() => loadPrompt('elimination')}>
                  {showPrompt === 'elimination' ? 'HIDE PROMPT' : 'SHOW PROMPT'}
                </button>
                <button className="btn" onClick={() => copyPrompt('elimination')}>
                  {copied ? 'COPIED' : 'COPY TO CLIPBOARD'}
                </button>
                <button className="btn btn--primary" onClick={() => setShowImport(showImport === 'elimination' ? null : 'elimination')}>
                  IMPORT RESULT
                </button>
              </div>
            )}
          </PipelineStep>
        ))}
      </div>

      {/* Run summary — shows after conviction scoring completes */}
      {status?.run_id && getState(4) === 'complete' && (
        <RunSummary runId={status.run_id} onSelectHypothesis={onSelectHypothesis} />
      )}

      {apiError && (
        <div className="pipeline-api-error">
          {apiError}
          <button className="btn btn--subtle" onClick={() => setApiError(null)}>DISMISS</button>
        </div>
      )}

      {showPrompt && (
        <PromptPreview
          prompt={promptText}
          visible={true}
          onToggle={() => setShowPrompt(null)}
        />
      )}

      {showImport && (
        <ImportPanel
          stage={showImport}
          visible={true}
          onToggle={() => setShowImport(null)}
          onImport={(parsed) => handleImport(showImport, parsed)}
        />
      )}

      {queuedItems && queuedItems.length > 0 && (
        <div className="pipeline-queued">
          <h3 className="pipeline-queued__title">Queued Inbox Items</h3>
          <div className="pipeline-queued__list">
            {queuedItems.map(item => (
              <div key={item.id} className="pipeline-queued__item">
                <span className="pipeline-queued__date">{fmtDate(item.date)}</span>
                <span className="pipeline-queued__content">{item.content}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}


function AuditMode({ onSelectHypothesis }) {
  // Fetch archive for run list
  const { data: archive, loading: loadingArchive, refetch: refetchArchive } = useApi('/api/runs/archive')
  const [selectedRunId, setSelectedRunId] = useState(null)
  const [expanded, setExpanded] = useState({})

  const runs = archive?.runs || []
  // Use selected run, or auto-select latest
  const activeRunId = selectedRunId || (runs.length > 0 ? runs[0].id : null)

  // Fetch full detail and walk-forward for the active run
  const { data: run, loading: loadingDetail } = useApi(activeRunId ? `/api/runs/${activeRunId}` : null, [activeRunId])
  const { data: walkforward, loading: loadingWF } = useApi(activeRunId ? `/api/runs/${activeRunId}/walkforward` : null, [activeRunId])

  const toggle = (stage) => {
    setExpanded(prev => ({ ...prev, [stage]: !prev[stage] }))
  }

  if (loadingArchive) return <div className="loading">Loading run archive...</div>
  if (runs.length === 0) return <div className="empty-state">No completed runs to audit.</div>

  const outcomeCounts = archive?.outcome_counts || {}

  return (
    <div className="pipeline-audit">
      {/* Run Archive Panel */}
      <div className="run-archive">
        <div className="run-archive__header">
          <span className="run-archive__title">RUN ARCHIVE</span>
          <span className="run-archive__count">{runs.length} {runs.length === 1 ? 'run' : 'runs'} total</span>
        </div>

        <table className="run-archive__table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Date</th>
              <th>Theories Active</th>
              <th>Generated</th>
              <th>Survived</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {runs.map(r => {
              const isSelected = (activeRunId === r.id)
              const survivalRate = r.hypotheses_generated > 0
                ? r.hypotheses_survived / r.hypotheses_generated
                : 0
              return (
                <tr
                  key={r.id}
                  className={`run-archive__row ${isSelected ? 'run-archive__row--selected' : ''}`}
                  onClick={() => setSelectedRunId(r.id)}
                >
                  <td className="run-archive__cell-id">{r.id.replace('R-', '#')}</td>
                  <td className="run-archive__cell-date">{fmtDate(r.timestamp)}</td>
                  <td className="run-archive__cell-theories">
                    {r.active_theories}/{r.total_theories || 8}
                  </td>
                  <td className="run-archive__cell-gen">{r.hypotheses_generated}</td>
                  <td className="run-archive__cell-surv">{r.hypotheses_survived}</td>
                  <td className="run-archive__cell-bar">
                    <SurvivalBar rate={survivalRate} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        <div className="run-archive__outcomes">
          Outcomes:{' '}
          {outcomeCounts.pending > 0 && <span>{outcomeCounts.pending} pending</span>}
          {outcomeCounts.correct > 0 && <span className="outcome-count--correct"> · {outcomeCounts.correct} correct</span>}
          {outcomeCounts.incorrect > 0 && <span className="outcome-count--incorrect"> · {outcomeCounts.incorrect} incorrect</span>}
          {outcomeCounts.partial > 0 && <span className="outcome-count--partial"> · {outcomeCounts.partial} partial</span>}
          {outcomeCounts.expired > 0 && <span className="outcome-count--expired"> · {outcomeCounts.expired} expired</span>}
        </div>
      </div>

      {/* Run Detail (existing audit stages) */}
      {loadingDetail && <div className="loading">Loading run detail...</div>}

      {run && <RunDetail
        run={run}
        expanded={expanded}
        toggle={toggle}
        walkforward={walkforward}
        loadingWF={loadingWF}
        onSelectHypothesis={onSelectHypothesis}
      />}
    </div>
  )
}


function RunDetail({ run, expanded, toggle, walkforward, loadingWF, onSelectHypothesis }) {
  const activation = run.activation_scores || []
  const hypotheses = run.hypotheses || []
  const generated = hypotheses
  const eliminated = hypotheses.filter(h => h.elimination_notes || h.status === 'KILLED')
  const scored = hypotheses.filter(h => h.conviction != null)

  const stages = [
    {
      key: 'activation',
      title: 'Activation',
      render: () => (
        <div className="audit-activation">
          {(Array.isArray(activation) ? activation : []).map(t => {
            const tier = t.is_two_phase ? (t.effective_tier || 'Inactive') : (t.tier || 'Inactive')
            const score = t.is_two_phase
              ? (t.effective_phase && t.phase_scores ? t.phase_scores[t.effective_phase] : 0)
              : (t.score || 0)
            return (
              <div key={t.theory_id} className="audit-activation__row">
                <TheoryTag theoryId={t.theory_id} />
                <span className="audit-activation__tier">{String(tier).toUpperCase()}</span>
                <span className="audit-activation__score">{Math.round(score * 100)}%</span>
                {t.is_two_phase && t.effective_phase && (
                  <span className="audit-activation__phase">{t.effective_phase}</span>
                )}
              </div>
            )
          })}
        </div>
      ),
    },
    {
      key: 'generation',
      title: 'Generation',
      render: () => (
        <div className="audit-generation">
          {generated.map((h, i) => (
            <div key={h.id || i} className="audit-hypothesis">
              <span className="audit-hypothesis__name">{h.short_name}</span>
              <TheoryTag theoryId={h.source_theory || h.theory_id} />
            </div>
          ))}
          {generated.length === 0 && <div className="empty-state">No hypotheses generated.</div>}
        </div>
      ),
    },
    {
      key: 'elimination',
      title: 'Elimination',
      render: () => (
        <div className="audit-elimination">
          {(Array.isArray(eliminated) ? eliminated : []).map((h, i) => (
            <div key={h.id || i} className={`audit-hypothesis ${h.status === 'KILLED' ? 'audit-hypothesis--killed' : ''}`}>
              <StatusBadge status={h.status} />
              <span className="audit-hypothesis__name">{h.short_name}</span>
              {h.elimination_notes && (
                <div className="audit-hypothesis__notes">{h.elimination_notes}</div>
              )}
            </div>
          ))}
          {eliminated.length === 0 && <div className="empty-state">No elimination results.</div>}
        </div>
      ),
    },
    {
      key: 'conviction',
      title: 'Conviction Scoring',
      render: () => (
        <div className="audit-conviction">
          {(Array.isArray(scored) ? scored : []).map((h, i) => (
            <div key={h.id || i} className="audit-scored">
              <span className="audit-scored__score">{fmtConviction(h.conviction)}</span>
              <span className="audit-scored__name">{h.short_name}</span>
              <StatusBadge status={h.status} />
            </div>
          ))}
          {scored.length === 0 && <div className="empty-state">No scored hypotheses.</div>}
        </div>
      ),
    },
    {
      key: 'decision',
      title: 'Human Decision',
      render: () => {
        const survived = (scored || []).filter(h => h.status === 'SURVIVED').length
        const wounded = (scored || []).filter(h => h.status === 'WOUNDED').length
        const killedCount = (scored || []).filter(h => h.status === 'KILLED').length
        const total = scored.length
        const parts = []
        if (survived > 0) parts.push(`${survived} SURVIVED`)
        if (wounded > 0) parts.push(`${wounded} WOUNDED`)
        if (killedCount > 0) parts.push(`${killedCount} KILLED`)
        return (
          <div className="audit-decision">
            <div className="audit-decision__summary">
              This run: {total} hypotheses scored -- {parts.join(', ')}.
            </div>
            <div className="audit-decision__note">
              This audit shows run {run.id} only. The Observatory ledger shows all hypotheses across all runs.
            </div>
          </div>
        )
      },
    },
  ]

  return (
    <>
      <div className="audit-run-info">
        <span className="audit-run-info__id">Run: {run.id || '--'}</span>
        <span className="audit-run-info__date">{fmtDate(run.timestamp)}</span>
      </div>

      {stages.map(stage => (
        <div key={stage.key} className="audit-stage">
          <button className="audit-stage__header" onClick={() => toggle(stage.key)}>
            <span className="audit-stage__title">{stage.title}</span>
            <span className="audit-stage__toggle">{expanded[stage.key] ? '--' : '+'}</span>
          </button>
          {expanded[stage.key] && (
            <div className="audit-stage__content">
              {stage.render()}
            </div>
          )}
        </div>
      ))}

      {/* Walk-Forward Panel */}
      <WalkForwardPanel
        walkforward={walkforward}
        loading={loadingWF}
        runId={run.id}
        hypotheses={hypotheses}
        onSelectHypothesis={onSelectHypothesis}
      />
    </>
  )
}


function WalkForwardPanel({ walkforward, loading, runId, hypotheses, onSelectHypothesis }) {
  if (loading) return <div className="loading">Loading walk-forward data...</div>
  if (!walkforward || !walkforward.rows || walkforward.rows.length === 0) return null

  const oc = walkforward.outcome_counts || {}

  // Build lookup from hypothesis data for realization primitives
  const hypMap = {}
  if (hypotheses) {
    for (const h of hypotheses) {
      hypMap[h.id] = h
    }
  }

  return (
    <div className="walkforward-panel">
      <div className="walkforward-panel__header">
        <span className="walkforward-panel__title">
          WALK-FORWARD · {runId.replace('R-', '#')} · {fmtDate(walkforward.run_date)}
        </span>
        {walkforward.price_snapshot_date && (
          <span className="walkforward-panel__snapshot-date">
            Price snapshot: {fmtDate(walkforward.price_snapshot_date)}
          </span>
        )}
      </div>

      <table className="walkforward-panel__table">
        <thead>
          <tr>
            <th>Hypothesis</th>
            <th>Action</th>
            <th>Age</th>
            <th>Direction</th>
            <th>Entry</th>
            <th>Current</th>
            <th className="walkforward-panel__col-delta">Delta %</th>
            <th>Realization</th>
            <th className="walkforward-panel__col-health">Health</th>
          </tr>
        </thead>
        <tbody>
          {walkforward.rows.map(row => {
            const deltaClass = row.delta_pct != null
              ? (row.delta_pct >= 0 ? 'perf--positive' : 'perf--negative')
              : ''
            const hyp = hypMap[row.hypothesis_id]
            const exprRet = row.expression_return ?? hyp?.expression_return
            return (
              <tr
                key={row.hypothesis_id}
                className="walkforward-panel__row"
                onClick={() => {
                  if (!onSelectHypothesis) return
                  api.get(`/api/hypotheses/${row.hypothesis_id}`).then(h => {
                    onSelectHypothesis(h)
                  }).catch(() => {})
                }}
              >
                <td className="walkforward-panel__cell-name">
                  {row.short_name} ({row.ticker})
                </td>
                <td className="walkforward-panel__cell-action">
                  <LifecycleActionBadge action={row.lifecycle_action} />
                </td>
                <td className="walkforward-panel__cell-age">
                  {row.thread_age != null ? `${row.thread_age}d` : '---'}
                </td>
                <td className={`walkforward-panel__cell-dir walkforward-panel__cell-dir--${row.direction.toLowerCase()}`}>
                  {row.direction}
                </td>
                <td className="walkforward-panel__cell-price">
                  {row.entry_price != null ? `$${row.entry_price.toFixed(2)}` : '---'}
                </td>
                <td className="walkforward-panel__cell-price">
                  {row.current_price != null ? `$${row.current_price.toFixed(2)}` : '---'}
                </td>
                <td className={`walkforward-panel__cell-delta ${deltaClass}`}>
                  {row.delta_pct != null ? `${row.delta_pct >= 0 ? '+' : ''}${row.delta_pct.toFixed(1)}%` : '---'}
                </td>
                <td className="walkforward-panel__cell-realization">
                  {exprRet != null && (
                    <span className={exprRet >= 0 ? 'perf--positive' : 'perf--negative'}>
                      {exprRet >= 0 ? '+' : ''}{(exprRet * 100).toFixed(1)}%
                    </span>
                  )}
                  {hyp && (
                    <FreshnessBadge
                      realization_vs_lower={hyp.realization_vs_lower}
                      realization_vs_upper={hyp.realization_vs_upper}
                      time_elapsed_pct={hyp.time_elapsed_pct}
                    />
                  )}
                  {!exprRet && !hyp && '---'}
                </td>
                <td className="walkforward-panel__cell-health">
                  {row.stale_count > 0 && (
                    <span className="health-flag health-flag--stale">{row.stale_count} STALE</span>
                  )}
                  {row.escalated_count > 0 && (
                    <span className="health-flag health-flag--escalated">{row.escalated_count} ESC</span>
                  )}
                  {row.has_emergent_risk && (
                    <span className="health-flag health-flag--emergent" title="Emergent risk identified">*</span>
                  )}
                  {!row.stale_count && !row.escalated_count && !row.has_emergent_risk && (
                    <span className="health-flag health-flag--clear">--</span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="walkforward-panel__outcomes">
        Outcomes:{' '}
        {oc.correct > 0 && <span className="outcome-count--correct">{oc.correct} correct</span>}
        {oc.incorrect > 0 && <span className="outcome-count--incorrect"> · {oc.incorrect} incorrect</span>}
        {oc.pending > 0 && <span> · {oc.pending} pending</span>}
        {oc.partial > 0 && <span className="outcome-count--partial"> · {oc.partial} partial</span>}
      </div>
    </div>
  )
}


function SurvivalBar({ rate }) {
  const filled = Math.round(rate * 4)
  const blocks = []
  for (let i = 0; i < 4; i++) {
    blocks.push(
      <span
        key={i}
        className={`survival-block ${i < filled ? 'survival-block--filled' : 'survival-block--empty'}`}
      />
    )
  }
  return <span className="survival-bar">{blocks}</span>
}
