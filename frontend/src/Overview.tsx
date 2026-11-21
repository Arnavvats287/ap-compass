import { Link } from 'react-router-dom'
import { ArrowUpRight, Upload } from 'lucide-react'
import { useDashboard, useRuns } from './queries'
import { Empty, ErrorState, Loading, RunTable } from './components'
import OperationsBento from './OperationsBento'
import LaunchDitherField from './LaunchDitherField'

export default function Overview() {
  const dashboard = useDashboard()
  const runs = useRuns()
  const retry = () => void runs.refetch()
  return (
    <div className="ops-page ops-overview">
      <LaunchDitherField />
      <div className="page-heading ops-heading">
        <div>
          <h1>
            Invoice operations <em>at a glance</em>
          </h1>
          <p>See what’s ready, what needs attention, and what happens next.</p>
        </div>
        <Link className="button primary ops-primary-action" to="/runs/upload">
          <Upload size={17} aria-hidden="true" /> Process invoices
        </Link>
      </div>
      {dashboard.isPending ? (
        <div className="ops-loading" role="status">
          <p>Loading operations overview…</p>
          <div className="ops-metrics" aria-hidden="true">
            {[0, 1, 2, 3].map((slot) => (
              <div key={slot} className="ops-card ops-metric" />
            ))}
          </div>
          <div className="ops-loading-grid" aria-hidden="true">
            <div className="ops-card" />
            <div className="ops-card" />
          </div>
        </div>
      ) : dashboard.isError ? (
        <ErrorState retry={() => void dashboard.refetch()} />
      ) : null}
      <OperationsBento
        metrics={dashboard.data}
        runs={runs.data ?? []}
        listState={runs.status}
        retry={retry}
        recentActivity={
          <section data-overview-section="activity" className="panel queue-panel">
            <div className="section-heading">
              <div>
                <h2>Recent invoice activity</h2>
                <p>Persisted decisions and work in progress.</p>
              </div>
              <Link className="text-link" to="/runs">
                View invoice queue
                <ArrowUpRight size={16} aria-hidden="true" />
              </Link>
            </div>
            {runs.isPending ? (
              <Loading />
            ) : runs.isError ? (
              <ErrorState retry={() => void runs.refetch()} />
            ) : runs.data?.length ? (
              <RunTable runs={runs.data.slice(0, 8)} />
            ) : (
              <Empty />
            )}
          </section>
        }
      />
    </div>
  )
}
