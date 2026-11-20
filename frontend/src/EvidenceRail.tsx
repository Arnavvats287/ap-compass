import { ChevronLeft, ChevronRight, CircleHelp, ShieldCheck, TriangleAlert } from 'lucide-react'
import { useId, useRef, useState } from 'react'
import { unknown, words } from './format'
import type { Evidence } from './types'

const fieldLabels: Record<string, string> = {
  vendor_name_raw: 'Supplier',
  invoice_number: 'Invoice number',
  invoice_date: 'Invoice date',
  po_reference: 'PO reference',
  currency: 'Currency',
  net: 'Invoice net',
  tax: 'Tax',
  total: 'Invoice total',
}

function fieldName(field: string) {
  const line = /^lines\[(\d+)\]\.(.+)$/.exec(field)
  return (
    fieldLabels[field] ?? (line ? `Line ${Number(line[1]) + 1}: ${words(line[2])}` : words(field))
  )
}

function isIdentifier(field: string) {
  return field === 'invoice_number' || field === 'po_reference'
}

const states = {
  NATIVE_VERIFIED: { label: 'Source verified', tone: 'ready', Icon: ShieldCheck },
  SOURCE_LOCATED_UNVERIFIED: { label: 'Source needs review', tone: 'review', Icon: TriangleAlert },
  MISSING: { label: 'Source not confirmed', tone: 'missing', Icon: CircleHelp },
} as const

export default function EvidenceList({
  evidence,
  onShowPage,
}: {
  evidence: Evidence[]
  onShowPage?: (page: number) => void
}) {
  const id = useId()
  const [selectedIndex, setSelectedIndex] = useState(0)
  const rail = useRef<HTMLDivElement>(null)
  const index = Math.min(selectedIndex, evidence.length - 1)
  const ref = evidence[index]
  if (!ref) return <p>No source references are available. Verify the original invoice.</p>

  function select(next: number, focus = false) {
    if (next < 0 || next >= evidence.length) return
    setSelectedIndex(next)
    const container = rail.current
    const target = container?.children[next] as HTMLButtonElement | undefined
    if (!container || !target) return
    const bounds = container.getBoundingClientRect()
    const item = target.getBoundingClientRect()
    if (item.left < bounds.left || item.right > bounds.right) {
      container.scrollBy({ left: item.left - bounds.left })
    }
    if (focus) target.focus({ preventScroll: true })
  }

  return (
    <div className="evidence-browser">
      <div className="evidence-toolbar">
        <span aria-live="polite">
          Field {index + 1} of {evidence.length}
        </span>
        <div className="evidence-arrows">
          <button
            type="button"
            aria-label="Previous evidence field"
            disabled={index === 0}
            onClick={() => select(index - 1)}
          >
            <ChevronLeft size={19} aria-hidden />
          </button>
          <button
            type="button"
            aria-label="Next evidence field"
            disabled={index === evidence.length - 1}
            onClick={() => select(index + 1)}
          >
            <ChevronRight size={19} aria-hidden />
          </button>
        </div>
      </div>
      <div
        className="evidence-rail"
        ref={rail}
        role="group"
        aria-label="Evidence fields"
        onKeyDown={(event) => {
          const next = {
            ArrowRight: index + 1,
            ArrowLeft: index - 1,
            Home: 0,
            End: evidence.length - 1,
          }[event.key]
          if (next === undefined) return
          event.preventDefault()
          select(next, true)
        }}
      >
        {evidence.map((item, i) => {
          const { label, tone, Icon } = states[item.evidence_state]
          return (
            <button
              key={`${item.field}-${i}`}
              className="evidence-tile"
              type="button"
              aria-controls={id}
              aria-pressed={index === i}
              tabIndex={i === index ? 0 : -1}
              onClick={() => select(i)}
            >
              <span className={`evidence-tile-state is-${tone}`}>
                <Icon size={15} aria-hidden />
                {label}
              </span>
              <strong>{fieldName(item.field)}</strong>
              <span
                className={
                  isIdentifier(item.field)
                    ? 'evidence-tile-value invoice-reference'
                    : 'evidence-tile-value'
                }
              >
                {item.normalized_value ?? unknown}
              </span>
            </button>
          )
        })}
      </div>
      <div className="evidence-inspection" id={id} aria-label={fieldName(ref.field)} role="region">
        <div className="evidence-inspection-meta">
          <h3>{fieldName(ref.field)}</h3>
          <p className={isIdentifier(ref.field) ? 'invoice-reference' : undefined}>
            {ref.normalized_value ?? unknown}
          </p>
          {ref.page && onShowPage ? (
            <button
              className="button secondary"
              type="button"
              onClick={() => onShowPage(ref.page!)}
            >
              Show page {ref.page} in PDF
            </button>
          ) : (
            <small>{ref.page ? `Page ${ref.page}` : 'Page not located'}</small>
          )}
        </div>
        <div className="evidence-inspection-quote">
          {ref.evidence_state === 'NATIVE_VERIFIED' ? (
            <>
              <strong>Verified source text</strong>
              <blockquote>{ref.quote ?? unknown}</blockquote>
            </>
          ) : (
            <>
              <p>
                {ref.route === 'image_only' || ref.route === 'mixed'
                  ? 'The value was extracted from an image-based invoice and has not been independently text-verified.'
                  : 'This value has not been independently verified against the source text.'}
              </p>
              {ref.quote && (
                <>
                  <strong>Extraction reference, not verified source text</strong>
                  <blockquote>{ref.quote}</blockquote>
                </>
              )}
              {ref.normalized_value === null && ref.raw_value && (
                <p>
                  Unverified model claim: {ref.raw_value}. The document-stated value remains
                  unknown.
                </p>
              )}
            </>
          )}
          <small className="reason-code">{ref.field}</small>
        </div>
      </div>
    </div>
  )
}
