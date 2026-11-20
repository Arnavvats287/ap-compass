import { useId } from 'react'
import { CircleAlert, CircleCheck, Files, ShieldAlert } from 'lucide-react'
import { money } from './format'
import type { Dashboard } from './types'

const cards = [
  ['submitted', 'Total submitted gross', Files],
  ['ready', 'Ready gross', CircleCheck],
  ['review_required', 'Review gross', CircleAlert],
  ['blocked', 'Blocked gross', ShieldAlert],
] as const

export default function FinancialOverview({
  gross,
}: {
  gross: NonNullable<Dashboard['invoice_gross']>
}) {
  const title = useId()
  return (
    <section
      className="financial-overview ops-card"
      data-overview-section="financial"
      aria-labelledby={title}
    >
      <h2 id={title}>Financial overview</h2>
      <p>
        Gross including tax, across all stored submissions. Repeat submissions and duplicates are
        included. Decision totals use recorded automated outcomes.
      </p>
      <div className="financial-cards">
        {cards.map(([key, title, Icon]) => {
          const projection = gross[key]
          const amounts = Object.entries(projection.by_currency)
          return (
            <section className={'financial-card financial-' + key} key={key} aria-label={title}>
              <h3>
                <Icon size={17} aria-hidden="true" />
                {title}
              </h3>
              {amounts.length ? (
                <dl>
                  {amounts.map(([currency, amount]) => (
                    <div key={currency}>
                      <dt>{currency}</dt>
                      <dd className="amount">{money(amount, currency)}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p>No recorded gross</p>
              )}
              {projection.missing_count > 0 && (
                <small>
                  {projection.missing_count}{' '}
                  {projection.missing_count === 1 ? 'run excluded' : 'runs excluded'} · gross or
                  currency unavailable
                </small>
              )}
            </section>
          )
        })}
      </div>
    </section>
  )
}
