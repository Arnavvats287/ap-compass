import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Search, Upload } from 'lucide-react'
import { useRuns, active } from './queries'
import { Empty, ErrorState, Loading, RunTable, UploadPanel } from './components'
import type { ExecutionState, Outcome, RunSummary } from './types'
import { isAttention, sortChoices, sortRuns } from './worklist'
import ExportInvoices from './ExportInvoices'

export const filters = [
  ['all', 'All'],
  ['attention', 'Needs attention'],
  ['ready', 'Ready'],
  ['review', 'Needs review'],
  ['blocked', 'Blocked'],
  ['processing', 'Processing'],
  ['failed', 'Failed'],
  ['interrupted', 'Interrupted'],
] as const
const outcomeFilters: Record<string, Outcome> = {
  ready: 'READY_FOR_AP',
  review: 'REVIEW_REQUIRED',
  blocked: 'BLOCKED',
}
const executionFilters: Record<string, ExecutionState> = {
  failed: 'PROCESSING_FAILED',
  interrupted: 'INTERRUPTED',
}
function matchesFilter(run: RunSummary, filter: string) {
  if (filter === 'attention') return isAttention(run)
  if (filter === 'processing') return active(run.execution_state)
  if (Object.hasOwn(outcomeFilters, filter)) return run.outcome === outcomeFilters[filter]
  if (Object.hasOwn(executionFilters, filter))
    return run.execution_state === executionFilters[filter]
  return true
}
export function matches(run: RunSummary, filter: string, search: string) {
  return (
    matchesFilter(run, filter) &&
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
  const urlSearch = params.get('q') ?? ''
  // Keep typing immediate while router navigation synchronizes the shareable URL.
  const [search, setSearch] = useState(urlSearch)
  useEffect(() => setSearch(urlSearch), [urlSearch])
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
  const vendor = params.get('vendor')
  const requestedSort = params.get('sort')
  const sort = sortChoices.find(([key]) => key === requestedSort)?.[0] ?? 'latest'
  const rows = sortRuns(
    query.data?.filter(
      (run) => (!vendor || run.vendor_name === vendor) && matches(run, status, search),
    ) ?? [],
    sort,
  )
  return (
    <div className="ops-page ops-queue">
      <div className="page-heading ops-heading">
        <div>
          <h1>Invoice Operations</h1>
          <p>Review the exception. Find the evidence. Move the invoice forward.</p>
        </div>
        <div className="ops-heading-actions">
          <Link className="button primary" to="/runs/upload">
            <Upload size={17} aria-hidden="true" /> Process invoices
          </Link>
          <ExportInvoices />
        </div>
      </div>
      <section className="panel queue-panel" aria-labelledby="queue-title">
        <div className="queue-toolbar">
          <h2 id="queue-title">
            Invoice queue{' '}
            <span className="muted">
              {query.data ? `${rows.length} of ${query.data.length}` : '—'}
            </span>
          </h2>
          <div className="ops-queue-controls">
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
                onChange={(e) => {
                  setSearch(e.target.value)
                  update('q', e.target.value)
                }}
              />
            </div>
            <label className="ops-sort">
              <span>Sort by</span>
              <select value={sort} onChange={(event) => update('sort', event.target.value)}>
                {sortChoices.map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        {vendor && (
          <div className="ops-vendor-filter">
            <span>Supplier: {vendor}</span>
            <button type="button" className="button secondary" onClick={() => update('vendor', '')}>
              Clear supplier
            </button>
          </div>
        )}
        <div className="filters" aria-label="Filter invoices">
          {filters.map(([key, label]) => (
            <button
              key={key}
              data-status={key}
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
          this list. Filters and overview counts use original automated decisions. Current
          human-reviewed assessments are labelled separately.
        </p>
      </section>
      <UploadPanel compact />
    </div>
  )
}
