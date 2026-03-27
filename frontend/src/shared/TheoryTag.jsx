import { shortTheory } from '../lib/format'

/**
 * TheoryTag — displays theory_id as a compact tag.
 * JetBrains Mono 10px on a bg-secondary pill.
 */
export default function TheoryTag({ theoryId, label }) {
  const display = label || shortTheory(theoryId)
  return <span className="theory-tag">{display}</span>
}
