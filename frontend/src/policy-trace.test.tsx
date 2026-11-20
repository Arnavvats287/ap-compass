import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import DecisionTrace, { StageTimeline } from './DecisionTrace'
import Workspace, { FindingValues } from './Workspace'
import { api } from './api'
import { run } from './test/fixtures'
import type { Run, Stage } from './types'

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

describe('recorded invoice policy', () => {
  it.each([
    ['0.02', 'Policy applied: 2% unit-price tolerance'],
    ['0.05', 'Policy applied: 5% unit-price tolerance'],
    [undefined, 'Applied unit-price tolerance unavailable'],
  ])(
    'only displays the stored tolerance %s alongside the recorded outcome',
    async (tolerance, label) => {
      vi.spyOn(api, 'run').mockResolvedValue({
        ...recorded,
        policy_snapshot: { version: 'persisted', price_tolerance_pct: tolerance },
      })
      const preview = vi.spyOn(api, 'preview')
      mount(
        <Routes>
          <Route path="/runs/:runId" element={<Workspace />} />
        </Routes>,
        '/runs/test-run',
      )
      const title = await screen.findByRole('heading', { name: 'Aster Systems' })
      const hero = title.closest('header')!
      expect(within(hero).getByText(label)).toBeInTheDocument()
      expect(within(hero).getByText('Blocked')).toBeInTheDocument()
      expect(screen.queryByRole('radio')).not.toBeInTheDocument()
      expect(screen.queryByText('Policy preview')).not.toBeInTheDocument()
      expect(preview).not.toHaveBeenCalled()
    },
  )
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
