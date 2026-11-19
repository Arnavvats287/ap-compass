import {
  Check,
  ChevronDown,
  CirclePause,
  FileText,
  LoaderCircle,
  Search,
  ShieldCheck,
  TriangleAlert,
  X,
} from 'lucide-react'
import { Status } from './components'
import { date, elapsed, words } from './format'
import type { Run, Stage } from './types'

export const stageLabels: Record<string, string> = {
  received: 'Invoice received',
  extracting_invoice: 'Reading invoice',
  matching_records: 'Checking procurement',
  evaluating_controls: 'Running AP controls',
  finalizing: 'Preparing decision',
}
const completedLabels: Record<string, string> = {
  received: 'Invoice received',
  extracting_invoice: 'Invoice read',
  matching_records: 'Procurement checked',
  evaluating_controls: 'AP controls evaluated',
  finalizing: 'Decision prepared',
}
const explanations: Record<string, string> = {
  received: 'Store the accepted invoice for this run.',
  extracting_invoice:
    'Read invoice fields and locate supporting source evidence. Source uncertainty remains visible.',
  matching_records:
    'Resolve supplier and PO candidates against trusted procurement and billed history. Unresolved identities remain findings.',
  evaluating_controls:
    'Evaluate deterministic amount, quantity, duplicate, currency and policy controls.',
  finalizing: 'Persist the business decision, findings and exact policy snapshot.',
}
const states = {
  QUEUED: 'Waiting',
  RUNNING: 'Running',
  PASSED: 'Complete',
  WARNING: 'Attention',
  FAILED: 'Failed',
  SKIPPED: 'Skipped',
}
const icons = [FileText, FileText, Search, ShieldCheck, Check]
const timingNames: Record<string, string> = {
  extracting_invoice: 'extraction',
  matching_records: 'matching',
  evaluating_controls: 'evaluation',
  finalizing: 'finalizing',
}
function duration(stage: Stage, timings: Run['timings']) {
  const measured = timings.find((timing) => timing.name === timingNames[stage.name])?.milliseconds
  if (measured != null) return measured
  if (stage.started_at && stage.finished_at) {
    const value = Date.parse(stage.finished_at) - Date.parse(stage.started_at)
    if (Number.isFinite(value) && value >= 0) return value
  }
  return null
}
export function StageTimeline({
  stages,
  timings = [],
}: {
  stages: Stage[]
  timings?: Run['timings']
}) {
  return (
    <ol className="stage-timeline trace-nodes" aria-label="Persisted processing stages">
      {stages.map((stage, index) => {
        const milliseconds = duration(stage, timings)
        const Icon =
          stage.state === 'RUNNING'
            ? LoaderCircle
            : stage.state === 'PASSED'
              ? Check
              : stage.state === 'FAILED'
                ? X
                : stage.state === 'WARNING'
                  ? TriangleAlert
                  : (icons[index] ?? CirclePause)
        return (
          <li
            key={stage.name}
            className={`stage stage-${stage.state.toLowerCase()}`}
            aria-current={stage.state === 'RUNNING' ? 'step' : undefined}
          >
            <span className="trace-connector" aria-hidden="true">
              <span />
            </span>
            <details className="trace-node">
              <summary>
                <span className="trace-icon">
                  <Icon
                    size={17}
                    className={stage.state === 'RUNNING' ? 'spin' : ''}
                    aria-hidden="true"
                  />
                </span>
                <strong>
                  <span>
                    {(stage.state === 'PASSED'
                      ? completedLabels[stage.name]
                      : stageLabels[stage.name]) ?? words(stage.name)}
                  </span>
                  <ChevronDown size={12} aria-hidden="true" />
                </strong>
                <span className="trace-state">{states[stage.state]}</span>
                <span className="trace-duration">
                  {milliseconds != null && milliseconds < 1000
                    ? `${new Intl.NumberFormat('en-IN').format(milliseconds)} ms`
                    : elapsed(milliseconds)}
                </span>
              </summary>
              <div className="trace-explanation">
                <p>{explanations[stage.name] ?? 'Persisted backend operation.'}</p>
                {stage.started_at && (
                  <p>
                    Started <time dateTime={stage.started_at}>{date(stage.started_at, true)}</time>
                  </p>
                )}
                {stage.finished_at && (
                  <p>
                    Finished{' '}
                    <time dateTime={stage.finished_at}>{date(stage.finished_at, true)}</time>
                  </p>
                )}
              </div>
            </details>
          </li>
        )
      })}
    </ol>
  )
}
export default function DecisionTrace({ run }: { run: Run }) {
  const active = run.execution_state === 'QUEUED' || run.execution_state === 'RUNNING'
  return (
    <section
      className={`decision-trace ${active ? 'trace-live' : 'trace-terminal'}`}
      aria-label="Decision trace"
    >
      <div className="section-heading">
        <h2>Decision trace</h2>
        <span className="muted">{active ? 'Live execution' : 'Persisted execution'}</span>
      </div>
      {active && (
        <p>
          {explanations[run.stages.find((stage) => stage.state === 'RUNNING')?.name ?? ''] ??
            'Your invoice is stored and waiting for processing capacity.'}
        </p>
      )}
      <StageTimeline stages={run.stages} timings={run.timings} />
      {!active && (
        <div className="trace-outcome">
          <span>{run.decision ? 'Recorded business outcome' : 'No AP decision produced'}</span>
          <Status state={run.execution_state} outcome={run.decision?.outcome} />
          {run.decision && <small>Successful execution does not imply financial readiness.</small>}
        </div>
      )}
    </section>
  )
}
