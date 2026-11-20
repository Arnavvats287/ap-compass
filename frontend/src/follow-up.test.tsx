import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import FollowUpAction from './FollowUpAction'
import { followUpDrafts } from './follow-up'
import { finding, run } from './test/fixtures'
import type { Evidence, Finding, Run } from './types'

function ref(field: string, value: string, verified = true): Evidence {
  return {
    field,
    raw_value: value,
    normalized_value: value,
    page: 1,
    quote: value,
    route: verified ? 'native_text' : 'image_only',
    evidence_state: verified ? 'NATIVE_VERIFIED' : 'SOURCE_LOCATED_UNVERIFIED',
  }
}

const invoice = run.extracted_invoice!
const match = {
  ...finding,
  code: 'PO_MATCH_CONFIRMED',
  severity: 'PASS',
  owner: null,
  values: [{ name: 'po_id', value: invoice.po_reference }],
} satisfies Finding
const commitment = {
  ...finding,
  values: [...finding.values, { name: 'prior_billed_net', value: '175000' }],
}
const header = [
  ref('vendor_name_raw', invoice.vendor_name_raw!),
  ref('invoice_number', invoice.invoice_number!),
  ref('po_reference', invoice.po_reference!),
  ref('currency', invoice.currency!),
  ref('net', invoice.net!),
]
const sourceIssue = {
  ...finding,
  code: 'SOURCE_EVIDENCE_MISSING',
  severity: 'REVIEW',
  owner: 'AP',
  values: [],
} satisfies Finding

function recorded(primary: Finding, evidence: Evidence[], extra: Finding[] = []): Run {
  return {
    ...run,
    extracted_invoice: { ...invoice, evidence },
    decision: {
      ...run.decision!,
      outcome: primary.severity === 'BLOCK' ? 'BLOCKED' : 'REVIEW_REQUIRED',
      primary_reason_code: primary.code,
      owner: primary.owner,
      findings: [primary, match, ...extra],
    },
  }
}

describe('evidence-backed follow-up', () => {
  it('uses the Aster commitment finding internally and keeps the supplier draft free of internal ledger values', () => {
    const drafts = followUpDrafts(recorded(commitment, header))
    expect(drafts.defaultAudience).toBe('internal')
    expect(drafts.internal.body).toContain('₹25,000 remaining on PO PO-3015')
    expect(drafts.internal.body).toContain('₹1,75,000 previously billed')
    expect(drafts.internal.body).toContain('exceeds that commitment by ₹5,000')
    expect(drafts.supplier?.body).toContain('net amount of ₹30,000')
    expect(drafts.supplier?.body).not.toMatch(/25,000|1,75,000|5,000|PO-3015|commitment|blocked/i)
  })

  it('uses a clarification when a critical amount has missing, ambiguous, or mismatched evidence', () => {
    const withoutNet = header.filter((entry) => entry.field !== 'net')
    for (const netEvidence of [
      [],
      [ref('net', '30000', false)],
      [ref('net', '30001')],
      [ref('net', '30000'), ref('net', '30001')],
    ]) {
      const drafts = followUpDrafts(recorded(commitment, [...withoutNet, ...netEvidence]))
      expect(drafts.internal.body).toMatch(/verify the invoice net/i)
      expect(drafts.internal.body).not.toMatch(/₹|exceeds that commitment/)
    }
  })

  it('surfaces Kaveri’s verified line code and requests authorization clarification without asserting an unverified PO or amount', () => {
    const scope = { ...sourceIssue, code: 'LINE_MAPPING_UNRESOLVED', owner: 'Procurement' }
    const base = recorded(
      sourceIssue,
      [ref('lines[1].item_code', 'KL-YARD-08'), ref('lines[1].net', '2750')],
      [scope],
    )
    const kaveri: Run = {
      ...base,
      candidates: [
        {
          ...run.candidates[0],
          po: { ...run.candidates[0].po, lines: [{ item_code: 'KL-FREIGHT' }] },
        },
      ],
      extracted_invoice: {
        ...base.extracted_invoice!,
        vendor_name_raw: 'Kaveri Logistics',
        lines: [
          { ...invoice.lines[0], item_code: 'KL-FREIGHT' },
          {
            ...invoice.lines[0],
            item_code: 'KL-YARD-08',
            description: 'Yard waiting surcharge',
            net: '2750',
          },
        ],
      },
    }
    const drafts = followUpDrafts(kaveri)
    expect(drafts.internal.body).toMatch(
      /confirm the intended PO and whether item KL-YARD-08 can be matched to an approved PO line/,
    )
    expect(drafts.internal.body).not.toMatch(/2,750|PO-3015|unauthorized/)
    expect(drafts.supplier).toBeNull()
  })

  it('asks the supplier if an exact duplicate was reissued without exposing an unrelated billed record', () => {
    const duplicate = {
      ...finding,
      owner: 'Vendor',
      code: 'EXACT_DUPLICATE',
      values: [{ name: 'billed_record_id', value: 'BILLED-PRIVATE' }],
    }
    const drafts = followUpDrafts(recorded(duplicate, header))
    expect(drafts.defaultAudience).toBe('supplier')
    expect(drafts.internal.body).toContain('match an entry in the billed ledger')
    expect(drafts.supplier?.body).toContain('a reissue or a separate charge')
    expect(drafts.supplier?.body).not.toMatch(/BILLED-PRIVATE|billed ledger|already paid/i)
  })

  it('keeps a Meridian scan internal and neutral even if a PO and amounts were extracted', () => {
    const scan = { ...recorded(sourceIssue, header), source_route: 'image_only' }
    const drafts = followUpDrafts(scan)
    expect(drafts.supplier).toBeNull()
    expect(drafts.internal.subject).toBe('Invoice follow-up — clarification requested')
    expect(drafts.internal.body).toContain(
      'confirm the invoice details and supporting documentation',
    )
    expect(drafts.internal.body).not.toMatch(/PO-3015|exceeds|₹|page 1|OVERBILLED_PARTIAL/)
  })

  it('grounds price and quantity in the verified item and its recorded comparison', () => {
    const fields = [
      ...header,
      ref('lines[0].item_code', 'AS-SERVICE-01'),
      ref('lines[0].qty', '6'),
      ref('lines[0].unit_price_net', '5000'),
    ]
    const values = (items: Record<string, string>) =>
      Object.entries(items).map(([name, value]) => ({ name, value }))
    const price = {
      ...finding,
      code: 'PRICE_VARIANCE',
      values: values({ item_code: 'AS-SERVICE-01', invoice_price: '5000', po_price: '4800' }),
    }
    const quantity = {
      ...finding,
      code: 'PO_QUANTITY_EXCEEDED',
      values: values({
        item_code: 'AS-SERVICE-01',
        requested_qty: '6',
        remaining_qty: '5',
        excess_qty: '1',
      }),
    }
    expect(followUpDrafts(recorded(price, fields)).internal.body).toMatch(/₹5,000.*₹4,800/)
    const drafts = followUpDrafts(recorded(quantity, fields))
    expect(drafts.internal.body).toMatch(/total 6, against 5 remaining.*excess is 1/)
    expect(drafts.supplier?.body).not.toMatch(/remaining|excess|PO-3015/)
  })

  it('keeps unapproved supplier follow-up internal and asks for a missing PO without guessing it', () => {
    const supplier = followUpDrafts(recorded({ ...sourceIssue, code: 'VENDOR_UNVERIFIED' }, header))
    expect(supplier.internal.body).toMatch(/approved vendor record/)
    expect(supplier.supplier).toBeNull()
    const missing = followUpDrafts(
      recorded({ ...sourceIssue, code: 'PO_REFERENCE_MISSING' }, header.slice(0, 2)),
    )
    expect(missing.supplier?.body).toMatch(/confirm the applicable purchase order reference/)
    expect(missing.supplier?.body).not.toMatch(/PO-3015/)
  })

  it('copies the edited draft and restores focus to the trigger when the drawer closes', async () => {
    const user = userEvent.setup()
    render(<FollowUpAction run={recorded(commitment, header)} />)
    const modal = screen.getByRole<HTMLDialogElement>('dialog', { hidden: true })
    Object.assign(modal, {
      showModal: () => {
        modal.open = true
      },
      close: () => {
        modal.open = false
        modal.dispatchEvent(new Event('close'))
      },
    })
    const trigger = screen.getByRole('button', { name: 'Prepare follow-up' })
    await user.click(trigger)
    const drawer = within(screen.getByRole('dialog', { name: 'Prepare follow-up' }))
    expect(drawer.getByRole('radio', { name: 'Internal' })).toBeChecked()
    await user.click(drawer.getByRole('radio', { name: 'Supplier' }))
    const subject = drawer.getByRole('textbox', { name: 'Subject' })
    const message = drawer.getByRole('textbox', { name: 'Message' })
    await user.clear(subject)
    await user.type(subject, 'Edited subject')
    await user.clear(message)
    await user.type(message, 'Edited body')
    await user.click(drawer.getByRole('button', { name: 'Copy draft' }))
    expect(await navigator.clipboard.readText()).toBe('Subject: Edited subject\n\nEdited body')
    expect(drawer.getByRole('status')).toHaveTextContent('Draft copied.')
    await user.click(drawer.getByRole('button', { name: 'Close follow-up' }))
    expect(trigger).toHaveFocus()
  })

  it('offers only a copyable, evidence-backed handoff for Ready decisions', async () => {
    const user = userEvent.setup()
    const readyMatch = { ...match, values: [{ name: 'po_id', value: 'PO-6001' }] }
    const base = recorded(readyMatch, [
      ref('vendor_name_raw', 'Orion Office Products'),
      ref('invoice_number', 'HAPPY_CLEAN-2026'),
      ref('po_reference', 'PO-6001'),
      ref('currency', 'INR'),
      ref('net', '48000'),
      ref('total', '56640', false),
    ])
    render(
      <FollowUpAction
        run={{
          ...base,
          decision: { ...base.decision!, outcome: 'READY_FOR_AP', findings: [readyMatch] },
          candidates: [{ ...base.candidates[0], po: { ...base.candidates[0].po, id: 'PO-6001' } }],
          extracted_invoice: {
            ...base.extracted_invoice!,
            vendor_name_raw: 'Orion Office Products',
            invoice_number: 'HAPPY_CLEAN-2026',
            po_reference: 'PO-6001',
            net: '48000',
            tax: null,
            total: '56640',
          },
        }}
      />,
    )
    expect(screen.queryByRole('button', { name: 'Prepare follow-up' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Copy processing summary' }))
    const text = await navigator.clipboard.readText()
    expect(text).toMatch(/automated AP eligibility/)
    expect(text).toMatch(/Invoice: HAPPY_CLEAN-2026/)
    expect(text).toMatch(/Purchase order: PO-6001/)
    expect(text).toMatch(/Net: ₹48,000/)
    expect(text).not.toMatch(/Gross:|Tax:/)
    expect(text).toMatch(/does not authorize final approval, payment, posting or settlement/)
    expect(screen.getByRole('status')).toHaveTextContent('Processing summary copied.')
  })
})
