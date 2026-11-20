import { decimal, money, unknown } from './format'
import type { Finding, Invoice, Run } from './types'

export type Audience = 'internal' | 'supplier'
type Draft = { subject: string; body: string }
type Message = { internal: string; supplier?: string; specific?: boolean }

const clean = (text?: string | null) => (text ?? '').replace(/[\s\p{Cc}\p{Cf}]+/gu, ' ').trim()
const identity = (text?: string | null) => clean(text).toLowerCase()
const isDecimal = (text: string) => /^-?\d+(?:\.\d+)?$/.test(text)

function verifiedText(
  invoice: Invoice | null,
  field: string,
  value?: string | null,
  numeric = false,
) {
  const text = clean(value)
  const refs = invoice?.evidence.filter((ref) => ref.field === field)
  if (!text || refs?.length !== 1) return null
  const [ref] = refs
  const recorded = clean(ref.normalized_value)
  if (
    ref.evidence_state !== 'NATIVE_VERIFIED' ||
    ref.route !== 'native_text' ||
    !ref.page ||
    !clean(ref.quote) ||
    !clean(ref.raw_value) ||
    !recorded
  )
    return null
  const matches = numeric
    ? isDecimal(text) && isDecimal(recorded) && decimal(text) === decimal(recorded)
    : identity(text) === identity(recorded)
  return matches ? text : null
}

function context(run: Run) {
  const invoice = run.source_route === 'image_only' ? null : run.extracted_invoice
  const get = (field: string, input?: string | null, numeric = false) =>
    verifiedText(invoice, field, input, numeric)
  const vendor = get('vendor_name_raw', invoice?.vendor_name_raw)
  const number = get('invoice_number', invoice?.invoice_number)
  const reportedCurrency = get('currency', invoice?.currency)
  const currency =
    reportedCurrency && /^[A-Za-z]{3}$/.test(reportedCurrency)
      ? reportedCurrency.toUpperCase()
      : null
  const po = get('po_reference', invoice?.po_reference)
  const poMatch = run.decision?.findings.find((finding) => finding.code === 'PO_MATCH_CONFIRMED')
  const matchedPO = run.candidates.find(
    (candidate) =>
      candidate.po.id === poMatch?.values.find((entry) => entry.name === 'po_id')?.value,
  )
  const funds = (value?: string | null) =>
    currency && value && isDecimal(value) ? money(value, currency) : unknown
  return { invoice, get, vendor, number, po, matchedPO, currency, funds }
}

const neutral: Message = {
  internal:
    'Please compare the original invoice with the procurement records, confirm the invoice details and supporting documentation, and advise what AP should do next.',
  supplier:
    'Could you confirm the invoice details and share a clear copy or supporting documents so we can continue our review?',
}

function exception(finding: Finding, run: Run, facts: ReturnType<typeof context>): Message {
  const { invoice, get, vendor, number, po, matchedPO, currency, funds } = facts
  const value = (name: string) => finding.values.find((entry) => entry.name === name)?.value
  const figures = (...names: string[]) => names.map((name) => funds(value(name)))
  const findings = run.decision?.findings ?? []
  const sameVendorPO = !findings.some((entry) =>
    ['VENDOR_PO_CONFLICT', 'VENDOR_UNVERIFIED'].includes(entry.code),
  )
  const confirmedPO =
    vendor && po && matchedPO && identity(matchedPO.po.id) === identity(po) && sameVendorPO
  const comparable =
    confirmedPO && currency && identity(matchedPO?.po.currency) === identity(currency)
  const item = value('item_code')
  const lines =
    invoice?.lines.map((line, index) => ({
      code: get(`lines[${index}].item_code`, line.item_code),
      qty: get(`lines[${index}].qty`, line.qty, true),
      price: get(`lines[${index}].unit_price_net`, line.unit_price_net, true),
      net: get(`lines[${index}].net`, line.net, true),
      recordedCode: line.item_code,
    })) ?? []
  const itemLines = item
    ? lines.filter((line) => identity(line.recordedCode) === identity(item))
    : []

  switch (finding.code) {
    case 'LINE_MAPPING_UNRESOLVED': {
      const approved = matchedPO?.po.lines
      const unmatched =
        approved?.length && sameVendorPO && finding.owner === 'Procurement'
          ? lines.filter(
              (line) =>
                line.code &&
                !approved.some((poLine) => identity(poLine.item_code) === identity(line.code)),
            )
          : []
      const line = unmatched.length === 1 ? unmatched[0] : null
      const amount = funds(line?.net)
      const charge = line
        ? `item ${line.code}${amount !== unknown ? ` (${amount} net)` : ''}`
        : 'the items in question'
      return {
        internal:
          line && confirmedPO
            ? `The recorded check could not match ${charge} to an approved line on PO ${po}. Please confirm whether the charge is authorized and advise AP on the next step.`
            : `Please confirm the intended PO and whether ${charge} can be matched to an approved PO line. Check the source invoice before AP proceeds.`,
        supplier: `Could you clarify ${charge} and share the related purchase order reference or supporting itemization?`,
        specific: Boolean(line),
      }
    }
    case 'PO_BALANCE_EXCEEDED': {
      const net = get('net', invoice?.net, true)
      const requested = value('requested_net')
      const [remaining, excess, prior] = figures('remaining_net', 'excess_net', 'prior_billed_net')
      if (
        comparable &&
        net &&
        requested &&
        isDecimal(requested) &&
        decimal(net) === decimal(requested) &&
        (!value('po_id') || value('po_id') === matchedPO?.po.id) &&
        remaining !== unknown &&
        excess !== unknown
      ) {
        return {
          internal: `The PDF-verified invoice net is ${funds(net)}. The recorded Procurement comparison shows ${remaining} remaining on PO ${po}${prior === unknown ? '' : ` after ${prior} previously billed`}. The invoice exceeds that commitment by ${excess}. Please review the available PO authorization and advise AP how to proceed.`,
          supplier: `Could you confirm the net amount of ${funds(net)} and provide the supporting itemization for this invoice?`,
          specific: true,
        }
      }
      return {
        internal:
          'The recorded check flagged a possible PO commitment issue. Please verify the invoice net, currency and PO against the source PDF and procurement records before concluding that the commitment was exceeded.',
        supplier: neutral.supplier,
      }
    }
    case 'PO_QUANTITY_EXCEEDED': {
      const requested = value('requested_qty')
      const remaining = value('remaining_qty')
      const excess = value('excess_qty')
      if (
        confirmedPO &&
        itemLines.length &&
        itemLines.every((line) => line.code && line.qty) &&
        requested &&
        remaining &&
        excess &&
        [requested, remaining, excess].every(isDecimal)
      ) {
        return {
          internal: `The PDF-verified quantities for ${item} total ${decimal(requested)}, against ${decimal(remaining)} remaining on PO ${po}. The recorded excess is ${decimal(excess)}. Please confirm the intended quantity and whether any PO amendment is authorized.`,
          supplier: `Could you confirm the invoiced quantity of ${decimal(requested)} for ${item} and share the supporting itemization?`,
          specific: true,
        }
      }
      return {
        internal:
          'Please confirm the invoice line quantities and remaining PO quantities before AP proceeds.',
        supplier: neutral.supplier,
      }
    }
    case 'PRICE_VARIANCE': {
      const rate = value('invoice_price')
      const poRate = funds(value('po_price'))
      const match =
        rate &&
        isDecimal(rate) &&
        itemLines.some((line) => line.code && line.price && decimal(line.price) === decimal(rate))
      if (comparable && match && poRate !== unknown) {
        const invoiceRate = funds(rate)
        const tolerance = value('tolerance_pct')
        return {
          internal: `The PDF-verified unit price for ${item} is ${invoiceRate}, compared with the recorded PO unit price of ${poRate}. The recorded comparison flagged a price variance${tolerance === '0.02' ? ' outside the 2% tolerance' : tolerance === '0.05' ? ' outside the 5% tolerance' : ''}. Please confirm the agreed rate and advise AP on the next step.`,
          supplier: `Could you confirm the invoiced unit price of ${invoiceRate} for ${item} and share the applicable pricing support?`,
          specific: true,
        }
      }
      return {
        internal:
          'Please verify the item code, unit price and currency against the PDF and confirm the agreed PO rate.',
        supplier: neutral.supplier,
      }
    }
    case 'EXACT_DUPLICATE':
    case 'POSSIBLE_DUPLICATE':
      return vendor && number
        ? {
            internal:
              finding.code === 'EXACT_DUPLICATE'
                ? 'The verified supplier and invoice number match an entry in the billed ledger. Please reconcile the two records and confirm whether the invoice was reissued.'
                : 'The recorded check found a possible duplicate. Please compare the billed record with the PDF and confirm whether this is a distinct charge.',
            supplier:
              'Could you confirm whether this invoice is a reissue or a separate charge? If it is a reissue, please clarify which copy we should use.',
            specific: true,
          }
        : {
            internal:
              'Please verify the supplier and invoice number against the original PDF and check the billed ledger for a possible duplicate.',
          }
    case 'PO_REFERENCE_MISSING':
    case 'PO_AMBIGUOUS':
    case 'PO_NOT_FOUND':
    case 'VENDOR_PO_CONFLICT':
      return {
        internal:
          'Please confirm the intended purchase order and its supplier against the procurement records before AP proceeds.',
        supplier:
          'Could you confirm the applicable purchase order reference and share any supporting documentation?',
      }
    case 'VENDOR_UNVERIFIED':
      return {
        internal:
          'Please confirm the invoice supplier against the approved vendor record and advise AP on the next step.',
      }
    case 'SOURCE_EVIDENCE_MISSING':
    case 'DOCUMENT_CONTENT_UNVERIFIED':
    case 'CRITICAL_FIELD_MISSING':
      return neutral
    default:
      return { internal: neutral.internal }
  }
}

export function followUpDrafts(run: Run) {
  const facts = context(run)
  const decision = run.decision
  const findings =
    decision?.findings.filter(
      (finding) => finding.severity === 'REVIEW' || finding.severity === 'BLOCK',
    ) ?? []
  const primary = findings.find((finding) => finding.code === decision?.primary_reason_code)
  const candidates = [primary, ...findings.filter((finding) => finding !== primary)].flatMap(
    (finding) => (finding ? [exception(finding, run, facts)] : []),
  )
  const message = candidates.find((candidate) => candidate.specific) ?? candidates[0] ?? neutral
  const { vendor, number } = facts
  const subject = number
    ? `Invoice ${number} — clarification requested`
    : 'Invoice follow-up — clarification requested'
  const invoice = number ? `invoice ${number}` : 'the invoice under review'
  const internal = {
    subject,
    body: `Hi team,\n\nCould you help with ${invoice}${vendor ? ` from ${vendor}` : ''}?\n\n${message.internal}\n\nThanks`,
  }
  const supplier: Draft | null =
    vendor && number && message.supplier
      ? {
          subject,
          body: `Hello,\n\nWe’re reviewing invoice ${number}. ${message.supplier}\n\nThank you`,
        }
      : null
  const owners = new Set(
    [decision?.owner, ...findings.map((finding) => finding.owner)].filter(Boolean).map(identity),
  )
  const defaultAudience: Audience =
    supplier && owners.size === 1 && (owners.has('vendor') || owners.has('supplier'))
      ? 'supplier'
      : 'internal'
  return { internal, supplier, defaultAudience }
}

export function processingSummary(run: Run) {
  const { invoice, get, vendor, number, po, matchedPO, currency, funds } = context(run)
  const lines = [
    'Recorded decision: Ready to process (automated AP eligibility).',
    vendor && `Supplier: ${vendor}`,
    number && `Invoice: ${number}`,
    po &&
      matchedPO &&
      identity(matchedPO.po.id) === identity(po) &&
      `Purchase order: ${po} (identified against procurement records)`,
  ]
  if (currency) {
    lines.push(`Currency: ${currency}`)
    for (const [field, label] of [
      ['net', 'Net'],
      ['tax', 'Tax'],
      ['total', 'Gross'],
    ] as const) {
      const amount = funds(get(field, invoice?.[field], true))
      if (amount !== unknown) lines.push(`${label}: ${amount}`)
    }
  }
  lines.push('This decision does not authorize final approval, payment, posting or settlement.')
  return lines.filter(Boolean).join('\n')
}

export function draftText(draft: Draft) {
  return `Subject: ${draft.subject}\n\n${draft.body}`
}
