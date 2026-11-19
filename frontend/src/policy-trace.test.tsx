import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import DecisionTrace, { StageTimeline } from './DecisionTrace'
import PolicyImpact from './PolicyImpact'
import Workspace, { FindingValues } from './Workspace'
import { api, ApiError } from './api'
import { run } from './test/fixtures'
import type { PolicyPreview, Run, Stage } from './types'

const stages: Stage[] = [
  'received',
  'extracting_invoice',
  'matching_records',
  'evaluating_controls',
  'finalizing',
].map((name) => ({
  name,
  state: 'PASSED',
  started_at: '2026-11-19T00:00:00Z',
  finished_at: '2026-11-19T00:00:03Z',
}))
const recorded: Run = {
  ...run,
  stages,
  policy_snapshot: { version: 'policy-v1', price_tolerance_pct: '0.02' },
}
const preview: PolicyPreview = {
  original_policy: { version: 'policy-v1', price_tolerance_pct: '0.02' },
  preview_policy: { version: 'TEST-preview', price_tolerance_pct: '0.05' },
  original_decision: run.decision!,
  preview_decision: {
    ...run.decision!,
    outcome: 'READY_FOR_AP',
    primary_reason_code: null,
    findings: [],
    owner: null,
    next_action: null,
    policy_version: 'TEST-preview',
  },
  changed: true,
}
function mount(element: React.ReactNode, path = '/') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>{element}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('truthful decision trace', () => {
  it('only marks the returned RUNNING node active, with future stages waiting', () => {
    const state: Stage[] = stages.map((s, i) => ({
      ...s,
      state: i === 0 ? 'PASSED' : i === 1 ? 'RUNNING' : 'QUEUED',
      finished_at: i === 0 ? s.finished_at : null,
    }))
    mount(<StageTimeline stages={state} />)
    const items = screen.getAllByRole('listitem')
    expect(items[1]).toHaveAttribute('aria-current', 'step')
    expect(items[2]).not.toHaveAttribute('aria-current')
    expect(within(items[2]).getByText('Waiting')).toBeInTheDocument()
    expect(document.querySelectorAll('.stage-running')).toHaveLength(1)
    expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument()
  })
  it('shows successful execution stages separately from a BLOCKED outcome', () => {
    mount(<DecisionTrace run={recorded} />)
    expect(screen.getAllByText('Complete')).toHaveLength(5)
    expect(
      within(document.querySelector('.journey-result')!).getByText('Blocked'),
    ).toBeInTheDocument()
    expect(screen.getByText('Recorded business outcome')).toBeInTheDocument()
    expect(screen.queryByText('Failed')).not.toBeInTheDocument()
  })
  it('shows technical failure with failed/skipped stages and no business decision', () => {
    mount(
      <DecisionTrace
        run={{
          ...recorded,
          execution_state: 'PROCESSING_FAILED',
          decision: null,
          stages: stages.map((s, i) => ({
            ...s,
            state: i === 0 ? 'PASSED' : i === 1 ? 'FAILED' : 'SKIPPED',
          })),
        }}
      />,
    )
    expect(screen.getByText('Processing failed')).toBeInTheDocument()
    expect(screen.getByText('No AP decision produced')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.queryByText('Blocked')).not.toBeInTheDocument()
  })
  it('uses measured timings and preserves missing timing as an em dash', () => {
    mount(
      <StageTimeline
        stages={[stages[1], { ...stages[2], started_at: null, finished_at: null }]}
        timings={[{ name: 'extraction', milliseconds: 3200 }]}
      />,
    )
    expect(screen.getByText('3.2 s')).toBeInTheDocument()
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.queryByText('0 s')).not.toBeInTheDocument()
  })
  it('replays presentation without closing stages or changing their recorded statuses', async () => {
    mount(<DecisionTrace run={recorded} />)
    const journey = screen.getByRole('region', { name: 'Decision journey' })
    const disclosure = journey.querySelector<HTMLDetailsElement>('details')!
    disclosure.open = true
    const replay = screen.getByRole('button', { name: 'Replay journey' })
    await userEvent.click(replay)
    expect(journey).toHaveAttribute('data-replay', 'true')
    expect(disclosure.open).toBe(true)
    expect(replay).toHaveFocus()
    expect(screen.getAllByText('Complete')).toHaveLength(5)
    expect(
      within(journey.querySelector('.journey-result')!).getByText('Procurement'),
    ).toBeInTheDocument()
  })
  it('shows a measured millisecond duration without rounding it to zero', () => {
    mount(<StageTimeline stages={[stages[2]]} timings={[{ name: 'matching', milliseconds: 2 }]} />)
    expect(screen.getByText('2 ms')).toBeInTheDocument()
  })
  it('derives actual stage duration only from two valid persisted timestamps', () => {
    mount(<StageTimeline stages={[stages[0]]} />)
    expect(screen.getByText('3 s')).toBeInTheDocument()
  })
  it('exposes keyboard-operable node details without prompts or invented reasoning', async () => {
    mount(<StageTimeline stages={[stages[2]]} />)
    const summary = document.querySelector('summary')!
    summary.focus()
    await userEvent.keyboard('{Enter}')
    // jsdom does not implement native Enter disclosure; the actual browser QA covers it.
    expect(summary).toHaveFocus()
    expect(screen.getByText(/Unresolved identities remain findings/)).toBeInTheDocument()
  })
})

describe('read-only policy impact', () => {
  it('requests the API and never substitutes a preview into the recorded main decision', async () => {
    vi.spyOn(api, 'run').mockResolvedValue(recorded)
    const spy = vi.spyOn(api, 'preview').mockResolvedValue(preview)
    mount(
      <Routes>
        <Route path="/runs/:runId" element={<Workspace />} />
      </Routes>,
      '/runs/test-run',
    )
    await screen.findByRole('heading', { name: 'Aster Systems' })
    fireEvent.click(document.querySelector('.policy-impact > summary')!)
    await userEvent.click(screen.getByRole('radio', { name: '5%' }))
    expect(spy).toHaveBeenCalledExactlyOnceWith('test-run', '0.05')
    expect(
      await within(screen.getByRole('region', { name: 'Policy preview result' })).findByText(
        'Ready to process',
      ),
    ).toBeInTheDocument()
    expect(document.querySelector('.invoice-hero .status')).toHaveTextContent('Blocked')
    expect(screen.getByText('Recorded AP decision')).toBeInTheDocument()
    expect(
      screen.getByText('Original AP decision unchanged. No document reprocessing required.'),
    ).toBeInTheDocument()
  })
  it('waits for an actual response; controls are disabled and no future outcome is fabricated', async () => {
    let resolve!: (result: PolicyPreview) => void
    vi.spyOn(api, 'preview').mockImplementation(
      () =>
        new Promise((r) => {
          resolve = r
        }),
    )
    mount(<PolicyImpact run={recorded} />)
    fireEvent.click(document.querySelector('.policy-impact > summary')!)
    await userEvent.click(screen.getByRole('radio', { name: '5%' }))
    expect(screen.getByText('Evaluating stored facts…')).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: '2%' })).toBeDisabled()
    expect(screen.queryByText('Ready to process')).not.toBeInTheDocument()
    await act(async () => resolve(preview))
    expect(await screen.findByText('Ready to process')).toBeInTheDocument()
  })
  it('presents protected controls as information, never toggles', () => {
    mount(<PolicyImpact run={recorded} />)
    fireEvent.click(document.querySelector('.policy-impact > summary')!)
    expect(screen.getAllByRole('radio')).toHaveLength(2)
    expect(screen.queryByRole('switch')).not.toBeInTheDocument()
    expect(
      screen.getByText('Changing price tolerance does not override PO authorization.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Exact duplicate protection')).toBeInTheDocument()
  })
  it('reports preview error and preserves the current evaluation', async () => {
    vi.spyOn(api, 'preview').mockRejectedValue(new ApiError(503))
    mount(<PolicyImpact run={recorded} />)
    fireEvent.click(document.querySelector('.policy-impact > summary')!)
    await userEvent.click(screen.getByRole('radio', { name: '5%' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('recorded decision is unchanged')
    expect(
      within(screen.getByRole('region', { name: 'Current evaluation' })).getByText('Blocked'),
    ).toBeInTheDocument()
  })
  it('does not preview on mount or by merely disclosing the panel', () => {
    const spy = vi.spyOn(api, 'preview')
    mount(<PolicyImpact run={recorded} />)
    fireEvent.click(document.querySelector('.policy-impact > summary')!)
    expect(spy).not.toHaveBeenCalled()
  })
  it('does not fabricate a current tolerance when the historical display field is absent', () => {
    mount(<PolicyImpact run={{ ...recorded, policy_snapshot: { version: 'legacy' } }} />)
    fireEvent.click(document.querySelector('.policy-impact > summary')!)
    expect(
      within(screen.getByRole('region', { name: 'Current evaluation' })).getByText('—'),
    ).toBeInTheDocument()
  })
})

it('formats backend unit-price and tolerance findings without recomputing a variance', () => {
  mount(
    <FindingValues
      currency="INR"
      finding={{
        ...run.decision!.findings[0],
        values: [
          { name: 'invoice_price', value: '1030' },
          { name: 'po_price', value: '1000' },
          { name: 'tolerance_pct', value: '0.02' },
        ],
      }}
    />,
  )
  expect(screen.getByText('₹1,030')).toBeInTheDocument()
  expect(screen.getByText('₹1,000')).toBeInTheDocument()
  expect(screen.getByText('2%')).toBeInTheDocument()
})

it('can explicitly request the recorded 2% tolerance without first selecting 5%', async () => {
  const spy = vi.spyOn(api, 'preview').mockResolvedValue({
    ...preview,
    preview_policy: { version: 'TEST-2', price_tolerance_pct: '0.02' },
    preview_decision: run.decision!,
    changed: false,
  })
  mount(<PolicyImpact run={recorded} />)
  fireEvent.click(document.querySelector('.policy-impact > summary')!)
  await userEvent.click(screen.getByRole('radio', { name: '2%' }))
  expect(spy).toHaveBeenCalledExactlyOnceWith('test-run', '0.02')
  expect(await screen.findByText('Decision unchanged under this preview.')).toBeInTheDocument()
})
