import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import Overview from './Overview'
import Queue from './Queue'
import Workspace, { Diagnostics, EvidenceList, FindingDetails, StageTimeline } from './Workspace'
import { UploadPanel, Status } from './components'
import { api, ApiError } from './api'
import { detailInterval, useRun } from './queries'
import { date, decimal, elapsed, money } from './format'
import { dashboard, finding, run, summary } from './test/fixtures'
import type { Run } from './types'

function renderPage(element: React.ReactNode, path = '/') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return {
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>{element}</MemoryRouter>
      </QueryClientProvider>,
    ),
    client,
  }
}
function defaults() {
  vi.spyOn(api, 'dashboard').mockResolvedValue(dashboard)
  vi.spyOn(api, 'runs').mockResolvedValue([summary])
  vi.spyOn(api, 'run').mockResolvedValue(run)
}

describe('connected operations views', () => {
  it('renders actual dashboard counts and defined net projection without invented metrics', async () => {
    defaults()
    renderPage(<Overview />)
    const metrics = await screen.findByRole('region', { name: 'Invoice operations counts' })
    expect(within(metrics).getByRole('link', { name: /Total invoices/ })).toHaveTextContent('17')
    expect(within(metrics).getByRole('link', { name: /Ready to process/ })).toHaveTextContent('6')
    expect(screen.getByRole('region', { name: 'Flagged invoice net value' })).toHaveTextContent(
      '₹1,23,456',
    )
    expect(screen.queryByText(/savings|hours saved|ROI|accuracy/i)).not.toBeInTheDocument()
    expect(screen.getByText(/Each analysis is counted/)).toBeInTheDocument()
  })
  it('has stable loading and actual empty dashboard states', async () => {
    vi.spyOn(api, 'dashboard').mockResolvedValue({
      ...dashboard,
      total_runs: 0,
      completed: 0,
      in_progress: 0,
      ready: 0,
      review_required: 0,
      blocked: 0,
    })
    vi.spyOn(api, 'runs').mockResolvedValue([])
    renderPage(<Overview />)
    expect(screen.getByText('Loading operations overview…')).toBeInTheDocument()
    expect(await screen.findByText('Your invoice queue starts here')).toBeInTheDocument()
    expect(screen.getByText(/No completed decisions yet/)).toBeInTheDocument()
  })
  it('renders API error and a real retry action', async () => {
    vi.spyOn(api, 'dashboard').mockRejectedValue(new ApiError(503))
    vi.spyOn(api, 'runs').mockResolvedValue([])
    renderPage(<Overview />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Invoice data is unavailable')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled()
  })
  it('renders READY, REVIEW and BLOCK statuses without computing a decision', async () => {
    vi.spyOn(api, 'runs').mockResolvedValue([
      summary,
      { ...summary, id: 'ready', invoice_number: 'READY-1', outcome: 'READY_FOR_AP' },
      { ...summary, id: 'review', invoice_number: 'REVIEW-1', outcome: 'REVIEW_REQUIRED' },
    ])
    renderPage(<Queue />, '/runs')
    const table = await screen.findByRole('table')
    expect(within(table).getByText('Ready to process')).toBeInTheDocument()
    expect(within(table).getByText('Needs review')).toBeInTheDocument()
    expect(within(table).getByText('Blocked')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'OVERBILLED_PARTIAL-2026' })).toHaveAttribute(
      'href',
      '/runs/test-run',
    )
  })
  it('keeps queue search/filter in URL and shows no matches honestly', async () => {
    defaults()
    renderPage(<Queue />, '/runs?status=ready&q=Aster')
    expect(await screen.findByText('No invoices match these filters')).toBeInTheDocument()
    expect(screen.getByRole('searchbox')).toHaveValue('Aster')
    expect(screen.getByRole('button', { name: 'Ready' })).toHaveAttribute('aria-pressed', 'true')
    await userEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(await screen.findByRole('link', { name: 'OVERBILLED_PARTIAL-2026' })).toBeInTheDocument()
  })
  it('uploads one PDF and navigates immediately to the returned workspace', async () => {
    vi.spyOn(api, 'upload').mockResolvedValue({ run_id: 'new-run', execution_state: 'QUEUED' })
    function Location() {
      return <p>{useLocation().pathname}</p>
    }
    renderPage(
      <Routes>
        <Route path="/" element={<UploadPanel />} />
        <Route path="/runs/:id" element={<Location />} />
      </Routes>,
    )
    const file = new File(['%PDF-test'], 'invoice.pdf', { type: 'application/pdf' })
    await userEvent.upload(screen.getByLabelText('Invoice PDF'), file)
    expect(screen.getByText('invoice.pdf')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Process invoice' }))
    expect(await screen.findByText('/runs/new-run')).toBeInTheDocument()
    expect(api.upload).toHaveBeenCalledWith(file)
  })
  it('shows genuine upload loading and prevents duplicate submission', async () => {
    let finish!: (v: { run_id: string; execution_state: 'QUEUED' }) => void
    vi.spyOn(api, 'upload').mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    renderPage(<UploadPanel />)
    await userEvent.upload(
      screen.getByLabelText('Invoice PDF'),
      new File(['%PDF-test'], 'invoice.pdf', { type: 'application/pdf' }),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Process invoice' }))
    expect(await screen.findByRole('button', { name: 'Uploading…' })).toBeDisabled()
    expect(api.upload).toHaveBeenCalledTimes(1)
    await act(async () => finish({ run_id: 'new-run', execution_state: 'QUEUED' }))
  })
  it('rejects oversized client input without a request', async () => {
    const upload = vi.spyOn(api, 'upload')
    renderPage(<UploadPanel />)
    await userEvent.upload(
      screen.getByLabelText('Invoice PDF'),
      new File([new Uint8Array(8 * 1024 * 1024 + 1)], 'large.pdf', { type: 'application/pdf' }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('exceeds 8 MiB')
    expect(upload).not.toHaveBeenCalled()
  })
  it('keeps server upload rejection visible and focused', async () => {
    vi.spyOn(api, 'upload').mockRejectedValue(new ApiError(415))
    renderPage(<UploadPanel />)
    await userEvent.upload(
      screen.getByLabelText('Invoice PDF'),
      new File(['%PDF-test'], 'invoice.pdf', { type: 'application/pdf' }),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Process invoice' }))
    const error = await screen.findByRole('alert')
    expect(error).toHaveTextContent('application/pdf')
    await waitFor(() => expect(error).toHaveFocus())
  })
  it('renders BLOCK owner/action and exact backend values', async () => {
    defaults()
    renderPage(
      <Routes>
        <Route path="/runs/:runId" element={<Workspace />} />
      </Routes>,
      '/runs/test-run',
    )
    expect(await screen.findByRole('heading', { name: 'Aster Systems' })).toBeInTheDocument()
    const brief = within(screen.getByRole('region', { name: finding.title }))
    expect(brief.getByText('Procurement', { exact: true })).toBeInTheDocument()
    expect(brief.getByText('₹25,000')).toBeInTheDocument()
    expect(brief.getByText('₹30,000')).toBeInTheDocument()
    expect(brief.getByText('₹5,000')).toBeInTheDocument()
    expect(brief.getByText(finding.next_action!)).toBeInTheDocument()
    expect(screen.getByTitle('Original invoice PDF')).toHaveAttribute(
      'src',
      '/api/runs/test-run/document#toolbar=0&view=FitH',
    )
  })
  it('keeps the primary resolution and evidence outside the optional audit disclosure', async () => {
    defaults()
    renderPage(
      <Routes>
        <Route path="/runs/:runId" element={<Workspace />} />
      </Routes>,
      '/runs/test-run',
    )
    await screen.findByRole('heading', { name: 'Aster Systems' })
    const audit = document.querySelector('.workspace-audit')!
    expect(audit).not.toHaveAttribute('open')
    expect(audit.contains(screen.getByRole('region', { name: finding.title }))).toBe(false)
    expect(audit.contains(document.querySelector('#evidence'))).toBe(false)
    expect(
      screen.getByRole('navigation', { name: 'Invoice workspace sections' }),
    ).toHaveTextContent('Recorded')
    expect(document.querySelector('#case-trace')).not.toBeNull()
    expect(document.querySelector('#case-policy')).not.toBeNull()
  })
  it('renders unknown future findings using supplied business content', () => {
    renderPage(
      <FindingDetails
        finding={{
          ...finding,
          code: 'FUTURE_CONTROL_42',
          title: 'New supplier control',
          explanation: 'A new backend rule requires Finance review.',
        }}
        currency="INR"
      />,
    )
    expect(screen.getByText('New supplier control')).toBeInTheDocument()
    expect(screen.getByText('FUTURE_CONTROL_42')).toBeInTheDocument()
    expect(screen.getByText('A new backend rule requires Finance review.')).toBeInTheDocument()
  })
  it('distinguishes verified, unverified and missing evidence language', () => {
    const reference = run.extracted_invoice!.evidence[0]
    renderPage(
      <EvidenceList
        evidence={[
          reference,
          {
            ...reference,
            field: 'tax',
            route: 'image_only',
            evidence_state: 'SOURCE_LOCATED_UNVERIFIED',
          },
          { ...reference, field: 'total', evidence_state: 'MISSING', quote: null, page: null },
        ]}
      />,
    )
    expect(screen.getByText('Source verified')).toBeInTheDocument()
    expect(screen.getByText('Source needs review')).toBeInTheDocument()
    expect(screen.getByText('Source not confirmed')).toBeInTheDocument()
    expect(
      screen.getByText(/image-based invoice and has not been independently text-verified/),
    ).toBeInTheDocument()
    expect(screen.getByText('Extraction reference, not verified source text')).toBeInTheDocument()
  })
  it('renders technical failure without a business rejection', async () => {
    defaults()
    vi.mocked(api.run).mockResolvedValue({
      ...run,
      execution_state: 'PROCESSING_FAILED',
      execution_error_code: 'PROVIDER_TIMEOUT',
      decision: null,
      extracted_invoice: null,
    })
    renderPage(
      <Routes>
        <Route path="/runs/:runId" element={<Workspace />} />
      </Routes>,
      '/runs/test-run',
    )
    expect(
      await screen.findByRole('heading', { name: 'Invoice processing failed' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/service timed out/)).toBeInTheDocument()
    expect(screen.queryByText('Blocked')).not.toBeInTheDocument()
    expect(screen.getByText(/No financial decision was produced/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Retry by uploading again' })).toHaveAttribute(
      'href',
      '/runs#upload',
    )
  })
  it('renders interruption without a produced decision', async () => {
    defaults()
    vi.mocked(api.run).mockResolvedValue({
      ...run,
      execution_state: 'INTERRUPTED',
      execution_error_code: 'SERVER_RESTART',
      decision: null,
    })
    renderPage(
      <Routes>
        <Route path="/runs/:runId" element={<Workspace />} />
      </Routes>,
      '/runs/test-run',
    )
    expect(
      await screen.findByRole('heading', { name: 'Processing was interrupted' }),
    ).toBeInTheDocument()
    expect(screen.queryByText('Blocked')).not.toBeInTheDocument()
  })
  it('leaves missing diagnostics unknown and displays reported zero honestly', () => {
    renderPage(
      <Diagnostics
        run={{
          ...run,
          usage: { model_calls: 0, input_tokens: null, output_tokens: null },
          model_id: null,
        }}
      />,
    )
    expect(screen.getAllByText('—').length).toBeGreaterThan(3)
    expect(screen.getByText('0', { exact: true })).toBeInTheDocument()
  })
  it('shows ambiguous candidate alternatives without selecting one', async () => {
    defaults()
    vi.mocked(api.run).mockResolvedValue({
      ...run,
      candidates: [
        run.candidates[0],
        { ...run.candidates[0], po: { ...run.candidates[0].po, id: 'PO-OTHER' } },
      ],
    })
    renderPage(
      <Routes>
        <Route path="/runs/:runId" element={<Workspace />} />
      </Routes>,
      '/runs/test-run',
    )
    expect(await screen.findByText(/Human confirmation required/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'PO-3015' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'PO-OTHER' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Confirm PO/i })).not.toBeInTheDocument()
  })
  it('uses persisted states for timeline, without predicting progress', () => {
    renderPage(
      <StageTimeline
        stages={[
          { ...run.stages[0], state: 'PASSED' },
          { ...run.stages[1], state: 'RUNNING', finished_at: null },
          { name: 'matching_records', state: 'QUEUED', started_at: null, finished_at: null },
        ]}
      />,
    )
    expect(screen.getByText('Running')).toBeInTheDocument()
    expect(screen.getByText('Waiting')).toBeInTheDocument()
    expect(screen.getByText('Complete')).toBeInTheDocument()
    expect(document.querySelectorAll('.spin')).toHaveLength(1)
    expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument()
  })
  it('keeps semantic navigation, skip link and mobile decision-before-source DOM order', async () => {
    defaults()
    renderPage(<App />, '/runs/test-run')
    await screen.findByRole('heading', { name: 'Aster Systems' })
    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Skip to main content' })).toHaveAttribute(
      'href',
      '#main',
    )
    expect(screen.queryByText('Foundation status')).not.toBeInTheDocument()
    const decision = document.querySelector('.decision-column')!
    const source = document.querySelector('.document-panel')!
    expect(decision.compareDocumentPosition(source) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
  it('renders ready confirmations only when supported and includes payment boundary', async () => {
    defaults()
    vi.mocked(api.run).mockResolvedValue({
      ...run,
      decision: {
        ...run.decision!,
        outcome: 'READY_FOR_AP',
        primary_reason_code: 'PO_MATCH_CONFIRMED',
        owner: null,
        next_action: null,
        findings: [
          {
            ...finding,
            severity: 'PASS',
            code: 'PO_MATCH_CONFIRMED',
            title: 'Purchase order identified',
          },
        ],
      },
    })
    renderPage(
      <Routes>
        <Route path="/runs/:runId" element={<Workspace />} />
      </Routes>,
      '/runs/test-run',
    )
    expect(await screen.findByText(/It does not authorize payment or posting/)).toBeInTheDocument()
    expect(screen.getByText('1 extracted field references source verified')).toBeInTheDocument()
    expect(screen.queryByText(/no known billed duplicate/i)).not.toBeInTheDocument()
  })
  it('renders run 404 and preserves a route back to history', async () => {
    defaults()
    vi.mocked(api.run).mockRejectedValue(new ApiError(404))
    renderPage(
      <Routes>
        <Route path="/runs/:runId" element={<Workspace />} />
      </Routes>,
      '/runs/missing',
    )
    expect(await screen.findByRole('heading', { name: 'Invoice not found' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open invoice queue' })).toBeInTheDocument()
  })
})

describe('polling and display invariants', () => {
  it('polls RUNNING, loads terminal decision and then stops automatic requests', async () => {
    const request = vi
      .spyOn(api, 'run')
      .mockResolvedValueOnce({ ...run, execution_state: 'RUNNING', decision: null })
      .mockResolvedValue(run)
    function Probe() {
      const query = useRun('test-run')
      return <p>{query.data?.execution_state ?? 'Loading'}</p>
    }
    renderPage(<Probe />)
    await screen.findByText('RUNNING')
    await screen.findByText('COMPLETED', {}, { timeout: 2500 })
    expect(request).toHaveBeenCalledTimes(2)
    // Wait beyond another poll window to prove the timer is disabled at terminal state.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 1100))
    })
    expect(request).toHaveBeenCalledTimes(2)
  })
  it.each(['COMPLETED', 'PROCESSING_FAILED', 'INTERRUPTED'] as const)(
    'does not schedule terminal %s polling',
    (state) => {
      expect(detailInterval(state)).toBe(false)
    },
  )
  it('uses a 1000ms interval for both queued and running states', () => {
    expect(detailInterval('QUEUED')).toBe(1000)
    expect(detailInterval('RUNNING')).toBe(1000)
  })
  it('formats decimal strings beyond Number precision without rounding them away', () => {
    expect(money('9007199254740993.123456', 'INR')).toBe('₹9,00,71,99,25,47,40,993.123456')
    expect(decimal('1234.5600')).toBe('1,234.56')
    expect(money(null, 'INR')).toBe('—')
    expect(money('0', 'INR')).toBe('₹0')
    expect(money('-0.25', 'INR')).toContain('0.25')
  })
  it('formats missing and actual zero elapsed time distinctly', () => {
    expect(elapsed(null)).toBe('—')
    expect(elapsed(0)).toBe('0 s')
    expect(date(null)).toBe('—')
  })
})

it('preserves identifier values and unknown future value strings verbatim', () => {
  renderPage(
    <FindingDetails
      finding={{
        ...finding,
        values: [
          { name: 'invoice_number', value: '000001' },
          { name: 'future_identifier', value: '000099' },
        ],
      }}
      currency="INR"
    />,
  )
  expect(screen.getByText('000001')).toBeInTheDocument()
  expect(screen.getByText('000099')).toBeInTheDocument()
})

it('shows scan arithmetic and source uncertainty as independent findings', async () => {
  defaults()
  const source = {
    ...finding,
    code: 'SOURCE_EVIDENCE_MISSING',
    severity: 'REVIEW' as const,
    title: 'Critical source evidence needs verification',
    explanation: 'Verify source fields',
    values: [],
  }
  const arithmetic = {
    ...finding,
    code: 'TOTAL_RECONCILIATION_FAILED',
    severity: 'REVIEW' as const,
    title: 'Invoice totals do not reconcile',
    explanation: 'The printed total differs from net plus tax.',
    values: [
      { name: 'expected_gross', value: '82600' },
      { name: 'stated_gross', value: '86200' },
      { name: 'difference', value: '3600' },
    ],
  }
  vi.mocked(api.run).mockResolvedValue({
    ...run,
    decision: {
      ...run.decision!,
      outcome: 'REVIEW_REQUIRED',
      primary_reason_code: source.code,
      findings: [source, arithmetic],
    },
  })
  renderPage(
    <Routes>
      <Route path="/runs/:runId" element={<Workspace />} />
    </Routes>,
    '/runs/test-run',
  )
  const brief = await screen.findByRole('region', { name: source.title })
  expect(within(brief).getByText('₹3,600')).toBeInTheDocument()
  expect(within(brief).getByText(/not been independently source verified/)).toBeInTheDocument()
  expect(within(brief).getByRole('heading', { name: arithmetic.title })).toBeInTheDocument()
})

it('accepts a dropped PDF with real selection feedback but does not auto-submit', () => {
  const upload = vi.spyOn(api, 'upload')
  renderPage(<UploadPanel />)
  const panel = screen.getByRole('region', { name: 'Process an invoice' })
  fireEvent.dragOver(panel)
  expect(panel).toHaveClass('dragging')
  fireEvent.drop(panel, {
    dataTransfer: { files: [new File(['%PDF-data'], 'dropped.pdf', { type: 'application/pdf' })] },
  })
  expect(screen.getByText('dropped.pdf')).toBeInTheDocument()
  expect(panel).not.toHaveClass('dragging')
  expect(screen.getByText('PDF, 9 B')).toBeInTheDocument()
  expect(upload).not.toHaveBeenCalled()
})

it('rejects multiple dropped files without accidentally keeping an older selection', () => {
  renderPage(<UploadPanel />)
  const panel = screen.getByRole('region', { name: 'Process an invoice' })
  const file = new File(['%PDF-data'], 'old.pdf', { type: 'application/pdf' })
  fireEvent.drop(panel, { dataTransfer: { files: [file] } })
  expect(screen.getByText('old.pdf')).toBeInTheDocument()
  fireEvent.drop(panel, { dataTransfer: { files: [file, file] } })
  expect(screen.getByRole('alert')).toHaveTextContent('one PDF at a time')
  expect(screen.queryByText('old.pdf')).not.toBeInTheDocument()
})

it('gives visible feedback when clipboard access is unavailable', async () => {
  defaults()
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: vi.fn().mockRejectedValue(new Error('TEST_ONLY denied')) },
    configurable: true,
  })
  renderPage(
    <Routes>
      <Route path="/runs/:runId" element={<Workspace />} />
    </Routes>,
    '/runs/test-run',
  )
  await screen.findByRole('heading', { name: 'Aster Systems' })
  await userEvent.click(screen.getByRole('button', { name: 'Copy link' }))
  expect(await screen.findByRole('button', { name: 'Copy unavailable' })).toBeInTheDocument()
  expect(
    screen.getByText('Copy is unavailable. Copy the address from your browser.'),
  ).not.toHaveClass('sr-only')
})
