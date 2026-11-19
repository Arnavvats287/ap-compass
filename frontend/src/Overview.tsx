import { Link } from 'react-router-dom'
import { ArrowUpRight, ShieldCheck } from 'lucide-react'
import { useDashboard, useRuns } from './queries'
import { Empty, ErrorState, Loading, RunTable } from './components'
import OperationsBento from './OperationsBento'

export default function Overview() {
  const dashboard = useDashboard()
  const runs = useRuns()
  const metrics = dashboard.data
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Operations overview</h1>
          <p>Turn messy vendor invoices into clear, controlled, actionable AP decisions.</p>
        </div>
        <a className="button secondary overview-upload-link" href="#upload">
          Process an invoice
        </a>
        <span className="quiet-label">
          <ShieldCheck size={16} aria-hidden="true" />
          Two-way AP controls
        </span>
      </div>
      <p className="queue-basis">
        Counts reflect recorded automated decisions. Human-reviewed assessments are labelled
        separately in the queue.
      </p>
      {dashboard.isPending ? (
        <Loading label="Loading operations overview…" />
      ) : dashboard.isError ? (
        <ErrorState retry={() => void dashboard.refetch()} />
      ) : (
        metrics && <OperationsBento metrics={metrics} />
      )}
      <section className="panel queue-panel">
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
    </>
  )
}
