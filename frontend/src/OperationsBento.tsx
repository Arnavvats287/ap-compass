import { useId } from 'react'
import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowDownToLine, ArrowUpRight, Check, CircleAlert, Files, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from './api'
import { ErrorState, UploadPanel } from './components'
import { money, reasonLabel } from './format'
import type { Dashboard, RunSummary } from './types'
import { attentionRuns, invoiceUrl } from './worklist'
import FinancialOverview from './FinancialOverview'
import { ExceptionInsights, ProcurementCapacity, VendorAttentionTable } from './DashboardTables'

import OverviewFocus from './OverviewFocus'
import DecisionRing from './DecisionRing'

const scope = 'Among the latest 100 invoices'

function Spotlight({
  metrics,
  runs,
  listState,
  retry,
  focused = false,
}: {
  metrics: Dashboard
  runs: RunSummary[]
  listState: 'pending' | 'error' | 'success'
  retry: () => void
  focused?: boolean
}) {
  const title = useId()
  const count = metrics.blocked + metrics.review_required
  const [priority, ...other] = attentionRuns(runs)
  const id = priority?.id ?? ''
  const detail = useQuery({
    queryKey: ['run', id],
    queryFn: ({ signal }) => api.run(id, signal),
    enabled: !!id,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnMount: !focused,
  })
  const decision = detail.data?.decision
  const finding = decision?.findings.find((entry) => entry.code === priority?.primary_reason_code)
  return (
    <section
      className="ops-spotlight ops-card"
      data-overview-section="attention"
      aria-labelledby={title}
      data-empty={!priority && listState === 'success'}
    >
      <div className="ops-spotlight-intro">
        <div>
          <span className="ops-kicker">
            <CircleAlert size={15} aria-hidden="true" /> Exceptions
          </span>
          <h2 id={title}>Needs attention</h2>
          <p>Recorded Review and Blocked invoices</p>
        </div>
        <span className="ops-signal" aria-label={count + ' invoices need attention'}>
          {count}
        </span>
      </div>
      {priority ? (
        <div className="ops-priority">
          <div className="ops-priority-meta">
            <span
              className={
                'ops-flag ' + (priority.outcome === 'BLOCKED' ? 'is-blocked' : 'is-review')
              }
            >
              {priority.outcome === 'BLOCKED' ? (
                <ShieldAlert size={14} aria-hidden="true" />
              ) : (
                <CircleAlert size={14} aria-hidden="true" />
              )}
              {priority.outcome === 'BLOCKED' ? 'Blocked' : 'Needs review'}
            </span>
            <span className="amount">
              {money(priority.total, priority.currency)}
              {priority.total != null && priority.currency && (
                <small>{priority.currency} gross</small>
              )}
            </span>
          </div>
          <h3>{finding?.title ?? reasonLabel(priority.primary_reason_code)}</h3>
          <p>
            {priority.vendor_name ?? 'Supplier unavailable'}
            {priority.invoice_number && ' · ' + priority.invoice_number}
          </p>
          <dl>
            <div>
              <dt>Owner</dt>
              <dd>{priority.owner ?? 'Unassigned'}</dd>
            </div>
            <div>
              <dt>Next action</dt>
              <dd aria-live="polite">
                {decision?.next_action ??
                  (detail.isPending
                    ? 'Loading recorded action…'
                    : 'Open the invoice for its assessment.')}
              </dd>
            </div>
          </dl>
          {priority.reviewed_outcome && <p>A human reassessment is available in the workspace.</p>}
          <Link className="ops-spotlight-action" to={invoiceUrl(priority.id)}>
            Review invoice <ArrowUpRight size={17} aria-hidden="true" />
          </Link>
        </div>
      ) : (
        <div className="ops-priority ops-priority-empty">
          {listState === 'pending' && <p role="status">Loading recent exceptions…</p>}
          {listState === 'error' && (
            <>
              <p role="status">Recent exceptions are unavailable.</p>
              <button className="ops-spotlight-action" onClick={retry}>
                Try again
              </button>
            </>
          )}
          {listState === 'success' && (
            <>
              {count ? (
                <CircleAlert size={24} aria-hidden="true" />
              ) : (
                <Check size={24} aria-hidden="true" />
              )}
              <h3>{count ? 'No exceptions in the recent list' : 'No recorded exceptions'}</h3>
              <p>
                {count
                  ? 'There are recorded exceptions outside the latest 100 invoices.'
                  : 'Invoices needing review or blocked by a control will appear here.'}
              </p>
            </>
          )}
        </div>
      )}
      <div className="ops-spotlight-footer">
        {other.length > 0 && (
          <ul aria-label="Other recent exceptions">
            {other.slice(0, 2).map((run) => (
              <li key={run.id}>
                <Link to={invoiceUrl(run.id)}>
                  <span>
                    <strong>{run.vendor_name ?? run.invoice_number ?? 'Invoice'}</strong>
                    <small>
                      {run.outcome === 'BLOCKED' ? 'Blocked' : 'Needs review'} ·{' '}
                      {reasonLabel(run.primary_reason_code)}
                    </small>
                  </span>
                  <ArrowUpRight size={16} aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ul>
        )}
        <span>{scope} · Blocked first, then newest updated</span>
      </div>
    </section>
  )
}

function Distribution({ metrics, focused = false }: { metrics: Dashboard; focused?: boolean }) {
  const title = useId()
  const outcomes = [
    ['ready', 'Ready', metrics.ready],
    ['review', 'Needs review', metrics.review_required],
    ['blocked', 'Blocked', metrics.blocked],
  ] as const
  return (
    <section
      className="ops-card ops-distribution"
      data-overview-section="distribution"
      aria-labelledby={title}
      data-empty={metrics.completed === 0}
    >
      <h2 id={title}>Decision distribution</h2>
      <p>Recorded automated outcomes</p>
      {focused && metrics.completed > 0 ? (
        <div className="ops-ring-chart">
          <DecisionRing segments={outcomes} />
          <div className="ops-ring-total">
            <strong className="ops-figure">{metrics.completed}</strong>
            <span className="ops-figure-label">Completed decisions</span>
          </div>
        </div>
      ) : (
        <>
          <strong className="ops-figure">{metrics.completed}</strong>
          <span className="ops-figure-label">Completed decisions</span>
          {metrics.completed > 0 ? (
            <div className="ops-outcome-bar" aria-hidden="true">
              {outcomes
                .filter(([, , count]) => count > 0)
                .map(([key, , count]) => (
                  <span key={key} className={key} style={{ flexGrow: count }} />
                ))}
            </div>
          ) : (
            <p className="ops-chart-empty">No completed decisions yet.</p>
          )}
        </>
      )}
      <ul className="ops-outcome-list">
        {outcomes.map(([key, label, count]) => (
          <li key={key}>
            <span>
              <i className={key} aria-hidden="true" />
              {label}
            </span>
            <strong>{count}</strong>
          </li>
        ))}
      </ul>
      <div className="ops-execution">
        <h3>Processing activity</h3>
        {(
          [
            ['processing', 'In progress', metrics.in_progress],
            ['failed', 'Processing failed', metrics.processing_failed],
            ['interrupted', 'Interrupted', metrics.interrupted],
          ] as const
        ).map(([key, label, count]) => (
          <Link key={key} to={'/runs?status=' + key}>
            {label} <strong>{count}</strong>
          </Link>
        ))}
      </div>
    </section>
  )
}

export default function OperationsBento({
  metrics,
  runs,
  listState,
  retry,
  recentActivity,
}: {
  metrics?: Dashboard
  runs: RunSummary[]
  listState: 'pending' | 'error' | 'success'
  retry: () => void
  recentActivity: ReactNode
}) {
  const counts =
    metrics &&
    ([
      ['all', 'Total invoices', metrics.total_runs, Files],
      ['ready', 'Ready to process', metrics.ready, Check],
      ['review', 'Needs review', metrics.review_required, CircleAlert],
      ['blocked', 'Blocked', metrics.blocked, ShieldAlert],
    ] as const)
  const values = Object.entries(metrics?.flagged_invoice_net_by_currency ?? {})
  const panels = {
    counts: counts && (
      <section
        data-overview-section="counts"
        className="ops-metrics"
        aria-label="Invoice operations counts"
      >
        {counts.map(([key, label, count, Icon]) => (
          <Link
            key={key}
            className={'ops-card ops-metric ' + key}
            to={key === 'all' ? '/runs' : '/runs?status=' + key}
          >
            <span className="ops-metric-icon">
              <Icon size={18} aria-hidden="true" />
            </span>
            <ArrowUpRight className="ops-metric-arrow" size={17} aria-hidden="true" />
            <strong>{count}</strong>
            <span>{label}</span>
          </Link>
        ))}
      </section>
    ),
    attention: metrics && (
      <Spotlight metrics={metrics} runs={runs} listState={listState} retry={retry} />
    ),
    distribution: metrics && <Distribution metrics={metrics} focused />,
    financial: metrics?.invoice_gross && <FinancialOverview gross={metrics.invoice_gross} />,
    vendors: metrics && <VendorAttentionTable rows={metrics.vendor_attention} />,
    capacity: metrics && <ProcurementCapacity rows={metrics.procurement_capacity} />,
    exceptions: metrics && <ExceptionInsights rows={metrics.exception_insights} />,
    flagged: metrics?.flagged_invoice_net_by_currency && (
      <section
        data-overview-section="flagged"
        className="ops-card ops-flagged"
        aria-label="Flagged invoice net value"
      >
        <h2>
          <ArrowDownToLine size={18} aria-hidden="true" /> Flagged invoice net
        </h2>
        <p>
          Known net from recorded Review and Blocked runs, grouped by currency. Each analysis is
          counted separately.
        </p>
        {values.length ? (
          <dl>
            {values.map(([currency, value]) => (
              <div key={currency}>
                <dt>{currency} net</dt>
                <dd className="amount">{money(value, currency)}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p>No flagged invoice value</p>
        )}
        {!!metrics.flagged_invoice_net_missing_count && (
          <small>
            {metrics.flagged_invoice_net_missing_count} run(s) excluded because net or currency is
            unknown.
          </small>
        )}
      </section>
    ),
    activity: recentActivity,
  }
  return (
    <OverviewFocus
      panels={{
        ...panels,
        attention: metrics && (
          <Spotlight metrics={metrics} runs={runs} listState={listState} retry={retry} focused />
        ),
      }}
    >
      {panels.counts}
      <div
        className={
          metrics?.invoice_gross
            ? 'ops-grid ops-grid-financial'
            : metrics
              ? 'ops-grid'
              : 'ops-grid ops-grid-fallback'
        }
      >
        {panels.attention}
        {metrics && <Distribution metrics={metrics} />}
        {panels.financial}
        {panels.vendors}
        {panels.capacity}
        {panels.exceptions}
        <div className="ops-support">
          <UploadPanel compact={!metrics} />
          {panels.flagged}
        </div>
      </div>
      <p className="queue-basis">
        Counts reflect recorded automated decisions. Human-reviewed assessments are labelled
        separately in the queue.
      </p>
      {panels.activity}
    </OverviewFocus>
  )
}
