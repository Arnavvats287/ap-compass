import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import { UploadPanel } from './components'
import { money } from './format'
import type { Dashboard } from './types'

function Metric({
  label,
  count,
  filter,
  tone,
}: {
  label: string
  count: number
  filter: string
  tone: string
}) {
  return (
    <Link className={`metric ${tone}`} to={`/runs${filter === 'all' ? '' : `?status=${filter}`}`}>
      <span>{label}</span>
      <strong>{count}</strong>
      <ArrowUpRight size={17} aria-hidden="true" />
    </Link>
  )
}

/** Real projections only. Layout priority never changes metric definitions or outcomes. */
export default function OperationsBento({ metrics }: { metrics: Dashboard }) {
  return (
    <section className="metric-strip overview-bento" aria-label="Invoice operations counts">
      <div className="attention-hub">
        <div className="attention-heading">
          <h2>Invoice attention</h2>
          <span>Review & resolution</span>
        </div>
        <div className="attention-workload">
          <Metric
            label="Needs review"
            count={metrics.review_required}
            filter="review"
            tone="review"
          />
          <Metric label="Blocked" count={metrics.blocked} filter="blocked" tone="blocked" />
        </div>
        {metrics.flagged_invoice_net_by_currency && (
          <section className="attention-value" aria-label="Flagged invoice net value">
            <div>
              <h2>Invoice value requiring attention</h2>
              <p>
                Known invoice net for completed review or blocked runs. Each analysis is counted;
                this is not unique payable exposure.
              </p>
            </div>
            <div className="flagged-amounts">
              {Object.entries(metrics.flagged_invoice_net_by_currency).length ? (
                Object.entries(metrics.flagged_invoice_net_by_currency).map(([currency, value]) => (
                  <strong className="amount" key={currency}>
                    {money(value, currency)}
                    <small>{currency} net</small>
                  </strong>
                ))
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
      </div>
      <UploadPanel />
      <div className="supporting-metrics">
        <Metric label="Ready to process" count={metrics.ready} filter="ready" tone="ready" />
        <Metric label="Total invoices" count={metrics.total_runs} filter="all" tone="total" />
        <Metric
          label="In progress"
          count={metrics.in_progress}
          filter="processing"
          tone="processing"
        />
      </div>
      <section className="distribution" aria-labelledby="distribution-title">
        <div className="distribution-main">
          <div className="section-heading">
            <h2 id="distribution-title">Decision distribution</h2>
            <span className="muted">{metrics.completed} completed</span>
          </div>
          {metrics.completed > 0 ? (
            <>
              <div className="distribution-bar" aria-hidden="true">
                {(
                  [
                    ['ready', metrics.ready],
                    ['review', metrics.review_required],
                    ['blocked', metrics.blocked],
                  ] as const
                ).map(([tone, count]) => (
                  <span key={tone} className={tone} style={{ flexGrow: count }} />
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
            <p>No completed decisions yet. Outcomes will appear after your first analysis.</p>
          )}
        </div>
        <div className="technical-counts">
          <Link to="/runs?status=failed">
            Processing failed <strong>{metrics.processing_failed}</strong>
          </Link>
          <Link to="/runs?status=interrupted">
            Interrupted <strong>{metrics.interrupted}</strong>
          </Link>
        </div>
      </section>
    </section>
  )
}
