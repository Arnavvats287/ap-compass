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
    expect(within(metrics).getByRole('link', { name: /Total submissions/ })).toHaveTextContent('17')
    expect(within(metrics).getByRole('link', { name: /Ready to process/ })).toHaveTextContent('6')
    expect(screen.getByRole('region', { name: 'Flagged invoice net value' })).toHaveTextContent(
      '₹1,23,456',
    )
    expect(screen.queryByText(/savings|hours saved|ROI|accuracy/i)).not.toBeInTheDocument()
    expect(screen.getByText(/Each analysis is counted/)).toBeInTheDocument()
    expect(screen.getByText(/Counts reflect recorded automated decisions/)).toBeInTheDocument()
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
    expect(screen.getByText('No recorded exceptions')).toBeInTheDocument()
    expect(
      screen.getByText('No named vendors have recent recorded exceptions.'),
    ).toBeInTheDocument()
    expect(api.runs).toHaveBeenCalledTimes(1)
  })
  it('uses the exact server gross projection and labels missing and separate currency values', async () => {
    defaults()
    vi.spyOn(api, 'dashboard').mockResolvedValue({
      ...dashboard,
      invoice_gross: {
        submitted: { by_currency: { INR: '221545', USD: '7.25' }, missing_count: 1 },
        ready: { by_currency: { INR: '55460' }, missing_count: 0 },
        review_required: { by_currency: { INR: '118885' }, missing_count: 0 },
        blocked: { by_currency: {}, missing_count: 1 },
      },
    })
    renderPage(<Overview />)
    const financial = await screen.findByRole('region', { name: 'Financial overview' })
    const submitted = within(financial).getByRole('region', { name: 'Total submitted gross' })
    expect(submitted).toHaveTextContent('₹2,21,545')
    expect(submitted).toHaveTextContent('USD')
    expect(submitted).toHaveTextContent(/7\.25/)
    expect(submitted).toHaveTextContent('1 run excluded')
    expect(within(financial).getByRole('region', { name: 'Blocked gross' })).toHaveTextContent(
      'No recorded gross',
    )
    expect(within(financial).getByRole('region', { name: 'Review gross' })).toHaveTextContent(
      '₹1,18,885',
    )
  })
  it('loads only the prioritized blocked record for its actual next action', async () => {
    defaults()
    vi.spyOn(api, 'runs').mockResolvedValue([
      { ...summary, id: 'failure', outcome: null, execution_state: 'PROCESSING_FAILED' },
      {
        ...summary,
        id: 'newer-review',
        outcome: 'REVIEW_REQUIRED',
        updated_at: '2026-11-20T10:00:00Z',
      },
      summary,
      { ...summary, id: 'older-block', updated_at: '2026-11-17T10:00:00Z' },
    ])
    renderPage(<Overview />)
    const spotlight = await screen.findByRole('region', { name: 'Needs attention' })
    expect(await within(spotlight).findByText(finding.next_action!)).toBeInTheDocument()
    expect(within(spotlight).getByRole('link', { name: 'Review invoice' })).toHaveAttribute(
      'href',
      '/runs/test-run',
    )
    expect(api.run).toHaveBeenCalledExactlyOnceWith(summary.id, expect.anything())
    expect(within(spotlight).queryByText('Processing failed')).not.toBeInTheDocument()
  })
  it('shows exact per-currency attention gross and links both approved spellings', async () => {
    defaults()
    vi.spyOn(api, 'dashboard').mockResolvedValue({
      ...dashboard,
      vendor_attention: [
        {
          name: 'Meridian Cloud Pvt Ltd',
          source_names: ['Meridian Cloud Ltd.', 'Meridian Cloud Pvt Ltd'],
          review_count: 1,
          blocked_count: 2,
          gross_by_currency: { INR: '211.20', USD: '18.49' },
          missing_gross_count: 1,
        },
      ],
      procurement_capacity: [
        {
          po_id: 'PO-1042',
          vendor_name: 'Meridian Cloud Pvt Ltd',
          status: 'OPEN',
          currency: 'INR',
          approved_net: '200000',
          previously_billed_net: '120000',
          remaining_net: '80000',
        },
      ],
      exception_insights: [{ code: 'PO_BALANCE_EXCEEDED', count: 2 }],
    })
    renderPage(<Overview />)
    const table = await screen.findByRole('table', { name: /Top 10 vendors/ })
    expect(table).toHaveTextContent(/211\.2.*INR/)
    expect(table).toHaveTextContent(/18\.49.*USD/)
    expect(table).toHaveTextContent('1 missing gross or currency')
    const blocked = within(table).getByRole('link', { name: /2 blocked invoices/ })
    const search = new URL(blocked.getAttribute('href')!, 'http://localhost').searchParams
    expect(search.get('status')).toBe('blocked')
    expect(search.getAll('vendor')).toEqual(['Meridian Cloud Ltd.', 'Meridian Cloud Pvt Ltd'])
    expect(screen.getByRole('table', { name: 'Purchase order capacity' })).toHaveTextContent(
      '₹80,000',
    )
    expect(screen.getByRole('region', { name: 'Common exceptions' })).toHaveTextContent(
      'PO_BALANCE_EXCEEDED',
    )
  })
  it('includes each exact vendor spelling in a combined queue link', async () => {
    defaults()
    vi.spyOn(api, 'runs').mockResolvedValue([
      {
        ...summary,
        id: 'first',
        vendor_name: 'Meridian Cloud Ltd.',
        invoice_number: 'FIRST-EXCEPTION',
      },
      {
        ...summary,
        id: 'second',
        vendor_name: 'Meridian Cloud Pvt Ltd',
        invoice_number: 'SECOND-EXCEPTION',
      },
      {
        ...summary,
        id: 'unrelated',
        vendor_name: 'Unrelated vendor',
        invoice_number: 'OTHER-EXCEPTION',
      },
    ])
    renderPage(
      <Queue />,
      '/runs?status=attention&vendor=Meridian+Cloud+Ltd.&vendor=Meridian+Cloud+Pvt+Ltd',
    )
    expect(await screen.findByText('FIRST-EXCEPTION')).toBeInTheDocument()
    expect(screen.getByText('SECOND-EXCEPTION')).toBeInTheDocument()
    expect(screen.queryByText('OTHER-EXCEPTION')).not.toBeInTheDocument()
  })
  it('preserves separate flagged-net currency amounts', async () => {
    defaults()
    vi.spyOn(api, 'dashboard').mockResolvedValue({
      ...dashboard,
      flagged_invoice_net_by_currency: { INR: '1000.10', USD: '21.45' },
    })
    renderPage(<Overview />)
    const flagged = await screen.findByRole('region', { name: 'Flagged invoice net value' })
    expect(within(flagged).getByText('INR net')).toBeInTheDocument()
    expect(within(flagged).getByText(/1,000\.1/)).toBeInTheDocument()
    expect(within(flagged).getByText('USD net')).toBeInTheDocument()
    expect(within(flagged).getByText(/21\.45/)).toBeInTheDocument()
  })
  it('renders API error and a real retry action', async () => {
    vi.spyOn(api, 'dashboard').mockRejectedValue(new ApiError(503))
    vi.spyOn(api, 'runs').mockResolvedValue([])
    renderPage(<Overview />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Invoice data is unavailable')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled()
  })
  it('keeps a selected PDF when the dashboard finishes loading', async () => {
    defaults()
    let resolveDashboard!: (metrics: typeof dashboard) => void
    vi.spyOn(api, 'dashboard').mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveDashboard = resolve
        }),
    )
    renderPage(<Overview />)
    const file = new File(['%PDF-test'], 'invoice.pdf', { type: 'application/pdf' })
    await userEvent.upload(screen.getByLabelText('Invoice PDF'), file)
    expect(screen.getByText(file.name)).toBeInTheDocument()
    resolveDashboard(dashboard)
    await screen.findByRole('region', { name: 'Invoice operations counts' })
    expect(screen.getByText(file.name)).toBeInTheDocument()
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
    expect(screen.getByRole('button', { name: 'Needs attention' })).toHaveAccessibleDescription('2')
    await userEvent.click(screen.getByRole('button', { name: 'Needs attention' }))
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(screen.getByRole('button', { name: 'Needs attention' })).toHaveAttribute(
      'aria-pressed',
      'true',
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
  it('applies exact supplier filters and accessible sort choices to the loaded queue', async () => {
    vi.spyOn(api, 'runs').mockResolvedValue([
      summary,
      { ...summary, id: 'older', invoice_number: 'OLDER', updated_at: '2026-11-01T10:00:00Z' },
      { ...summary, id: 'other-vendor', vendor_name: summary.vendor_name + ' East' },
    ])
    renderPage(<Queue />, '/runs?status=attention&vendor=Aster+Systems')
    const table = await screen.findByRole('table')
    const firstRow = () => within(table).getAllByRole('row')[1]
    expect(firstRow()).toHaveTextContent(summary.invoice_number!)
    await userEvent.selectOptions(screen.getByLabelText('Sort by'), 'oldest')
    expect(firstRow()).toHaveTextContent('OLDER')
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    await userEvent.click(screen.getByRole('button', { name: 'Clear supplier' }))
    expect(within(table).getAllByRole('row')).toHaveLength(4)
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
    expect(document.querySelector('#case-decision')).toHaveTextContent('Recorded decision')
    const nav = within(screen.getByRole('navigation', { name: 'Invoice workspace sections' }))
    expect(nav.getByRole('link', { name: 'Run details' })).toHaveAttribute('href', '#case-details')
    await userEvent.click(nav.getByRole('button', { name: 'Collapse workspace sidebar' }))
    expect(nav.getByRole('button', { name: 'Expand workspace sidebar' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
    expect(nav.getByRole('link', { name: 'Source evidence' })).toHaveAttribute(
      'aria-label',
      'Source evidence',
    )
    expect(api.run).toHaveBeenCalledTimes(1)
    expect(document.querySelector('#case-trace')).not.toBeNull()
    expect(nav.queryByRole('link', { name: 'Policy impact' })).not.toBeInTheDocument()
    expect(document.querySelector('#case-policy')).toBeNull()
    for (const link of nav.getAllByRole('link')) {
      expect(document.querySelector(link.getAttribute('href')!)).toBeInTheDocument()
    }
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
  it('distinguishes source states and opens each reference with the keyboard', async () => {
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
    screen.getByRole('button', { name: /Source verified/ }).focus()
    await userEvent.keyboard('{ArrowRight}')
    expect(
      screen.getByText(/image-based invoice and has not been independently text-verified/),
    ).toBeInTheDocument()
    expect(screen.getByText('Extraction reference, not verified source text')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Source needs review/ })).toHaveFocus()
    await userEvent.keyboard('{End}')
    expect(screen.getByRole('button', { name: /Source not confirmed/ })).toHaveFocus()
    expect(screen.getByText('Page not located')).toBeInTheDocument()
  })
  it('loops through evidence, pauses on request, and lets the analyst restart it', () => {
    vi.useFakeTimers()
    vi.spyOn(document, 'hidden', 'get').mockReturnValue(false)
    const reference = run.extracted_invoice!.evidence[0]
    try {
      render(<EvidenceList evidence={[reference, { ...reference, field: 'tax' }]} />)
      expect(screen.getByText('Field 1 of 2')).toBeInTheDocument()
      act(() => vi.advanceTimersByTime(4000))
      expect(screen.getByText('Field 2 of 2')).toBeInTheDocument()
      const rail = screen.getByRole('group', { name: 'Evidence fields' })
      const scrollTo = vi.fn()
      Object.assign(rail, { scrollLeft: 500, scrollTo })
      act(() => vi.advanceTimersByTime(4000))
      expect(screen.getByText('Field 1 of 2')).toBeInTheDocument()
      expect(scrollTo).toHaveBeenCalledWith({ left: 0, behavior: 'instant' })

      fireEvent.click(screen.getByRole('button', { name: 'Pause evidence rotation' }))
      act(() => vi.advanceTimersByTime(8000))
      expect(screen.getByText('Field 1 of 2')).toBeInTheDocument()
      fireEvent.click(screen.getByRole('button', { name: 'Play evidence rotation' }))
      act(() => vi.advanceTimersByTime(4000))
      expect(screen.getByText('Field 2 of 2')).toBeInTheDocument()

      act(() => screen.getByRole('button', { name: /Source verified.*Tax/ }).focus())
      act(() => vi.advanceTimersByTime(4000))
      expect(screen.getByText('Field 2 of 2')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Play evidence rotation' })).toBeInTheDocument()
    } finally {
      vi.useRealTimers()
    }
  })
  it('keeps manual navigation available with reduced motion', () => {
    vi.useFakeTimers()
    vi.stubGlobal('matchMedia', () => ({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))
    const reference = run.extracted_invoice!.evidence[0]
    try {
      render(<EvidenceList evidence={[reference, { ...reference, field: 'tax' }]} />)
      act(() => vi.advanceTimersByTime(8000))
      expect(screen.getByText('Field 1 of 2')).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /evidence rotation/ })).not.toBeInTheDocument()
      fireEvent.click(screen.getByRole('button', { name: 'Next evidence field' }))
      expect(screen.getByText('Field 2 of 2')).toBeInTheDocument()
    } finally {
      vi.unstubAllGlobals()
      vi.useRealTimers()
    }
  })
  it('shows controlled provenance in Run details and keeps raw model wording out of the hero', async () => {
    defaults()
    vi.mocked(api.run).mockResolvedValue({ ...run, model_id: 'TEST_ONLY-rehearsal' })
    renderPage(
      <Routes>
        <Route path="/runs/:runId" element={<Workspace />} />
      </Routes>,
      '/runs/test-run',
    )
    await screen.findByRole('heading', { name: 'Aster Systems' })
    expect(document.querySelector('#case-decision')).not.toHaveTextContent('TEST_ONLY')
    const details = within(screen.getByRole('region', { name: 'Run details' }))
    expect(details.getByText('Demo run', { exact: false })).toBeInTheDocument()
    await userEvent.click(details.getByText('Run diagnostics'))
    expect(details.getByText(/made no live Gemini request/)).toBeVisible()
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
    expect(await screen.findByText(/original analysis returned alternatives/)).toBeInTheDocument()
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
    expect(
      await screen.findByText(/^This invoice passed the supported two-way controls\./),
    ).toBeInTheDocument()
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

it('opens a finding’s stored PDF page and selects its evidence field', async () => {
  defaults()
  const prior = run.extracted_invoice!.evidence[0]
  const evidence = {
    ...prior,
    field: 'lines[0].item_code',
    page: 2,
    quote: 'Item code: AS-SERVICE-01',
  }
  const findingWithSource = { ...finding, evidence_refs: [evidence] }
  vi.mocked(api.run).mockResolvedValue({
    ...run,
    extracted_invoice: { ...run.extracted_invoice!, evidence: [prior, evidence] },
    decision: { ...run.decision!, findings: [findingWithSource] },
  })
  renderPage(
    <Routes>
      <Route path="/runs/:runId" element={<Workspace />} />
    </Routes>,
    '/runs/test-run',
  )
  const decision = await screen.findByRole('region', { name: finding.title })
  const action = within(decision).getByRole('button', { name: 'Show source' })
  action.focus()
  await userEvent.keyboard('{Enter}')
  expect(screen.getByTitle('Original invoice PDF').getAttribute('src')).toContain('#page=2&')
  expect(
    screen.getByRole('button', { name: /Line 1: item code/i, pressed: true }),
  ).toBeInTheDocument()
  await waitFor(() => expect(screen.getByRole('region', { name: 'Source invoice' })).toHaveFocus())
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
  expect(within(brief).queryByRole('button', { name: /source/i })).not.toBeInTheDocument()
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
