import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowUpRight, CircleCheck, Search, ShieldAlert, TriangleAlert, Upload } from 'lucide-react'
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
const decisionTabs = [
  { key: 'attention', Icon: ArrowUpRight },
  { key: 'blocked', Icon: ShieldAlert },
  { key: 'review', Icon: TriangleAlert },
  { key: 'ready', Icon: CircleCheck },
] as const
const utilityFilters = filters.filter(([key]) => !decisionTabs.some((tab) => tab.key === key))
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
  const comparable = query.data?.filter(
    (run) => (!vendor || run.vendor_name === vendor) && matches(run, 'all', search),
  )
  const rows = sortRuns(comparable?.filter((run) => matchesFilter(run, status)) ?? [], sort)
  return (
    <div className="ops-page ops-queue">
      <div className="page-heading ops-heading operations-heading">
        <div>
          <h1>Invoice Operations</h1>
          <p>Review decisions and find the next action.</p>
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
          <div className="operations-queue-heading">
            <h2 id="queue-title">Invoice queue</h2>
            {query.data && (
              <span role="status">
                {rows.length} of {query.data.length} invoices shown
              </span>
            )}
          </div>
          <div className="operations-decisions" role="group" aria-label="Filter recorded decisions">
            {decisionTabs.map(({ key, Icon }) => {
              const label = filters.find(([value]) => value === key)?.[1]
              const count =
                !query.isError && comparable?.filter((run) => matchesFilter(run, key)).length
              return (
                <button
                  key={key}
                  type="button"
                  aria-label={label}
                  aria-describedby={`operations-count-${key}`}
                  aria-pressed={status === key}
                  className="operations-decision"
                  data-outcome={key}
                  onClick={() => update('status', key)}
                >
                  <span className="operations-decision-label">
                    <Icon size={18} aria-hidden="true" /> {label}
                  </span>
                  <strong id={`operations-count-${key}`}>
                    {typeof count === 'number' ? count : '—'}
                  </strong>
                </button>
              )
            })}
          </div>
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
                placeholder="Search invoices or suppliers…"
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
        <div className="filters operations-filters" aria-label="Filter by intake status">
          {utilityFilters.map(([key, label]) => (
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
          Latest 100 runs. Amounts include tax. Decision filters use the recorded automated outcome.
          Reviewed assessments are labeled separately.
        </p>
      </section>
      <UploadPanel compact />
    </div>
  )
}
