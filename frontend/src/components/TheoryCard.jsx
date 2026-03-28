/**
 * TheoryCard — displays a single theory module with activation state.
 * Activation bar colored by tier, phase label for two-phase theories.
 * Clickable — opens TheoryDetail overlay.
 */
export default function TheoryCard({ theory, onClick }) {
  const score = theory.activation_score ?? 0
  const pct = Math.round(score * 100)
  const tier = theory.tier || (score >= 0.60 ? 'active' : score >= 0.30 ? 'adjacent' : 'inactive')
  const tierLabel = tier.toUpperCase()
  const phase = theory.active_phase || null

  const tierClass = `theory-card--${tier}`
  const barClass = `theory-card__bar-fill--${tier}`

  return (
    <div
      className={`theory-card ${tierClass}`}
      onClick={() => onClick && onClick(theory)}
      style={{ cursor: 'pointer' }}
    >
      <div className="theory-card__header">
        <div className="theory-card__name">{theory.name || theory.theory_id}</div>
        <span className={`theory-card__tier theory-card__tier--${tier}`}>{tierLabel}</span>
      </div>
      <div className="theory-card__bar">
        <div className={`theory-card__bar-fill ${barClass}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="theory-card__footer">
        <span className="theory-card__score">{pct}%</span>
        {phase && <span className="theory-card__phase">{phase}</span>}
      </div>
    </div>
  )
}
