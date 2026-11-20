import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { money, reasonLabel } from './format'
import type { Dashboard, VendorAttention } from './types'

function DashboardTable({
  title,
  columns,
  children,
}: {
  title: string
  columns: string[]
  children: ReactNode
}) {
  return (
    <table className="dashboard-table" aria-labelledby={title}>
      <thead>
        <tr>
          {columns.map((label) => (
            <th key={label} scope="col">
              {label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  )
}

function vendorFilter(vendor: VendorAttention, status: 'attention' | 'review' | 'blocked') {
  const params = new URLSearchParams({ status })
  for (const name of vendor.source_names) params.append('vendor', name)
  return '/runs?' + params.toString()
}

export function VendorAttentionTable({ rows }: { rows: VendorAttention[] }) {
  return (
    <section className="ops-card ops-vendors" aria-labelledby="vendors-title">
      <h2 id="vendors-title">Top 10 vendors needing attention</h2>
      <p>Latest 100 submissions · Recorded automated decisions · Gross by currency</p>
      {rows.length ? (
        <>
          <DashboardTable
            title="vendors-title"
            columns={['Vendor', 'Review', 'Blocked', 'Flagged gross']}
          >
            {rows.map((vendor) => (
              <tr key={vendor.source_names[0]}>
                <th scope="row">
                  <Link to={vendorFilter(vendor, 'attention')}>{vendor.name}</Link>
                </th>
                <td>
                  {vendor.review_count ? (
                    <Link
                      className="dashboard-count review"
                      aria-label={vendor.review_count + ' review invoices for ' + vendor.name}
                      to={vendorFilter(vendor, 'review')}
                    >
                      {vendor.review_count}
                    </Link>
                  ) : (
                    0
                  )}
                </td>
                <td>
                  {vendor.blocked_count ? (
                    <Link
                      className="dashboard-count blocked"
                      aria-label={vendor.blocked_count + ' blocked invoices for ' + vendor.name}
                      to={vendorFilter(vendor, 'blocked')}
                    >
                      {vendor.blocked_count}
                    </Link>
                  ) : (
                    0
                  )}
                </td>
                <td>
                  {Object.entries(vendor.gross_by_currency).map(([currency, amount]) => (
                    <span className="dashboard-amount" key={currency}>
                      {money(amount, currency)} <small>{currency}</small>
                    </span>
                  ))}
                  {!Object.keys(vendor.gross_by_currency).length && '—'}
                  {vendor.missing_gross_count > 0 && (
                    <small className="dashboard-meta">
                      {vendor.missing_gross_count} missing gross or currency
                    </small>
                  )}
                </td>
              </tr>
            ))}
          </DashboardTable>
          <p className="dashboard-meta">
            Ranked by attention count, then known gross within each currency. Repeat submissions
            count separately.
          </p>
        </>
      ) : (
        <p className="ops-chart-empty">No named vendors have recent recorded exceptions.</p>
      )}
    </section>
  )
}

export function ProcurementCapacity({ rows }: { rows: Dashboard['procurement_capacity'] }) {
  return (
    <section className="ops-card ops-capacity" aria-labelledby="capacity-title">
      <h2 id="capacity-title">Purchase order capacity</h2>
      <p>Procurement ledger · Net by PO currency</p>
      {rows.length ? (
        <DashboardTable
          title="capacity-title"
          columns={['Vendor / PO', 'Approved', 'Billed', 'Remaining']}
        >
          {rows.map((row) => (
            <tr key={row.po_id}>
              <th scope="row">
                {row.vendor_name}
                <small className="dashboard-meta">
                  {row.po_id} · {row.currency}
                  {row.status !== 'OPEN' && ' · ' + row.status}
                </small>
              </th>
              <td>{money(row.approved_net, row.currency)}</td>
              <td>{money(row.previously_billed_net, row.currency)}</td>
              <td>
                <strong>{money(row.remaining_net, row.currency)}</strong>
              </td>
            </tr>
          ))}
        </DashboardTable>
      ) : (
        <p className="ops-chart-empty">No purchase orders in the procurement ledger.</p>
      )}
      <p className="dashboard-meta">
        Remaining net deducts recorded prior billing only. Uploads and Ready invoices do not consume
        capacity.
      </p>
    </section>
  )
}

export function ExceptionInsights({ rows }: { rows: Dashboard['exception_insights'] }) {
  return (
    <section className="ops-card ops-insights" aria-labelledby="insights-title">
      <h2 id="insights-title">Common exceptions</h2>
      <p>Review and Block findings · Latest 100 submissions</p>
      {rows.length ? (
        <ul className="dashboard-findings">
          {rows.map(({ code, count }) => (
            <li key={code}>
              <span>
                <strong>{reasonLabel(code)}</strong>
                <small className="dashboard-meta">{code}</small>
              </span>
              <strong>{count}</strong>
            </li>
          ))}
        </ul>
      ) : (
        <p className="ops-chart-empty">No recent Review or Block findings.</p>
      )}
      <p className="dashboard-meta">
        Finding counts can overlap. One invoice may have multiple findings.
      </p>
    </section>
  )
}
