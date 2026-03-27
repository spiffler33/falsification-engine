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
import StatusBadge from '../shared/StatusBadge'
import TheoryTag from '../shared/TheoryTag'
import { fmtConviction, fmtDate } from '../lib/format'

export default function PipelineView() {
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

      {mode === 'run' ? <RunMode /> : <AuditMode />}
    </div>
  )
}


function RunMode() {
  const { data: status, loading, refetch: refetchStatus } = useApi('/api/pipeline/status')
  const { data: queuedItems } = useApi('/api/inbox/queued')

  const [showPrompt, setShowPrompt] = useState(null) // 'generation' | 'elimination' | null
  const [showImport, setShowImport] = useState(null) // 'generation' | 'elimination' | null
  const [promptText, setPromptText] = useState('')
  const [copied, setCopied] = useState(false)
  const [apiRunning, setApiRunning] = useState(null) // 'generation' | 'elimination' | null
  const [apiError, setApiError] = useState(null)

  const loadPrompt = useCallback(async (stage) => {
    if (showPrompt === stage) {
      setShowPrompt(null)
      return
    }
    try {
      const data = await api.get(`/api/pipeline/prompt/${stage}`)
      setPromptText(typeof data === 'string' ? data : (data?.prompt || JSON.stringify(data, null, 2)))
      setShowPrompt(stage)
    } catch (err) {
      setPromptText('Failed to load prompt: ' + err.message)
      setShowPrompt(stage)
    }
  }, [showPrompt])

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

  const runViaApi = useCallback(async (stage) => {
    setApiRunning(stage)
    setApiError(null)
    try {
      await api.post(`/api/pipeline/run/${stage}`, { web_search: true })
      refetchStatus()
    } catch (err) {
      setApiError(err.message || `API ${stage} failed`)
    } finally {
      setApiRunning(null)
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
            {/* Step 3: Generation — show prompt/copy/import buttons */}
            {i === 2 && (
              <>
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
                <div className="pipeline-step__api-alt">
                  <button
                    className="btn btn--subtle"
                    onClick={() => runViaApi('generation')}
                    disabled={apiRunning !== null}
                  >
                    {apiRunning === 'generation' ? 'RUNNING VIA API...' : 'or run via API'}
                  </button>
                </div>
              </>
            )}
            {/* Step 4: Elimination — same pattern */}
            {i === 3 && (
              <>
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
                <div className="pipeline-step__api-alt">
                  <button
                    className="btn btn--subtle"
                    onClick={() => runViaApi('elimination')}
                    disabled={apiRunning !== null}
                  >
                    {apiRunning === 'elimination' ? 'RUNNING VIA API...' : 'or run via API'}
                  </button>
                </div>
              </>
            )}
          </PipelineStep>
        ))}
      </div>

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


function AuditMode() {
  // First fetch the latest run summary to get the run ID
  const { data: latestRun, loading: loadingSummary } = useApi('/api/runs/latest')
  // Then fetch full run detail with all stage outputs
  const runId = latestRun?.id || null
  const { data: run, loading: loadingDetail } = useApi(runId ? `/api/runs/${runId}` : null)
  const [expanded, setExpanded] = useState({})

  const toggle = (stage) => {
    setExpanded(prev => ({ ...prev, [stage]: !prev[stage] }))
  }

  if (loadingSummary || loadingDetail) return <div className="loading">Loading run data...</div>
  if (!run) return <div className="empty-state">No completed runs to audit.</div>

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
        const survivorCount = (scored || []).filter(h => h.status !== 'KILLED').length
        return (
          <div className="audit-decision">
            {survivorCount} hypothesis{survivorCount !== 1 ? 'es' : ''} survived. The system has done its work.
          </div>
        )
      },
    },
  ]

  return (
    <div className="pipeline-audit">
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
    </div>
  )
}
