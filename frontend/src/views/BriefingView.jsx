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
  const { data: inboxItems, loading: inboxLoading, refetch: refetchInbox } = useApi('/api/inbox')
  const { data: briefing, loading: briefingLoading } = useApi('/api/briefing/latest')

  return (
    <div className="briefing-view">
      <div className="briefing-view__section">
        {inboxLoading ? (
          <div className="loading">Loading inbox...</div>
        ) : (
          <ResearchInbox items={inboxItems} onRefetch={refetchInbox} />
        )}
      </div>

      <div className="briefing-view__divider" />

      <div className="briefing-view__section">
        <h3>Data Briefing</h3>
        {briefing?.fetched_at && (
          <div className="briefing-view__timestamp">
            Last updated: {briefing.fetched_at}
          </div>
        )}
        {briefingLoading ? (
          <div className="loading">Loading briefing...</div>
        ) : (
          <BriefingGrid briefing={briefing} />
        )}
      </div>
    </div>
  )
}
