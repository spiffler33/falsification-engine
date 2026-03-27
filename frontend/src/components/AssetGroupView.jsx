import HypothesisTable from './HypothesisTable'

/**
 * AssetGroupView — groups alive hypotheses by predicted ETF ticker.
 * Each group: ticker, direction consensus, hypothesis count, convergence info.
 * Sorted by max conviction descending.
 */
export default function AssetGroupView({ hypotheses, onSelect }) {
  const groups = buildAssetGroups(hypotheses)

  if (groups.length === 0) {
    return <div className="empty-state">No alive hypotheses to group by asset.</div>
  }

  return (
    <div>
      {groups.map(g => (
        <div key={g.ticker} className="asset-group">
          <div className="asset-group__header">
            <span className="asset-group__ticker">{g.ticker}</span>
            <span className={`asset-group__direction asset-group__direction--${g.directionConsensus.toLowerCase()}`}>
              {g.directionConsensus}
            </span>
            <span className="asset-group__count">
              {g.hypotheses.length} {g.hypotheses.length === 1 ? 'hypothesis' : 'hypotheses'}
            </span>
            <span className="asset-group__convergence">
              {g.theoryCount >= 2
                ? `${g.theoryCount}-theory convergence`
                : g.hypotheses[0]?.source_theory_label || g.hypotheses[0]?.source_theory}
            </span>
          </div>
          <HypothesisTable hypotheses={g.hypotheses} onSelect={onSelect} />
        </div>
      ))}
    </div>
  )
}

function buildAssetGroups(hypotheses) {
  if (!hypotheses) return []

  // Only alive hypotheses
  const alive = hypotheses.filter(h => h.status !== 'KILLED')

  // Group by ticker
  const tickerMap = {}
  for (const h of alive) {
    const assets = h.predicted_assets || []
    for (const ticker of assets) {
      if (!tickerMap[ticker]) tickerMap[ticker] = []
      tickerMap[ticker].push(h)
    }
  }

  // Build group objects
  const groups = Object.entries(tickerMap).map(([ticker, hyps]) => {
    // Direction consensus
    const directions = hyps.map(h => h.asset_direction?.[ticker]).filter(Boolean)
    const longs = directions.filter(d => d === 'LONG').length
    const shorts = directions.filter(d => d === 'SHORT').length
    let directionConsensus = 'LONG'
    if (longs > 0 && shorts > 0) directionConsensus = 'MIXED'
    else if (shorts > longs) directionConsensus = 'SHORT'

    // Unique theories
    const theories = new Set(hyps.map(h => h.source_theory))

    // Sort hypotheses by conviction desc
    const sorted = [...hyps].sort((a, b) => (b.conviction || 0) - (a.conviction || 0))

    return {
      ticker,
      directionConsensus,
      hypotheses: sorted,
      theoryCount: theories.size,
      maxConviction: sorted[0]?.conviction || 0,
    }
  })

  // Sort groups by max conviction desc
  groups.sort((a, b) => b.maxConviction - a.maxConviction)

  return groups
}
