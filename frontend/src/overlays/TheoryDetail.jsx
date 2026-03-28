/**
 * TheoryDetail -- Full explanation overlay for a theory module.
 * Shows: summary, core mechanism, activation indicators, predictions,
 * hard/soft falsifiers, and current activation data when available.
 *
 * Works in both live and static mode via embedded theoryDescriptions.
 */
import { useEffect, useCallback } from 'react'
import { getTheoryDescription } from '../lib/theoryDescriptions'

const severityLabel = { minor: 'Minor', medium: 'Medium', major: 'Major' }

export default function TheoryDetail({ theory, onClose }) {
  // ESC to close
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleBackdropClick = useCallback((e) => {
    if (e.target === e.currentTarget) onClose()
  }, [onClose])

  if (!theory) return null

  const desc = getTheoryDescription(theory.theory_id)
  if (!desc) return null

  const score = theory.activation_score ?? 0
  const pct = Math.round(score * 100)
  const tier = theory.tier || 'inactive'

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-panel theory-detail">
        <button className="modal-close" onClick={onClose}>X</button>

        {/* Header */}
        <div className="theory-detail__header">
          <h2 className="theory-detail__title">{desc.title}</h2>
          <div className="theory-detail__meta">
            <span className={`theory-detail__tier theory-detail__tier--${tier}`}>
              {tier.toUpperCase()}
            </span>
            <span className="theory-detail__score">{pct}% activation</span>
            {theory.active_phase && (
              <span className="theory-detail__phase">{theory.active_phase}</span>
            )}
            {desc.twoPhase && (
              <span className="theory-detail__phases-label">
                Two-phase: {desc.phases.join(' / ')}
              </span>
            )}
            <span className="theory-detail__horizon">{desc.horizon}</span>
          </div>
        </div>

        {/* Summary */}
        <div className="theory-detail__section">
          <p className="theory-detail__summary">{desc.summary}</p>
        </div>

        {/* Core Mechanism */}
        <div className="theory-detail__section">
          <h3 className="theory-detail__section-title">Core Mechanism</h3>
          <ol className="theory-detail__mechanism">
            {desc.coreMechanism.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </div>

        {/* Activation Indicators */}
        <div className="theory-detail__section">
          <h3 className="theory-detail__section-title">What It Watches</h3>
          <table className="theory-detail__table">
            <thead>
              <tr>
                <th>Indicator</th>
                <th>Threshold</th>
                <th className="theory-detail__num">Weight</th>
              </tr>
            </thead>
            <tbody>
              {desc.indicators.map((ind, i) => (
                <tr key={i}>
                  <td>{ind.name}</td>
                  <td className="theory-detail__threshold">{ind.threshold}</td>
                  <td className="theory-detail__num">{(ind.weight * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Predictions */}
        <div className="theory-detail__section">
          <h3 className="theory-detail__section-title">Predictions When Active</h3>
          <table className="theory-detail__table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Direction</th>
                <th>Magnitude</th>
              </tr>
            </thead>
            <tbody>
              {desc.predictions.map((p, i) => (
                <tr key={i}>
                  <td className="theory-detail__asset">{p.asset}</td>
                  <td>{p.direction}</td>
                  <td className="theory-detail__threshold">{p.magnitude}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Hard Falsifiers */}
        <div className="theory-detail__section">
          <h3 className="theory-detail__section-title">Hard Falsifiers</h3>
          <p className="theory-detail__section-hint">
            Conditions that would kill the theory entirely.
          </p>
          <ul className="theory-detail__falsifiers">
            {desc.hardFalsifiers.map((f, i) => (
              <li key={i} className="theory-detail__falsifier theory-detail__falsifier--hard">
                {f}
              </li>
            ))}
          </ul>
        </div>

        {/* Soft Falsifiers */}
        <div className="theory-detail__section">
          <h3 className="theory-detail__section-title">Soft Falsifiers</h3>
          <p className="theory-detail__section-hint">
            Conditions that wound the theory -- reduce conviction without killing it.
          </p>
          <div className="theory-detail__soft-list">
            {desc.softFalsifiers.map((f, i) => (
              <div key={i} className="theory-detail__soft-item">
                <span className={`theory-detail__severity theory-detail__severity--${f.severity}`}>
                  {severityLabel[f.severity]}
                </span>
                <span className="theory-detail__soft-text">{f.condition}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
