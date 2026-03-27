/**
 * AssetTag — displays an ETF ticker with LONG/SHORT coloring.
 * Shows max 3 tags, then "+N" overflow.
 */
export default function AssetTag({ ticker, direction }) {
  const cls = `asset-tag asset-tag--${(direction || 'long').toLowerCase()}`
  return <span className={cls}>{ticker}</span>
}

export function AssetTags({ assets, directions, max = 3 }) {
  if (!assets || assets.length === 0) return null
  const shown = assets.slice(0, max)
  const overflow = assets.length - max

  return (
    <span>
      {shown.map(ticker => (
        <AssetTag
          key={ticker}
          ticker={ticker}
          direction={directions?.[ticker] || 'LONG'}
        />
      ))}
      {overflow > 0 && (
        <span className="asset-tag asset-tag--overflow">+{overflow}</span>
      )}
    </span>
  )
}
