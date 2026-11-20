import { Link } from 'react-router-dom'
import { decimal, money, toleranceLabel, unknown, valueLabels, words } from './format'
import type { Finding } from './types'

export function FindingValues({
  finding,
  currency,
}: {
  finding: Finding
  currency?: string | null
}) {
  const isMoney = (name: string) =>
    name.endsWith('_net') ||
    ['expected_gross', 'stated_gross', 'difference', 'invoice_price', 'po_price'].includes(name)
  return finding.values.length ? (
    <dl className="finding-values">
      {finding.values.map((value, index) => (
        <div key={`${value.name}-${index}`}>
          <dt>{valueLabels[value.name] ?? words(value.name)}</dt>
          <dd className={isMoney(value.name) ? 'amount' : ''}>
            {value.value === null ? (
              unknown
            ) : value.name === 'prior_run_id' && finding.code === 'ALREADY_SUBMITTED' ? (
              <Link className="text-link" to={'/runs/' + encodeURIComponent(value.value)}>
                Open earlier invoice
              </Link>
            ) : isMoney(value.name) ? (
              money(value.value, currency)
            ) : value.name === 'tolerance_pct' ? (
              toleranceLabel(value.value)
            ) : value.name.endsWith('_qty') || value.name === 'qty' ? (
              decimal(value.value)
            ) : (
              value.value
            )}
          </dd>
        </div>
      ))}
    </dl>
  ) : null
}
/** Presentation only: emphasize existing backend comparison values; never calculate them. */
export function ExceptionValues({
  finding,
  currency,
}: {
  finding: Finding
  currency?: string | null
}) {
  const keys = ['remaining_net', 'requested_net', 'excess_net'].every((name) =>
    finding.values.some((value) => value.name === name),
  )
    ? ['remaining_net', 'requested_net', 'excess_net']
    : ['expected_gross', 'stated_gross', 'difference'].every((name) =>
          finding.values.some((value) => value.name === name),
        )
      ? ['expected_gross', 'stated_gross', 'difference']
      : []
  if (!keys.length) return <FindingValues finding={finding} currency={currency} />
  const comparison = keys.flatMap((name) => finding.values.filter((value) => value.name === name))
  const supporting = finding.values.filter((value) => !keys.includes(value.name))
  return (
    <>
      <div className="exception-comparison">
        <FindingValues finding={{ ...finding, values: comparison }} currency={currency} />
      </div>
      {supporting.length > 0 && (
        <div className="comparison-context">
          <FindingValues finding={{ ...finding, values: supporting }} currency={currency} />
        </div>
      )}
    </>
  )
}
