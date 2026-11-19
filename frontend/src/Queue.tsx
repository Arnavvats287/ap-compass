import { useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { useRuns, active } from './queries'
import { Empty, ErrorState, Loading, RunTable, UploadPanel } from './components'
import type { RunSummary } from './types'

export const filters = [
  ['all', 'All'],
  ['ready', 'Ready'],
  ['review', 'Needs review'],
  ['blocked', 'Blocked'],
  ['processing', 'Processing'],
  ['failed', 'Failed'],
  ['interrupted', 'Interrupted'],
] as const
export function matches(run: RunSummary, filter: string, search: string) {
  const stateMatch =
    filter === 'ready'
      ? run.outcome === 'READY_FOR_AP'
      : filter === 'review'
        ? run.outcome === 'REVIEW_REQUIRED'
        : filter === 'blocked'
          ? run.outcome === 'BLOCKED'
          : filter === 'processing'
            ? active(run.execution_state)
            : filter === 'failed'
              ? run.execution_state === 'PROCESSING_FAILED'
              : filter === 'interrupted'
                ? run.execution_state === 'INTERRUPTED'
                : true
  return (
    stateMatch &&
    `${run.invoice_number ?? ''} ${run.vendor_name ?? ''}`
      .toLocaleLowerCase()
      .includes(search.trim().toLocaleLowerCase())
  )
}
export default function Queue() {
  const query = useRuns()
  const [params, setParams] = useSearchParams()
  const requested = params.get('status') ?? 'all'
  const status = filters.some(([key]) => key === requested) ? requested : 'all'
  const search = params.get('q') ?? ''
  const update = (key: string, value: string) =>
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous)
        if (value && value !== 'all') next.set(key, value)
        else next.delete(key)
        return next
      },
      { replace: true },
    )
  const rows = query.data?.filter((run) => matches(run, status, search)) ?? []
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Invoice Operations</h1>
          <p>Review the exception. Find the evidence. Move the invoice forward.</p>
        </div>
        <a className="button secondary" href="#upload">
          Process an invoice
        </a>
      </div>
      <section className="panel queue-panel" aria-labelledby="queue-title">
        <div className="queue-toolbar">
          <h2 id="queue-title">
            Invoice queue{' '}
            <span className="muted">
              {query.data ? `${rows.length} of ${query.data.length}` : '—'}
            </span>
          </h2>
          <div className="search-input">
            <Search size={18} aria-hidden="true" />
            <label className="sr-only" htmlFor="invoice-search">
              Search invoice or supplier
            </label>
            <input
              id="invoice-search"
              name="q"
              type="search"
              autoComplete="off"
              placeholder="Search invoice or supplier…"
              value={search}
              onChange={(e) => update('q', e.target.value)}
            />
          </div>
        </div>
        <div className="filters" aria-label="Filter invoices">
          {filters.map(([key, label]) => (
            <button
              key={key}
              className={status === key ? 'filter selected' : 'filter'}
              aria-pressed={status === key}
              onClick={() => update('status', key)}
            >
              {label}
            </button>
          ))}
        </div>
        {query.isPending ? (
          <Loading />
        ) : query.isError ? (
          <ErrorState retry={() => void query.refetch()} />
        ) : rows.length ? (
          <RunTable runs={rows} />
        ) : (
          <Empty
            filtered={!!query.data?.length}
            clear={query.data?.length ? () => setParams({}) : undefined}
          />
        )}
        <p className="table-note">
          Amounts are invoice totals including tax. Showing up to 100 recent runs; filters apply to
          this list.
        </p>
      </section>
      <UploadPanel compact />
    </>
  )
}
