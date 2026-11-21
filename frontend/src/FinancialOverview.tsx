import { useEffect, useId, useRef, useState } from 'react'
import { CircleAlert, CircleCheck, Files, ShieldAlert } from 'lucide-react'
import { money } from './format'
import type { Dashboard } from './types'

const cards = [
  ['submitted', 'Total submitted gross', Files],
  ['ready', 'Ready gross', CircleCheck],
  ['review_required', 'Review gross', CircleAlert],
  ['blocked', 'Blocked gross', ShieldAlert],
] as const

const countSteps = 1000
const countDuration = 440
const reducedMotion = '(prefers-reduced-motion: reduce)'

function countFrame(value: string, progress: number): string {
  const parts = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value)
  if (!parts) return value
  const [, sign, integer, fraction = ''] = parts
  const absolute = (BigInt(integer + fraction) * BigInt(progress)) / BigInt(countSteps)
  const digits = String(absolute).padStart(fraction.length + 1, '0')
  const prefix = absolute === 0n ? '' : sign
  return fraction
    ? prefix + digits.slice(0, -fraction.length) + '.' + digits.slice(-fraction.length)
    : prefix + digits
}

export default function FinancialOverview({
  gross,
  animate = false,
}: {
  gross: NonNullable<Dashboard['invoice_gross']>
  animate?: boolean
}) {
  const title = useId()
  const amountsGrid = useRef<HTMLDivElement>(null)
  const [progress, setProgress] = useState(() =>
    animate &&
    typeof IntersectionObserver !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    !window.matchMedia(reducedMotion).matches
      ? 0
      : countSteps,
  )

  useEffect(() => {
    const grid = amountsGrid.current
    if (
      !animate ||
      !grid ||
      typeof IntersectionObserver === 'undefined' ||
      typeof window.matchMedia !== 'function'
    )
      return
    const motion = window.matchMedia(reducedMotion)
    if (motion.matches) {
      setProgress(countSteps)
      return
    }

    let frame: number | undefined
    const finish = () => {
      observer.disconnect()
      if (frame !== undefined) cancelAnimationFrame(frame)
      setProgress(countSteps)
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return
        observer.disconnect()
        if (motion.matches) {
          finish()
          return
        }

        let started: number | undefined
        const tick = (now: number) => {
          started ??= now
          const elapsed = Math.min(1, (now - started) / countDuration)
          setProgress(Math.round(countSteps * (1 - (1 - elapsed) ** 2)))
          if (elapsed < 1) frame = requestAnimationFrame(tick)
        }
        frame = requestAnimationFrame(tick)
      },
      { rootMargin: '0px 0px -12% 0px' },
    )

    observer.observe(grid)
    motion.addEventListener('change', finish)
    return () => {
      observer.disconnect()
      if (frame !== undefined) cancelAnimationFrame(frame)
      motion.removeEventListener('change', finish)
    }
  }, [animate])

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
      <div className="financial-cards" ref={amountsGrid}>
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
                      <dd className="amount">
                        {progress === countSteps ? (
                          money(amount, currency)
                        ) : (
                          <>
                            <span className="sr-only">{money(amount, currency)}</span>
                            <span aria-hidden="true">
                              {money(countFrame(amount, progress), currency)}
                            </span>
                          </>
                        )}
                      </dd>
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
