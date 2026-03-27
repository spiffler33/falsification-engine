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

  const handleImport = useCallback(async (stage, parsed) => {
    await api.post(`/api/pipeline/import/${stage}`, parsed)
    setShowImport(null)
    refetchStatus()
  }, [refetchStatus])

  if (loading) return <div className="loading">Loading pipeline status...</div>

  // Derive step states from status
  const steps = status?.steps || []
  const getState = (idx) => {
    const step = steps[idx]
    if (!step) return 'waiting'
    if (step.status === 'complete') return 'complete'
    if (step.status === 'ready') return 'ready'
    return 'waiting'
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
  const { data: run, loading } = useApi('/api/runs/latest')
  const [expanded, setExpanded] = useState({})

  const toggle = (stage) => {
    setExpanded(prev => ({ ...prev, [stage]: !prev[stage] }))
  }

  if (loading) return <div className="loading">Loading run data...</div>
  if (!run) return <div className="empty-state">No completed runs to audit.</div>

  const activation = run.activation_scores || run.activation || []
  const generated = run.generated_hypotheses || run.generation || []
  const eliminated = run.elimination_results || run.elimination || []
  const scored = run.conviction_results || run.scored || []

  const stages = [
    {
      key: 'activation',
      title: 'Activation',
      render: () => (
        <div className="audit-activation">
          {(Array.isArray(activation) ? activation : []).map(t => (
            <div key={t.theory_id} className="audit-activation__row">
              <TheoryTag theoryId={t.theory_id} />
              <span className="audit-activation__tier">{(t.tier || '').toUpperCase()}</span>
              <span className="audit-activation__score">{Math.round((t.activation_score || 0) * 100)}%</span>
            </div>
          ))}
        </div>
      ),
    },
    {
      key: 'generation',
      title: 'Generation',
      render: () => (
        <div className="audit-generation">
          {(Array.isArray(generated) ? generated : []).map((h, i) => (
            <div key={h.id || i} className="audit-hypothesis">
              <span className="audit-hypothesis__name">{h.short_name}</span>
              <TheoryTag theoryId={h.source_theory} />
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
        <span className="audit-run-info__id">Run: {run.id || run.run_id || '--'}</span>
        <span className="audit-run-info__date">{fmtDate(run.date || run.created_at)}</span>
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
