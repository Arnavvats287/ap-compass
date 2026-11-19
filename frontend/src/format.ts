/** Display only. Financial decisions/calculations belong exclusively to the backend. */
export const unknown = '—'
export function decimal(value: string | null | undefined): string {
  if (value == null) return unknown
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value)
  if (!match) return value
  const fraction = match[3]?.replace(/0+$/, '')
  return `${match[1]}${new Intl.NumberFormat('en-IN').format(BigInt(match[2]))}${fraction ? '.' + fraction : ''}`
}
export function money(
  value: string | null | undefined,
  currency: string | null | undefined,
): string {
  if (value == null) return unknown
  if (!currency) return `${decimal(value)} (currency unknown)`
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value)
  if (!match) return unknown
  try {
    const integer = BigInt(match[2])
    const fraction = match[3]?.replace(/0+$/, '')
    const formatter = new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
    })
    const parts = formatter.formatToParts(match[1] ? -integer : integer)
    const lastInteger = parts.map((part) => part.type).lastIndexOf('integer')
    if (fraction)
      parts.splice(
        lastInteger + 1,
        0,
        { type: 'decimal', value: '.' },
        { type: 'fraction', value: fraction },
      )
    return `${match[1] && integer === 0n ? '−' : ''}${parts.map((part) => part.value).join('')}`
  } catch {
    return `${currency} ${decimal(value)}`
  }
}
export function date(value?: string | null, time = false): string {
  if (!value || Number.isNaN(Date.parse(value))) return unknown
  return new Intl.DateTimeFormat('en-IN', {
    dateStyle: 'medium',
    ...(time ? { timeStyle: 'short' } : { timeZone: 'UTC' }),
  }).format(new Date(value))
}
export function elapsed(ms?: number | null): string {
  return ms == null
    ? unknown
    : `${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(ms / 1000)} s`
}
export function relative(value: string): string {
  const difference = Date.parse(value) - Date.now()
  if (Number.isNaN(difference)) return unknown
  const unit =
    Math.abs(difference) < 3600000 ? 'minute' : Math.abs(difference) < 86400000 ? 'hour' : 'day'
  return new Intl.RelativeTimeFormat('en', { numeric: 'auto' }).format(
    Math.round(difference / { minute: 60000, hour: 3600000, day: 86400000 }[unit]),
    unit,
  )
}
export function words(code?: string | null): string {
  if (!code) return unknown
  const text = code.toLowerCase().replaceAll('_', ' ')
  return (text.charAt(0).toUpperCase() + text.slice(1)).replace(/\bpo\b/gi, 'PO')
}
export const valueLabels: Record<string, string> = {
  po_id: 'Purchase order',
  authorized_net: 'Authorized net',
  prior_billed_net: 'Previously billed net',
  remaining_net: 'Remaining PO net',
  requested_net: 'Invoice net',
  excess_net: 'Excess net',
  expected_gross: 'Net plus tax',
  stated_gross: 'Printed total',
  difference: 'Total discrepancy',
  remaining_qty: 'Remaining quantity',
  requested_qty: 'Invoice quantity',
  prior_billed_qty: 'Previously billed quantity',
  excess_qty: 'Excess quantity',
  item_code: 'Item code',
  fields: 'Fields requiring verification',
}

export function reasonLabel(code?: string | null): string {
  const labels: Record<string, string> = {
    PO_MATCH_CONFIRMED: 'Purchase order identified',
    PO_BALANCE_EXCEEDED: 'PO commitment exceeded',
    PO_QUANTITY_EXCEEDED: 'PO quantity exceeded',
    EXACT_DUPLICATE: 'Previously billed invoice',
    SOURCE_EVIDENCE_MISSING: 'Source evidence needs review',
    TOTAL_RECONCILIATION_FAILED: 'Invoice totals do not reconcile',
  }
  return code ? (labels[code] ?? words(code)) : unknown
}

export function fileSize(bytes: number): string {
  const unit = bytes < 1024 ? 'B' : bytes < 1024 * 1024 ? 'KiB' : 'MiB'
  const value = bytes / (unit === 'B' ? 1 : unit === 'KiB' ? 1024 : 1024 * 1024)
  return `${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(value)} ${unit}`
}
