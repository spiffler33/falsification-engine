/**
 * BriefingView — dual-purpose utility view.
 * Top: Research Inbox for capturing notes/links (primary daily input surface).
 * Bottom: Briefing packet display showing what the system sees (6-panel grid).
 *
 * Depends on: GET /api/inbox, GET /api/briefing/latest
 * Depends on: ResearchInbox, BriefingGrid components
 */
import { useApi } from '../hooks/useApi'
import ResearchInbox from '../components/ResearchInbox'
import BriefingGrid from '../components/BriefingGrid'

export default function BriefingView() {
  const { data: inboxItems, loading: inboxLoading, error: inboxError, refetch: refetchInbox } = useApi('/api/inbox')
  const { data: briefing, loading: briefingLoading, error: briefingError } = useApi('/api/briefing/latest')

  return (
    <div className="briefing-view">
      <div className="briefing-view__section">
        {inboxLoading ? (
          <div className="loading">Loading inbox...</div>
        ) : inboxError ? (
          <div className="empty-state">Failed to load inbox.</div>
        ) : (
          <ResearchInbox items={inboxItems} onRefetch={refetchInbox} />
        )}
      </div>

      <div className="briefing-view__divider" />

      <div className="briefing-view__section">
        <h3>Data Briefing</h3>
        {briefing && (
          <div className="briefing-view__timestamp">
            {briefing.is_mock && <span className="briefing-view__mock-badge">MOCK DATA</span>}
            {briefing.staleness_hours != null && briefing.staleness_hours >= 0 && (
              <span>Staleness: {briefing.staleness_hours < 1 ? '<1h' : `${Math.round(briefing.staleness_hours)}h`}</span>
            )}
          </div>
        )}
        {briefingLoading ? (
          <div className="loading">Loading briefing...</div>
        ) : briefingError ? (
          <div className="empty-state">No briefing data available. Run scripts/run_data.py to fetch data.</div>
        ) : (
          <BriefingGrid briefing={briefing} />
        )}
      </div>
    </div>
  )
}
