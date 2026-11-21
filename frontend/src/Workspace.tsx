import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowUpRight,
  Check,
  CircleCheck,
  Copy,
  FileText,
  FlaskConical,
  ShieldCheck,
  TriangleAlert,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { ApiError, api } from './api'
import { active, useRun } from './queries'
import { ErrorState, Loading, Status, statusInfo } from './components'
import { date, elapsed, money, toleranceLabel, unknown, words } from './format'
import DecisionTrace, { stageLabels } from './DecisionTrace'
import { ExceptionValues, FindingValues } from './FindingValues'
import HumanPOReview from './HumanPOReview'
import FollowUpAction from './FollowUpAction'
export { StageTimeline } from './DecisionTrace'
import EvidenceList from './EvidenceRail'
import WorkspaceNavigation from './WorkspaceNavigation'
import WorkspaceFocusSection from './WorkspaceFocusSection'
import FocusDialog from './FocusDialog'
import type { Evidence, Finding, Run } from './types'
export { default as EvidenceList } from './EvidenceRail'

export { FindingValues } from './FindingValues'

type ShowFindingSource = (reference: Evidence, trigger: HTMLButtonElement) => void

function FindingSource({
  finding,
  onShowSource,
}: {
  finding: Finding
  onShowSource?: ShowFindingSource
}) {
  const located = finding.evidence_refs.find(
    (ref) => ref.page && ref.page > 0 && ref.evidence_state === 'NATIVE_VERIFIED',
  )
  if (!located || !onShowSource) return null
  return (
    <button
      className="button secondary finding-source-action"
      type="button"
      aria-haspopup="dialog"
      onClick={(event) => onShowSource(located, event.currentTarget)}
    >
      <FileText size={16} aria-hidden="true" />
      Show source
    </button>
  )
}

export function FindingDetails({
  finding,
  currency,
  onShowSource,
}: {
  finding: Finding
  currency?: string | null
  onShowSource?: ShowFindingSource
}) {
  return (
    <details className="finding-disclosure">
      <summary>
        <span className={`severity-icon severity-${finding.severity.toLowerCase()}`}>
          {finding.severity === 'PASS' ? (
            <CircleCheck size={18} aria-hidden="true" />
          ) : finding.severity === 'INFO' ? (
            <FileText size={18} aria-hidden="true" />
          ) : (
            <TriangleAlert size={18} aria-hidden="true" />
          )}
        </span>
        <span>{finding.title}</span>
      </summary>
      <div className="disclosure-content">
        <p>{finding.explanation}</p>
        <FindingValues finding={finding} currency={currency} />
        <FindingSource finding={finding} onShowSource={onShowSource} />
        {finding.owner && (
          <p>
            <strong>Owner:</strong> {finding.owner}
          </p>
        )}
        {finding.next_action && (
          <p>
            <strong>Next action:</strong> {finding.next_action}
          </p>
        )}
        <small className="reason-code">{finding.code}</small>
      </div>
    </details>
  )
}
export const failureMessages: Record<string, string> = {
  PROVIDER_TIMEOUT:
    'The invoice could not be analyzed because the document extraction service timed out.',
  RATE_LIMIT:
    'Document extraction is temporarily unavailable because the processing quota was reached.',
  INVALID_PDF: 'The uploaded file could not be read as a valid PDF.',
  EMPTY_PDF: 'The PDF contains no readable invoice content.',
  ENCRYPTED_PDF: 'This PDF is encrypted. Upload an unlocked copy of the invoice.',
  PAGE_LIMIT: 'This PDF exceeds the supported 10-page limit.',
  RESOURCE_LIMIT: 'The PDF exceeds safe document-processing limits. Try a simpler PDF.',
  CONFIGURATION:
    'Document processing is not configured. Ask the application owner to check the extraction service.',
  AUTHORIZATION:
    'The extraction service could not authorize this request. Ask the application owner to check access.',
  PROVIDER_UNAVAILABLE: 'The document extraction service is temporarily unavailable.',
  MODEL_OUTPUT_JSON: 'The extraction service returned malformed invoice data.',
  MODEL_OUTPUT_SCHEMA: 'The extraction service returned data outside the expected invoice format.',
  MODEL_OUTPUT_UNUSABLE: 'The extraction did not provide enough usable invoice facts.',
  INVALID_RESPONSE:
    'A usable invoice extraction could not be produced. Verify the source PDF and try uploading again.',
}
export function Diagnostics({ run }: { run: Run }) {
  const controlled = run.model_id?.startsWith('TEST_ONLY')
  const values = [
    ['Source route', run.source_route ? words(run.source_route) : null],
    ['Extraction model', run.model_id],
    ['Model calls', run.usage?.model_calls],
    ['Input tokens', run.usage?.input_tokens],
    ['Output tokens', run.usage?.output_tokens],
    ...['extraction', 'matching', 'evaluation', 'total_processing'].map((name) => [
      `${words(name)} time`,
      elapsed(run.timings.find((t) => t.name === name)?.milliseconds),
    ]),
    ['Extraction schema', run.extraction_schema_version],
    ['Policy version', run.policy_snapshot?.version],
    ['Execution error code', run.execution_error_code],
    ['Run ID', run.id],
  ]
  return (
    <details className="diagnostics">
      <summary>Run diagnostics</summary>
      {controlled && (
        <p className="run-provenance">
          Controlled extraction (TEST_ONLY). This run used a saved extraction reply and made no live
          Gemini request.
        </p>
      )}
      <dl>
        {values.map(([label, value]) => (
          <div key={String(label)}>
            <dt>{label}</dt>
            <dd>{value === null || value === undefined || value === '' ? unknown : value}</dd>
          </div>
        ))}
      </dl>
    </details>
  )
}
function BusinessDecision({ run, onShowSource }: { run: Run; onShowSource: ShowFindingSource }) {
  const decision = run.decision!
  const invoice = run.extracted_invoice
  const primary = decision.findings.find((finding) => finding.code === decision.primary_reason_code)
  const arithmetic = decision.findings.find(
    (finding) => finding.code === 'TOTAL_RECONCILIATION_FAILED',
  )
  return (
    <>
      {decision.outcome === 'READY_FOR_AP' ? (
        <section className="decision-brief ready-brief">
          <div className="section-heading">
            <CircleCheck size={24} aria-hidden="true" />
            <h2>Ready to process</h2>
          </div>
          {decision.findings
            .filter((f) => f.severity === 'PASS')
            .map((f) => (
              <p className="check-note" key={f.code}>
                <Check size={16} aria-hidden="true" />
                {f.title}
              </p>
            ))}
          {invoice?.evidence.length &&
          invoice.evidence.every((ref) => ref.evidence_state === 'NATIVE_VERIFIED') ? (
            <p className="check-note">
              <ShieldCheck size={16} aria-hidden="true" />
              {invoice.evidence.length} extracted field references source verified
            </p>
          ) : null}
          <p className="control-disclaimer">
            This invoice passed the supported two-way controls. Payment and posting require separate
            authorization.
          </p>
        </section>
      ) : (
        <>
          <section
            className={`decision-brief ${decision.outcome === 'BLOCKED' ? 'blocked-brief' : 'review-brief'}`}
            aria-labelledby="primary-finding-title"
          >
            <h2 id="primary-finding-title">{primary?.title ?? 'This invoice needs attention'}</h2>
            <p>
              {primary?.code === 'SOURCE_EVIDENCE_MISSING'
                ? 'Some invoice fields have not been independently source verified. Review the source evidence before continuing.'
                : primary?.code === 'PO_BALANCE_EXCEEDED'
                  ? 'The invoice net is above the remaining purchase order commitment.'
                  : (primary?.explanation ??
                    'Review the findings and original invoice before continuing.')}
            </p>
            {primary && primary.code !== 'SOURCE_EVIDENCE_MISSING' && (
              <ExceptionValues finding={primary} currency={invoice?.currency} />
            )}
            {primary && <FindingSource finding={primary} onShowSource={onShowSource} />}
            {arithmetic && arithmetic !== primary && (
              <div className="related-financial">
                <h3>{arithmetic.title}</h3>
                <p>{arithmetic.explanation}</p>
                <ExceptionValues finding={arithmetic} currency={invoice?.currency} />
              </div>
            )}
            <div className="ownership">
              <div>
                <h3>Resolution owner</h3>
                <p>{decision.owner ?? primary?.owner ?? 'Owner not assigned'}</p>
              </div>
              <div>
                <h3>Recommended next step</h3>
                <p>
                  {decision.next_action ??
                    primary?.next_action ??
                    'Review the invoice findings with AP.'}
                </p>
              </div>
            </div>
          </section>
        </>
      )}
    </>
  )
}
function SupportingRecords({ run, onShowSource }: { run: Run; onShowSource: ShowFindingSource }) {
  const decision = run.decision!
  const invoice = run.extracted_invoice
  return (
    <>
      <section className="workspace-section">
        <h2>Findings & controls</h2>
        {(
          [
            ['BLOCK', 'Blockers'],
            ['REVIEW', 'Needs review'],
            ['PASS', 'Passed controls'],
            ['INFO', 'Information'],
          ] as const
        ).map(([severity, label]) => {
          const findings = decision.findings.filter((f) => f.severity === severity)
          return findings.length ? (
            <div className="finding-group" key={severity}>
              <div className="finding-group-heading">
                <h3>{label}</h3>
                <span>{findings.length}</span>
              </div>
              {findings.map((finding, index) => (
                <FindingDetails
                  key={`${finding.code}-${index}`}
                  finding={finding}
                  currency={invoice?.currency}
                  onShowSource={onShowSource}
                />
              ))}
            </div>
          ) : null
        })}
      </section>
      <section className="workspace-section">
        <h2>Purchase order context</h2>
        {run.candidates.length > 1 && (
          <p className="review-note">
            The original analysis returned alternatives. Use Review PO candidates above when
            available; this historical context does not select a PO.
          </p>
        )}
        {run.candidates.length ? (
          run.candidates.map((candidate) => (
            <div className="po-record" key={candidate.po.id}>
              <div className="section-heading">
                <h3>{candidate.po.id}</h3>
                <span>{candidate.po.status}</span>
              </div>
              <dl className="finding-values">
                <div>
                  <dt>Authorized net</dt>
                  <dd className="amount">
                    {money(candidate.po.authorized_net, candidate.po.currency)}
                  </dd>
                </div>
                <div>
                  <dt>Vendor record</dt>
                  <dd>{candidate.po.vendor_id}</dd>
                </div>
              </dl>
              <p>
                <strong>Identification provenance:</strong> {candidate.selection_provenance}
              </p>
              <p>Financial eligibility is reported separately in Findings &amp; controls.</p>
            </div>
          ))
        ) : (
          <p>No authoritative PO candidate was returned.</p>
        )}
      </section>
    </>
  )
}
export default function Workspace() {
  const { runId = '' } = useParams()
  const query = useRun(runId)
  const [focused, setFocused] = useState<{
    id: string
    label: string
    runId: string
    trigger: HTMLElement
  } | null>(null)
  const focusTarget = useRef<HTMLDivElement>(null)
  const focus = focused?.runId === runId ? focused : null
  const [copied, setCopied] = useState(false)
  const [copyError, setCopyError] = useState(false)
  const [sourcePage, setSourcePage] = useState<{
    runId: string
    number: number
    evidenceIndex?: number
    reference: Evidence
  } | null>(null)
  useEffect(() => {
    setCopied(false)
    setCopyError(false)
  }, [runId])
  if (query.isPending) return <Loading label="Loading invoice workspace…" />
  if (query.isError)
    return query.error instanceof ApiError && query.error.status === 404 ? (
      <section className="empty-state">
        <h1>Invoice not found</h1>
        <p>This run is unavailable. Open the queue to find a persisted invoice.</p>
        <Link className="button secondary" to="/runs">
          Open invoice queue
        </Link>
      </section>
    ) : (
      <ErrorState title="The invoice workspace is unavailable" retry={() => void query.refetch()} />
    )
  const run = query.data
  if (!run) return null
  const invoice = run.extracted_invoice
  const page = sourcePage?.runId === run.id ? sourcePage : undefined
  const showFindingSource: ShowFindingSource = (reference, trigger) => {
    if (!reference.page) return
    const index =
      invoice?.evidence.findIndex(
        (item) =>
          item.field === reference.field &&
          item.page === reference.page &&
          item.evidence_state === reference.evidence_state &&
          item.quote === reference.quote,
      ) ?? -1
    setSourcePage({
      runId,
      number: reference.page,
      reference,
      evidenceIndex: index >= 0 ? index : undefined,
    })
    setFocused({
      id: 'source-inspection',
      label: 'Inspect invoice source',
      runId,
      trigger: focus?.trigger ?? trigger,
    })
  }
  const appliedTolerance = run.policy_snapshot?.price_tolerance_pct
  const sourceUrl = api.documentUrl(run.id)
  const pending = active(run.execution_state)
  const failed =
    run.execution_state === 'PROCESSING_FAILED' || run.execution_state === 'INTERRUPTED'
  const announcement = pending
    ? run.execution_state === 'QUEUED'
      ? 'Invoice queued. Waiting for processing capacity.'
      : `Processing: ${stageLabels[run.stages.find((s) => s.state === 'RUNNING')?.name ?? ''] ?? 'Analysis in progress'}.`
    : failed
      ? 'Processing ended without an AP decision.'
      : `Analysis complete. ${run.decision ? statusInfo[run.decision.outcome].label : 'No decision available'}.`
  return (
    <div className="invoice-workspace">
      <div className="workspace-breadcrumb">
        <Link className="text-link" to="/runs">
          <ArrowLeft size={16} aria-hidden="true" />
          Back to queue
        </Link>
        <a className="invoice-mobile-source text-link" href="#source-document">
          View PDF
        </a>
        <button
          className="button quiet"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(window.location.href)
              setCopied(true)
              setCopyError(false)
            } catch {
              setCopyError(true)
            }
          }}
        >
          <Copy size={15} aria-hidden="true" />
          {copyError ? 'Copy unavailable' : copied ? 'Link copied' : 'Copy link'}
        </button>
        <span className={copyError ? 'copy-error' : 'sr-only'} role="status">
          {copyError
            ? 'Copy is unavailable. Copy the address from your browser.'
            : copied
              ? 'Invoice link copied.'
              : ''}
        </span>
      </div>
      <div className="invoice-layout">
        <WorkspaceNavigation
          key={run.id}
          hasDecision={!!run.decision}
          hasEvidence={!!invoice}
          onFocusSection={({ id, label }, trigger) => {
            document.getElementById(id)?.scrollIntoView?.({ block: 'nearest' })
            setFocused({ id, label, runId, trigger })
          }}
        />
        <div className="invoice-content">
          <WorkspaceFocusSection focused={focus?.id === 'case-decision'} target={focusTarget}>
            <header className="invoice-hero" id="case-decision" tabIndex={-1}>
              <div>
                <div className="invoice-hero-outcome">
                  {run.decision && <span>Recorded decision</span>}
                  <Status state={run.execution_state} outcome={run.decision?.outcome} />
                  {run.decision && (
                    <span className="invoice-policy-applied">
                      {appliedTolerance
                        ? `Policy applied: ${toleranceLabel(appliedTolerance)} unit-price tolerance`
                        : 'Applied unit-price tolerance unavailable'}
                    </span>
                  )}
                </div>
                <h1>
                  {invoice?.vendor_name_raw ||
                    (pending
                      ? 'Invoice analysis in progress'
                      : failed
                        ? 'Invoice processing incomplete'
                        : 'Supplier not available')}
                </h1>
                <p className="invoice-identity">
                  {invoice?.invoice_number || `Run ${run.id.slice(0, 8)}`}
                </p>
                <div className="invoice-meta">
                  <span>
                    Invoice date <strong>{date(invoice?.invoice_date)}</strong>
                  </span>
                  <span>
                    Purchase order <strong>{invoice?.po_reference ?? unknown}</strong>
                  </span>
                </div>
              </div>
              <div className="invoice-hero-amount">
                <span>
                  Invoice total{invoice?.currency ? ` · ${invoice.currency}` : ''}
                  {invoice?.total ? ' incl. tax' : ''}
                </span>
                <strong className="amount">{money(invoice?.total, invoice?.currency)}</strong>
              </div>
            </header>
          </WorkspaceFocusSection>
          <p className="run-announcement" role="status" aria-live="polite" aria-atomic="true">
            {announcement}
          </p>
          {pending && (
            <section className="processing-panel">
              <h2>
                {run.execution_state === 'QUEUED' ? 'Waiting to process' : 'Analysis is underway'}
              </h2>
              <p>
                {run.execution_state === 'QUEUED'
                  ? 'Your PDF is stored. It will be processed when capacity is available.'
                  : 'Progress below reflects real backend work. You can leave and return to this invoice.'}
              </p>
            </section>
          )}
          {failed && (
            <section className="technical-failure" role="alert">
              <TriangleAlert size={26} aria-hidden="true" />
              <h2>
                {run.execution_state === 'INTERRUPTED'
                  ? 'Processing was interrupted'
                  : 'Invoice processing failed'}
              </h2>
              <p>
                {run.execution_state === 'INTERRUPTED'
                  ? 'Processing stopped before completion. No AP decision was produced.'
                  : (failureMessages[run.execution_error_code ?? ''] ??
                    'The invoice could not be analyzed because of a technical processing problem.')}
              </p>
              <p>No financial decision was produced.</p>
              <Link className="button secondary" to="/runs/upload">
                Retry by uploading again
              </Link>
            </section>
          )}
          {(pending || failed) && (
            <WorkspaceFocusSection focused={focus?.id === 'case-trace'} target={focusTarget}>
              <DecisionTrace key={run.id} run={run} />
            </WorkspaceFocusSection>
          )}
          <div className="invoice-decision-grid">
            <div className="decision-column">
              <WorkspaceFocusSection focused={focus?.id === 'case-decision'} target={focusTarget}>
                {run.decision && (
                  <>
                    {!invoice?.po_reference?.trim() && (
                      <p className="recorded-assessment-label">Original automated decision</p>
                    )}
                    <BusinessDecision run={run} onShowSource={showFindingSource} />
                    <FollowUpAction key={run.id} run={run} />
                  </>
                )}
                <HumanPOReview
                  key={run.id}
                  run={run}
                  renderFinding={(finding) => (
                    <FindingDetails
                      finding={finding}
                      currency={invoice?.currency}
                      onShowSource={showFindingSource}
                    />
                  )}
                />
              </WorkspaceFocusSection>
              {invoice && (
                <WorkspaceFocusSection focused={focus?.id === 'evidence'} target={focusTarget}>
                  <section
                    className="invoice-evidence"
                    id="evidence"
                    tabIndex={-1}
                    aria-labelledby="evidence-title"
                  >
                    <h2 id="evidence-title">Source evidence</h2>
                    <p>Compare extracted fields with their supporting text and page references.</p>
                    <EvidenceList
                      key={run.id}
                      evidence={invoice.evidence}
                      onShowPage={showFindingSource}
                      sourceSelection={page}
                    />
                  </section>
                </WorkspaceFocusSection>
              )}
            </div>
            <section
              className="document-panel"
              id="source-document"
              tabIndex={-1}
              aria-labelledby="source-title"
            >
              <div className="section-heading">
                <h2 id="source-title">
                  <FileText size={18} aria-hidden /> Source invoice
                </h2>
                <a className="text-link" href={sourceUrl} target="_blank" rel="noopener noreferrer">
                  Open PDF
                  <ArrowUpRight size={16} aria-hidden="true" />
                  <span className="sr-only"> (new tab)</span>
                </a>
              </div>
              <iframe
                title="Original invoice PDF"
                src={`${sourceUrl}#toolbar=0&view=FitH`}
                loading="lazy"
              />
              {invoice && (
                <button
                  className="document-evidence-link text-link"
                  type="button"
                  aria-haspopup="dialog"
                  onClick={(event) =>
                    setFocused({
                      id: 'evidence',
                      label: 'Source evidence',
                      runId,
                      trigger: event.currentTarget,
                    })
                  }
                >
                  Inspect source evidence
                </button>
              )}
            </section>
          </div>
          {run.decision && (
            <WorkspaceFocusSection focused={focus?.id === 'case-trace'} target={focusTarget}>
              <div className="completed-trace">
                <DecisionTrace key={run.id} run={run} />
              </div>
            </WorkspaceFocusSection>
          )}
          <WorkspaceFocusSection focused={focus?.id === 'case-details'} target={focusTarget}>
            <section
              className="invoice-run-details"
              id="case-details"
              tabIndex={-1}
              aria-labelledby="details-title"
            >
              <div className="section-heading">
                <h2 id="details-title">Run details</h2>
                {run.model_id?.startsWith('TEST_ONLY') && (
                  <span
                    className="invoice-demo-label"
                    title="Controlled extraction from a saved reply. No live Gemini request."
                  >
                    <FlaskConical size={15} aria-hidden /> Demo run
                    <span className="sr-only">
                      . Controlled extraction with no live Gemini request.
                    </span>
                  </span>
                )}
              </div>
              <Diagnostics run={run} />
              {run.decision && (
                <details className="workspace-audit" open={run.candidates.length > 1}>
                  <summary>All controls & procurement records</summary>
                  <div>
                    <SupportingRecords run={run} onShowSource={showFindingSource} />
                  </div>
                </details>
              )}
            </section>
          </WorkspaceFocusSection>
        </div>
        <FocusDialog
          open={focus !== null}
          label={focus?.label}
          section={focus?.id}
          contentRef={focusTarget}
          onClose={() => {
            setFocused(null)
            focus?.trigger.focus({ preventScroll: true })
          }}
        >
          {focus?.id === 'source-inspection' && page && (
            <div className="source-focus-content">
              <h2>Inspect invoice source</h2>
              <p className="source-focus-provenance">
                Page {page.number} ·{' '}
                {page.reference.evidence_state === 'NATIVE_VERIFIED'
                  ? 'Independently verified'
                  : 'Extracted reference · needs verification'}
              </p>
              {page.reference.quote && <blockquote>{page.reference.quote}</blockquote>}
              <iframe
                title="Referenced invoice page"
                src={`${sourceUrl}#page=${page.number}&toolbar=0&view=Fit`}
              />
              <a
                className="text-link"
                href={`${sourceUrl}#page=${page.number}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open page {page.number} in a new tab <ArrowUpRight size={16} aria-hidden="true" />
              </a>
            </div>
          )}
        </FocusDialog>
      </div>
    </div>
  )
}
