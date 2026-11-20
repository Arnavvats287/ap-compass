import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import {
  Check,
  ChevronDown,
  CirclePause,
  FileText,
  LoaderCircle,
  RotateCcw,
  ScanText,
  Search,
  ShieldCheck,
  Stamp,
  TriangleAlert,
  X,
} from 'lucide-react'
import { Status, statusInfo } from './components'
import { ExceptionValues } from './FindingValues'
import { date, elapsed, words } from './format'
import { active } from './queries'
import type { Run, Stage } from './types'

export const stageLabels: Record<string, string> = {
  received: 'Invoice received',
  extracting_invoice: 'Reading invoice',
  matching_records: 'Checking procurement',
  evaluating_controls: 'Running AP controls',
  finalizing: 'Preparing decision',
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
const icons = [FileText, ScanText, Search, ShieldCheck, Stamp]
const timingNames: Record<string, string> = {
  extracting_invoice: 'extraction',
  matching_records: 'matching',
  evaluating_controls: 'evaluation',
  finalizing: 'finalizing',
}
function duration(stage: Stage, timings: Run['timings']) {
  const timing = timings.find((entry) => entry.name === timingNames[stage.name])?.milliseconds
  if (timing != null) return timing
  if (!stage.started_at || !stage.finished_at) return null
  const milliseconds = Date.parse(stage.finished_at) - Date.parse(stage.started_at)
  return Number.isFinite(milliseconds) && milliseconds >= 0 ? milliseconds : null
}
function stageContext(stage: Stage, run?: Run) {
  if (!run) return null
  const invoice = run.extracted_invoice
  const decision = run.decision
  if (stage.state === 'FAILED' && run.execution_error_code)
    return (
      <p>
        Recorded error <strong>{words(run.execution_error_code)}</strong>
      </p>
    )
  if (stage.state !== 'PASSED' && stage.state !== 'WARNING') return null
  if (stage.name === 'received')
    return (
      <p>
        Source PDF stored · Run <strong>{run.id.slice(0, 8)}</strong>
      </p>
    )
  if (stage.name === 'extracting_invoice' && invoice) {
    const verified = invoice.evidence.filter(
      (ref) => ref.evidence_state === 'NATIVE_VERIFIED',
    ).length
    return (
      <p>
        {words(run.source_route)} · {verified} of {invoice.evidence.length} evidence references
        native-verified.{' '}
        <a className="text-link" href="#evidence">
          View source evidence
        </a>
      </p>
    )
  }
  if (stage.name === 'matching_records')
    return (
      <p>
        Printed PO <strong>{invoice?.po_reference || 'Not supplied'}</strong> ·{' '}
        {run.candidates.length
          ? 'Recorded candidates: ' + run.candidates.map((candidate) => candidate.po.id).join(', ')
          : 'No recorded candidates'}
      </p>
    )
  if (stage.name === 'evaluating_controls' && decision) {
    const findings = decision.findings.filter(
      (finding) => finding.severity === 'BLOCK' || finding.severity === 'REVIEW',
    )
    return findings.length ? (
      <ul>
        {findings.map((finding, index) => (
          <li key={finding.code + index}>
            {finding.severity === 'BLOCK' ? 'Blocker' : 'Review'} · {finding.title}
          </li>
        ))}
      </ul>
    ) : (
      <p>{decision.findings.length} recorded control findings. No Block or Review findings.</p>
    )
  }
  if (stage.name === 'finalizing' && decision)
    return (
      <p>
        Recorded result <strong>{statusInfo[decision.outcome].label}</strong> · Policy{' '}
        {decision.policy_version}
      </p>
    )
  return null
}

export function StageTimeline({
  stages,
  timings = [],
  run,
  replay = 0,
}: {
  stages: Stage[]
  timings?: Run['timings']
  run?: Run
  replay?: number
}) {
  return (
    <ol className="trace-nodes journey-stages" aria-label="Persisted processing stages">
      {stages.map((stage, index) => {
        const milliseconds = duration(stage, timings)
        const Icon =
          stage.state === 'RUNNING'
            ? LoaderCircle
            : stage.state === 'FAILED'
              ? X
              : stage.state === 'WARNING'
                ? TriangleAlert
                : (icons[index] ?? CirclePause)
        return (
          <li
            key={stage.name}
            className={'journey-stage stage-' + stage.state.toLowerCase()}
            style={{ '--journey-step': index } as CSSProperties}
            aria-current={stage.state === 'RUNNING' ? 'step' : undefined}
          >
            <span className="journey-connector" aria-hidden="true">
              <span key={replay} />
            </span>
            <span className="journey-stage-icon" aria-hidden="true">
              <Icon size={19} className={stage.state === 'RUNNING' ? 'spin' : ''} />
            </span>
            <details className="trace-node journey-node">
              <summary>
                <strong>{stageLabels[stage.name] ?? words(stage.name)}</strong>
                <span className="journey-status">{states[stage.state]}</span>
                <span className="journey-duration">
                  {milliseconds != null && milliseconds < 1000
                    ? milliseconds + ' ms'
                    : elapsed(milliseconds)}
                </span>
                <ChevronDown size={16} className="journey-chevron" aria-hidden="true" />
              </summary>
              <div className="journey-details">
                <p>{explanations[stage.name] ?? 'Persisted backend operation.'}</p>
                {stageContext(stage, run)}
                {(stage.started_at || stage.finished_at) && (
                  <dl className="journey-times">
                    {stage.started_at && (
                      <div>
                        <dt>Started</dt>
                        <dd>
                          <time dateTime={stage.started_at}>{date(stage.started_at, true)}</time>
                        </dd>
                      </div>
                    )}
                    {stage.finished_at && (
                      <div>
                        <dt>Finished</dt>
                        <dd>
                          <time dateTime={stage.finished_at}>{date(stage.finished_at, true)}</time>
                        </dd>
                      </div>
                    )}
                  </dl>
                )}
              </div>
            </details>
          </li>
        )
      })}
    </ol>
  )
}

function ResultGlyph({ kind }: { kind: 'ready' | 'review' | 'blocked' | 'stopped' }) {
  return (
    <svg
      className="journey-glyph"
      viewBox="0 0 48 48"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {kind === 'ready' && (
        <>
          <circle className="journey-glyph-outline" cx="24" cy="24" r="19" pathLength="100" />
          <path className="journey-glyph-mark" d="m15 24 6 6 12-13" pathLength="100" />
        </>
      )}
      {kind === 'review' && (
        <>
          <path
            className="journey-glyph-outline"
            d="M13 39h22a6 6 0 0 0 5-9L29 10a6 6 0 0 0-10 0L8 30a6 6 0 0 0 5 9Z"
          />
          <path className="journey-glyph-mark" d="M24 18v8m0 6h.01" />
        </>
      )}
      {kind === 'blocked' && (
        <>
          <path className="journey-glyph-outline" d="m16 6 16 0 10 10v16L32 42H16L6 32V16Z" />
          <path className="journey-glyph-mark" d="M15 24h18" />
        </>
      )}
      {kind === 'stopped' && (
        <>
          <path className="journey-glyph-outline" d="M17 7H8v34h9m14-34h9v34h-9" />
          <path className="journey-glyph-mark" d="M20 16v16m8-16v16" />
        </>
      )}
    </svg>
  )
}

export default function DecisionTrace({ run }: { run: Run }) {
  const live = active(run.execution_state)
  const [replay, setReplay] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const firstNode = useRef<HTMLDivElement>(null)
  const resultIcon = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    const start = firstNode.current
    const end = resultIcon.current
    if (live || !start || !end || typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          if (entry.target === start) setReplay((current) => current || 1)
          if (entry.target === end) setRevealed(true)
          observer.unobserve(entry.target)
        }
      },
      { threshold: 0.2 },
    )
    observer.observe(start)
    observer.observe(end)
    return () => observer.disconnect()
  }, [live])

  const decision = run.decision
  const primary = decision?.findings.find(
    (finding) => finding.code === decision.primary_reason_code,
  )
  const kind =
    decision?.outcome === 'READY_FOR_AP'
      ? 'ready'
      : decision?.outcome === 'REVIEW_REQUIRED'
        ? 'review'
        : decision?.outcome === 'BLOCKED'
          ? 'blocked'
          : 'stopped'
  const liveStage = run.stages.find((stage) => stage.state === 'RUNNING')?.name
  return (
    <section
      className="decision-trace decision-journey"
      id="case-trace"
      tabIndex={-1}
      aria-labelledby="journey-title"
      data-replay={replay > 0 && !live}
    >
      <header className="journey-heading">
        <div>
          <h2 id="journey-title">Decision journey</h2>
          <p>{live ? 'Live execution by stage' : 'Recorded execution by stage'}</p>
        </div>
        {!live && (
          <button
            className="button secondary"
            type="button"
            onClick={() => setReplay((count) => count + 1)}
          >
            <RotateCcw size={17} aria-hidden="true" /> Replay journey
          </button>
        )}
      </header>
      <div className="journey-path">
        <div ref={firstNode}>
          <StageTimeline stages={run.stages} timings={run.timings} run={run} replay={replay} />
        </div>
        {live ? (
          <p className="journey-wait">
            <CirclePause size={18} aria-hidden="true" />
            {liveStage
              ? (stageLabels[liveStage] ?? words(liveStage))
              : 'Waiting for processing capacity'}
          </p>
        ) : (
          <div
            className={'journey-result journey-' + kind}
            style={{ '--journey-step': run.stages.length } as CSSProperties}
          >
            <span className="journey-result-icon" ref={resultIcon} data-reveal={revealed}>
              <ResultGlyph key={replay} kind={kind} />
            </span>
            <div className="journey-result-body">
              <div className="journey-result-top">
                <p>{decision ? 'Recorded business outcome' : 'No AP decision produced'}</p>
                <Status state={run.execution_state} outcome={decision?.outcome} />
              </div>
              <h3>
                {decision
                  ? kind === 'ready'
                    ? 'Two-way controls passed'
                    : (primary?.title ?? 'Invoice needs attention')
                  : 'Execution stopped'}
              </h3>
              {kind === 'ready' && (
                <p>Continue to AP review. Payment and posting require separate authorization.</p>
              )}
              {decision && kind !== 'ready' && (
                <>
                  {primary && kind === 'blocked' && primary.values.length > 0 && (
                    <ExceptionValues finding={primary} currency={run.extracted_invoice?.currency} />
                  )}
                  <dl className="journey-owner">
                    <div>
                      <dt>Owner</dt>
                      <dd>{decision.owner ?? primary?.owner ?? 'Unassigned'}</dd>
                    </div>
                    <div>
                      <dt>Next action</dt>
                      <dd>
                        {decision.next_action ??
                          primary?.next_action ??
                          'Review the recorded findings.'}
                      </dd>
                    </div>
                  </dl>
                </>
              )}
              {kind === 'stopped' && (
                <p>
                  {run.execution_error_code
                    ? 'Recorded technical error · ' + words(run.execution_error_code)
                    : 'The run ended before recording a financial outcome.'}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
