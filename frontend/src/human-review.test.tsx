import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import HumanPOReview from './HumanPOReview'
import { api, ApiError } from './api'
import { run, summary } from './test/fixtures'
import { MemoryRouter } from 'react-router-dom'
import { RunTable } from './components'
import type { ReviewAction, ReviewHistory, Run } from './types'

const invoice: Run = {
  ...run,
  decision: { ...run.decision!, outcome: 'REVIEW_REQUIRED' },
  extracted_invoice: {
    ...run.extracted_invoice!,
    po_reference: null,
    vendor_name_raw: 'Meridian Cloud Ltd.',
  },
}
const candidate = (id: string) => ({
  po: { id, vendor_id: 'V-MER', status: 'OPEN', authorized_net: '200000', currency: 'INR' },
  selection_provenance: 'Canonical vendor V-MER; no financial eligibility filtering',
  rank: 1,
})
const history: ReviewHistory = {
  actions: [],
  current_reviewed_assessment: null,
  confirmation_available: true,
  unavailable_reason: null,
  candidates: [candidate('PO-1042'), candidate('PO-1057')],
  canonical_vendor_name: 'Meridian Cloud Pvt Ltd',
  authority_basis: 'Current authority; recorded policy',
}
const action: ReviewAction = {
  id: 'action-1',
  source_run_id: run.id,
  client_action_id: '12345678-1234-4234-8234-123456789012',
  action_type: 'CONFIRM_PO',
  selected_po_id: 'PO-1042',
  reviewer_label: 'Demo analyst',
  reviewer_identity: 'Demo reviewer — identity not authenticated',
  rationale: 'Checked with Procurement.',
  created_at: '2026-11-19T06:00:00Z',
  original_decision: invoice.decision!,
  reassessment: {
    ...run.decision!,
    outcome: 'READY_FOR_AP',
    findings: [],
    owner: null,
    next_action: 'Continue to AP review; no payment authority.',
  },
  policy_snapshot: { version: 'policy-v1', price_tolerance_pct: '0.02' },
  authority_fingerprint: 'a'.repeat(64),
  source_snapshot_fingerprint: 'b'.repeat(64),
  selection_provenance: 'Audited human selection',
  canonical_vendor_name: 'Meridian Cloud Pvt Ltd',
}
function mount(source = invoice) {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}
    >
      <HumanPOReview
        run={source}
        renderFinding={(finding) => (
          <p>
            {finding.title}: {finding.explanation}
          </p>
        )}
      />
    </QueryClientProvider>,
  )
}
async function open() {
  await userEvent.click(await screen.findByRole('button', { name: 'Review PO candidates' }))
}
async function fill() {
  await userEvent.click(screen.getByRole('radio', { name: /PO-1042/ }))
  await userEvent.type(screen.getByLabelText('Demo reviewer label'), 'Demo analyst')
  await userEvent.type(
    screen.getByLabelText('Reason for confirming this PO'),
    'Checked with Procurement.',
  )
}
// jsdom lacks native dialog methods; Chrome QA exercises the real modal/focus behavior.
for (const name of ['showModal', 'close'] as const) {
  if (!(name in HTMLDialogElement.prototype))
    Object.defineProperty(HTMLDialogElement.prototype, name, {
      configurable: true,
      writable: true,
      value() {},
    })
}
beforeEach(() => {
  vi.spyOn(HTMLDialogElement.prototype, 'showModal').mockImplementation(function (
    this: HTMLDialogElement,
  ) {
    this.setAttribute('open', '')
  })
  vi.spyOn(HTMLDialogElement.prototype, 'close').mockImplementation(function (
    this: HTMLDialogElement,
  ) {
    this.removeAttribute('open')
    this.dispatchEvent(new Event('close'))
  })
  vi.spyOn(api, 'reviewHistory').mockResolvedValue(history)
})
describe('audited PO resolution', () => {
  it('compares candidates without arbitrary selection and requires rationale', async () => {
    mount()
    await open()
    expect(screen.getAllByRole('radio')).toHaveLength(2)
    expect(screen.getByRole('radio', { name: /PO-1042/ })).not.toBeChecked()
    expect(screen.getAllByText(/identity not authenticated/).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: 'Confirm PO & re-evaluate' })).toBeDisabled()
    await userEvent.click(screen.getByRole('radio', { name: /PO-1042/ }))
    expect(screen.getByRole('button', { name: 'Confirm PO & re-evaluate' })).toBeDisabled()
    expect(
      screen.getByText(/Financial eligibility is checked separately after selection/),
    ).toBeInTheDocument()
  })
  it('saves once, waits for actual result and distinguishes original from reassessment', async () => {
    let finish!: (value: ReviewAction) => void
    const spy = vi.spyOn(api, 'confirmPO').mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    mount()
    await open()
    await fill()
    const button = screen.getByRole('button', { name: 'Confirm PO & re-evaluate' })
    await userEvent.dblClick(button)
    expect(spy).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Saving reassessment…' })).toBeDisabled()
    expect(screen.queryByText('Supported AP controls now pass.')).not.toBeInTheDocument()
    await act(async () => finish(action))
    const summary = await screen.findByRole('region', { name: 'PO confirmed manually' })
    expect(within(summary).getByText('PO-1042', { selector: 'p' })).toBeVisible()
    expect(within(summary).getByText('Supported AP controls now pass.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'PO confirmed manually' })).toHaveFocus()
    const reviewDetails = within(summary).getByText('Review details')
    expect(reviewDetails.closest('details')).not.toHaveAttribute('open')
    await userEvent.click(reviewDetails)
    expect(reviewDetails.closest('details')).toHaveAttribute('open')
    expect(
      await within(screen.getByRole('region', { name: 'Current reassessment' })).findByText(
        'Ready to process',
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: 'Original automated decision' })).getByText(
        'Needs review',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText(/does not authorize payment or posting/)).toBeInTheDocument()
  })
  it('keeps missing facts and still-not-ready outcome visible after saving', async () => {
    const revised = {
      ...action,
      reassessment: {
        ...action.original_decision,
        findings: [
          {
            ...run.decision!.findings[0],
            severity: 'REVIEW' as const,
            code: 'CRITICAL_FIELD_MISSING',
            title: 'Required invoice facts are missing',
            explanation: 'Line quantity and unit price remain unknown.',
          },
        ],
      },
    }
    vi.mocked(api.reviewHistory).mockResolvedValue({
      ...history,
      actions: [revised],
      current_reviewed_assessment: revised.reassessment,
      confirmation_available: false,
    })
    mount()
    const summary = await screen.findByRole('region', { name: 'PO confirmed manually' })
    expect(within(summary).getByRole('status')).toHaveTextContent(
      'Required invoice facts are missing',
    )
    expect(within(summary).getByText('Review details').closest('details')).not.toHaveAttribute(
      'open',
    )
    await userEvent.click(within(summary).getByText('Review details'))
    expect(screen.getByText(/Required invoice facts are missing:/)).toHaveTextContent(
      'Line quantity and unit price remain unknown',
    )
    expect(screen.queryByRole('button', { name: 'Review PO candidates' })).not.toBeInTheDocument()
  })
  it('handles safe conflict without inventing an assessment', async () => {
    vi.spyOn(api, 'confirmPO').mockRejectedValue(new ApiError(409))
    mount()
    await open()
    await fill()
    await userEvent.click(screen.getByRole('button', { name: 'Confirm PO & re-evaluate' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('confirmation may already exist')
    expect(screen.queryByRole('region', { name: 'Current reassessment' })).not.toBeInTheDocument()
  })
  it('retries uncertain network failure using the same idempotency key', async () => {
    const spy = vi.spyOn(api, 'confirmPO').mockRejectedValue(new Error('offline'))
    mount()
    await open()
    await fill()
    await userEvent.click(screen.getByRole('button', { name: 'Confirm PO & re-evaluate' }))
    await screen.findByRole('alert')
    await userEvent.click(screen.getByRole('button', { name: 'Confirm PO & re-evaluate' }))
    expect(spy).toHaveBeenCalledTimes(2)
    expect(spy.mock.calls[0][1]).toEqual(spy.mock.calls[1][1])
  })
  it('has keyboard-operable disclosure and returns focus on cancel', async () => {
    mount()
    const opener = await screen.findByRole('button', { name: 'Review PO candidates' })
    opener.focus()
    await userEvent.keyboard('{Enter}')
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(opener).toHaveFocus()
  })
  it('does not fetch or confirm an explicit-PO invoice', () => {
    const spy = vi.spyOn(api, 'confirmPO')
    mount(run)
    expect(api.reviewHistory).not.toHaveBeenCalled()
    expect(spy).not.toHaveBeenCalled()
  })
  it('does not confirm merely by opening the candidate dialog', async () => {
    const spy = vi.spyOn(api, 'confirmPO')
    mount()
    await open()
    expect(spy).not.toHaveBeenCalled()
  })
  it('shows history failure with a real reload action', async () => {
    vi.mocked(api.reviewHistory).mockRejectedValue(new ApiError(503))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'recorded automated decision is unchanged',
    )
    expect(screen.getByRole('button', { name: 'Reload review history' })).toBeEnabled()
  })
})

it('labels queue recorded and reviewed outcomes separately without changing the recorded outcome', () => {
  render(
    <MemoryRouter>
      <RunTable
        runs={[{ ...summary, outcome: 'REVIEW_REQUIRED', reviewed_outcome: 'READY_FOR_AP' }]}
      />
    </MemoryRouter>,
  )
  expect(screen.getByText('Original automated')).toBeInTheDocument()
  expect(screen.getByText('Current reviewed')).toBeInTheDocument()
  expect(screen.getByText('Needs review')).toBeInTheDocument()
  expect(screen.getByText('Ready to process')).toBeInTheDocument()
})
