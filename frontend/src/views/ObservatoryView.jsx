/**
 * ObservatoryView — background context layer showing all theory modules
 * with their activation state. "Why is the system generating these hypotheses?"
 *
 * Depends on: GET /api/theories (returns theory list with activation scores)
 * Depends on: TheoryCard component
 */
import { useApi } from '../hooks/useApi'
import TheoryCard from '../components/TheoryCard'

export default function ObservatoryView() {
  const { data: theories, loading, error } = useApi('/api/theories')

  if (loading) return <div className="loading">Loading theories...</div>
  if (error) return <div className="empty-state">Failed to load theory modules.</div>
  if (!theories || theories.length === 0) return <div className="empty-state">No theory modules found.</div>

  // Sort: Active first, then Adjacent, then Inactive — within each tier, by score desc
  const tierOrder = { active: 0, adjacent: 1, inactive: 2 }
  const sorted = [...theories].sort((a, b) => {
    const ta = tierOrder[a.tier] ?? 2
    const tb = tierOrder[b.tier] ?? 2
    if (ta !== tb) return ta - tb
    return (b.activation_score ?? 0) - (a.activation_score ?? 0)
  })

  return (
    <div className="observatory-view">
      <h2>Observatory</h2>
      <div className="observatory-grid">
        {sorted.map(t => (
          <TheoryCard key={t.theory_id} theory={t} />
        ))}
      </div>
    </div>
  )
}
