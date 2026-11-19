import { Link } from 'react-router-dom'
import { ArrowUpRight, ShieldCheck } from 'lucide-react'
import { useDashboard, useRuns } from './queries'
import { Empty, ErrorState, Loading, RunTable, UploadPanel } from './components'
import { money } from './format'

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
        <span className="quiet-label">
          <ShieldCheck size={16} aria-hidden="true" />
          Two-way AP controls
        </span>
      </div>
      {dashboard.isPending ? (
        <Loading label="Loading operations overview…" />
      ) : dashboard.isError ? (
        <ErrorState retry={() => void dashboard.refetch()} />
      ) : (
        metrics && (
          <>
            <section className="metric-strip" aria-label="Invoice operations counts">
              {[
                ['Total invoices', metrics.total_runs, 'all', ''],
                ['Ready to process', metrics.ready, 'ready', 'ready'],
                ['Needs review', metrics.review_required, 'review', 'review'],
                ['Blocked', metrics.blocked, 'blocked', 'blocked'],
                ['In progress', metrics.in_progress, 'processing', 'processing'],
              ].map(([label, count, filter, tone]) => (
                <Link
                  key={label}
                  to={`/runs${filter === 'all' ? '' : `?status=${filter}`}`}
                  className={`metric ${tone}`}
                >
                  <span>{label}</span>
                  <strong>{count}</strong>
                  <ArrowUpRight size={16} aria-hidden="true" />
                </Link>
              ))}
            </section>
            <div className="overview-grid">
              <div className="overview-main">
                <section className="distribution panel" aria-labelledby="distribution-title">
                  <div className="section-heading">
                    <h2 id="distribution-title">Decision distribution</h2>
                    <span className="muted">{metrics.completed} completed</span>
                  </div>
                  {metrics.completed > 0 ? (
                    <>
                      <div className="distribution-bar" aria-hidden="true">
                        {[
                          ['ready', metrics.ready],
                          ['review', metrics.review_required],
                          ['blocked', metrics.blocked],
                        ].map(([tone, count]) => (
                          <span
                            key={tone}
                            className={String(tone)}
                            style={{ flexGrow: Number(count) }}
                          />
                        ))}
                      </div>
                      <ul className="distribution-legend">
                        <li>
                          <span className="legend-line ready" />
                          Ready <strong>{metrics.ready}</strong>
                        </li>
                        <li>
                          <span className="legend-line review" />
                          Needs review <strong>{metrics.review_required}</strong>
                        </li>
                        <li>
                          <span className="legend-line blocked" />
                          Blocked <strong>{metrics.blocked}</strong>
                        </li>
                      </ul>
                    </>
                  ) : (
                    <p>
                      No completed decisions yet. Outcomes will appear after your first analysis.
                    </p>
                  )}
                </section>
                {metrics.flagged_invoice_net_by_currency && (
                  <section className="attention-value" aria-label="Flagged invoice net value">
                    <div>
                      <h2>Invoice value requiring attention</h2>
                      <p>
                        Known invoice net for completed review or blocked runs. Each analysis is
                        counted; this is not unique payable exposure.
                      </p>
                    </div>
                    <div className="flagged-amounts">
                      {Object.entries(metrics.flagged_invoice_net_by_currency).length ? (
                        Object.entries(metrics.flagged_invoice_net_by_currency).map(
                          ([currency, value]) => (
                            <strong className="amount" key={currency}>
                              {money(value, currency)} <small>{currency} net</small>
                            </strong>
                          ),
                        )
                      ) : (
                        <span>No flagged invoice value</span>
                      )}
                    </div>
                    <small>
                      Grouped by currency.{' '}
                      {metrics.flagged_invoice_net_missing_count
                        ? `${metrics.flagged_invoice_net_missing_count} run(s) with unknown net or currency excluded.`
                        : 'Unknown amounts are excluded.'}
                    </small>
                  </section>
                )}
                <div className="technical-counts">
                  <Link to="/runs?status=failed">
                    Processing failed <strong>{metrics.processing_failed}</strong>
                  </Link>
                  <Link to="/runs?status=interrupted">
                    Interrupted <strong>{metrics.interrupted}</strong>
                  </Link>
                </div>
              </div>
              <UploadPanel />
            </div>
          </>
        )
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
