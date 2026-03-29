import StatusBadge from '../shared/StatusBadge'
import TheoryTag from '../shared/TheoryTag'
import { AssetTags } from '../shared/AssetTag'
import ConvictionDisplay from '../shared/ConvictionDisplay'
import FalsifierCompact from '../shared/FalsifierCompact'
import ActionMarker from '../shared/ActionMarker'
import { fmtAge } from '../lib/format'

const CHANNEL_LABELS = {
  nominal_price_decline: 'NOM. DECLINE',
  inflationary_grind: 'INFL. GRIND',
  real_asset_outperformance: 'REAL ASSETS',
  sector_rotation: 'ROTATION',
  broad_credit_contraction: 'CREDIT CONTR.',
  sector_credit_stress: 'SECTOR STRESS',
}

/**
 * HypothesisTable — the primary data table in the Ledger.
 * Columns: Status, Hypothesis, Theory, Channel, Conv., Fals., Assets, Age, Markers.
 * Row click -> opens hypothesis detail.
 */
export default function HypothesisTable({ hypotheses, onSelect }) {
  if (!hypotheses || hypotheses.length === 0) {
    return <div className="empty-state">No hypotheses to display.</div>
  }

  const anyChannel = hypotheses.some(h => h.resolution_channel)

  return (
    <table className="hypothesis-table">
      <thead>
        <tr>
          <th className="col-status">Status</th>
          <th className="col-hypothesis">Hypothesis</th>
          <th className="col-theory">Theory</th>
          {anyChannel && <th className="col-channel">Channel</th>}
          <th className="col-conviction">Conv.</th>
          <th className="col-falsifiers">Fals.</th>
          <th className="col-assets">Assets</th>
          <th className="col-age">Age</th>
          <th className="col-markers"></th>
        </tr>
      </thead>
      <tbody>
        {hypotheses.map(h => (
          <tr
            key={h.id}
            className={rowClass(h)}
            onClick={() => onSelect(h)}
          >
            <td className="col-status">
              <StatusBadge status={h.status} />
            </td>
            <td className="col-hypothesis">
              <span className="hypothesis-name">{h.short_name}</span>
            </td>
            <td className="col-theory">
              <TheoryTag theoryId={h.source_theory} label={h.source_theory_label} />
            </td>
            {anyChannel && (
              <td className="col-channel">
                <ChannelTag
                  channel={h.resolution_channel}
                  originalChannel={h.resolution_channel_original}
                />
              </td>
            )}
            <td className="col-conviction">
              <ConvictionDisplay
                conviction={h.conviction}
                convictionPrev={h.conviction_prev}
              />
            </td>
            <td className="col-falsifiers">
              <FalsifierCompact
                triggered={h.falsifier_health?.triggered}
                total={h.falsifier_health?.total}
              />
            </td>
            <td className="col-assets">
              <AssetTags
                assets={h.predicted_assets}
                directions={h.asset_direction}
              />
            </td>
            <td className="col-age">
              <span className="data-text" style={{ fontSize: '11px' }}>
                {fmtAge(h.age)}
              </span>
            </td>
            <td className="col-markers">
              <ActionMarker
                hasAction={h.has_action}
                hasNotes={h.research_notes?.length > 0}
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function ChannelTag({ channel, originalChannel }) {
  if (!channel) return null
  const label = CHANNEL_LABELS[channel] || channel.replace(/_/g, ' ').toUpperCase()
  const corrected = originalChannel && originalChannel !== channel
  return (
    <span className={`channel-tag${corrected ? ' channel-tag--corrected' : ''}`} title={
      corrected
        ? `Corrected from: ${CHANNEL_LABELS[originalChannel] || originalChannel}`
        : channel.replace(/_/g, ' ')
    }>
      {label}
      {corrected && <span className="channel-tag__marker">*</span>}
    </span>
  )
}

function rowClass(h) {
  if (h.status === 'KILLED') return 'row--killed'
  if (h.status === 'WOUNDED') return 'row--wounded'
  return ''
}
