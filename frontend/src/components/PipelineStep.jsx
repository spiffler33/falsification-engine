/**
 * PipelineStep — a single step in the pipeline workflow.
 * States: complete (green check), ready (accent, user action needed), waiting (gray).
 * Ready steps show action buttons (SHOW PROMPT, COPY, IMPORT).
 */

export default function PipelineStep({
  number,
  label,
  type,
  state,
  children,
}) {
  // state: 'complete' | 'ready' | 'waiting'
  const stateClass = `pipeline-step--${state}`
  const indicatorClass = `pipeline-step__indicator--${state}`

  return (
    <div className={`pipeline-step ${stateClass}`}>
      <div className="pipeline-step__header">
        <div className={`pipeline-step__indicator ${indicatorClass}`}>
          {state === 'complete' ? '\u2713' : number}
        </div>
        <div className="pipeline-step__info">
          <div className="pipeline-step__label">{label}</div>
          <div className="pipeline-step__type">{type}</div>
        </div>
        <div className={`pipeline-step__state pipeline-step__state--${state}`}>
          {state === 'complete' ? 'COMPLETE' : state === 'ready' ? 'READY' : 'WAITING'}
        </div>
      </div>
      {state === 'ready' && children && (
        <div className="pipeline-step__actions">
          {children}
        </div>
      )}
    </div>
  )
}
