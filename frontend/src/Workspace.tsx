import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowUpRight,
  Check,
  CircleCheck,
  Copy,
  FileText,
  ShieldCheck,
  TriangleAlert,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { ApiError, api } from './api'
import { active, useRun } from './queries'
import { ErrorState, Loading, Status, statusInfo } from './components'
import {
  date,
  decimal,
  elapsed,
  money,
  unknown,
  valueLabels,
  words,
  toleranceLabel,
} from './format'
import DecisionTrace, { stageLabels } from './DecisionTrace'
import PolicyImpact from './PolicyImpact'
export { StageTimeline } from './DecisionTrace'
import type { Evidence, Finding, Run } from './types'

export function FindingValues({
  finding,
  currency,
}: {
  finding: Finding
  currency?: string | null
}) {
  const isMoney = (name: string) =>
    name.endsWith('_net') ||
    ['expected_gross', 'stated_gross', 'difference', 'invoice_price', 'po_price'].includes(name)
  return finding.values.length ? (
    <dl className="finding-values">
      {finding.values.map((value, index) => (
        <div key={`${value.name}-${index}`}>
          <dt>{valueLabels[value.name] ?? words(value.name)}</dt>
          <dd className={isMoney(value.name) ? 'amount' : ''}>
            {value.value === null
              ? unknown
              : isMoney(value.name)
                ? money(value.value, currency)
                : value.name === 'tolerance_pct'
                  ? toleranceLabel(value.value)
                  : value.name.endsWith('_qty') || value.name === 'qty'
                    ? decimal(value.value)
                    : value.value}
          </dd>
        </div>
      ))}
    </dl>
  ) : null
}
/** Presentation only: emphasize existing backend comparison values; never calculate them. */
function ExceptionValues({ finding, currency }: { finding: Finding; currency?: string | null }) {
  const keys = ['remaining_net', 'requested_net', 'excess_net'].every((name) =>
    finding.values.some((value) => value.name === name),
  )
    ? ['remaining_net', 'requested_net', 'excess_net']
    : ['expected_gross', 'stated_gross', 'difference'].every((name) =>
          finding.values.some((value) => value.name === name),
        )
      ? ['expected_gross', 'stated_gross', 'difference']
      : []
  if (!keys.length) return <FindingValues finding={finding} currency={currency} />
  const comparison = keys.flatMap((name) => finding.values.filter((value) => value.name === name))
  const supporting = finding.values.filter((value) => !keys.includes(value.name))
  return (
    <>
      <div className="exception-comparison">
        <FindingValues finding={{ ...finding, values: comparison }} currency={currency} />
      </div>
      {supporting.length > 0 && (
        <div className="comparison-context">
          <FindingValues finding={{ ...finding, values: supporting }} currency={currency} />
        </div>
      )}
    </>
  )
}
export function FindingDetails({
  finding,
  currency,
}: {
  finding: Finding
  currency?: string | null
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
const fieldLabels: Record<string, string> = {
  vendor_name_raw: 'Supplier',
  invoice_number: 'Invoice number',
  invoice_date: 'Invoice date',
  po_reference: 'PO reference',
  currency: 'Currency',
  net: 'Invoice net',
  tax: 'Tax',
  total: 'Invoice total',
}
function fieldName(field: string) {
  const line = /^lines\[(\d+)\]\.(.+)$/.exec(field)
  return (
    fieldLabels[field] ?? (line ? `Line ${Number(line[1]) + 1}: ${words(line[2])}` : words(field))
  )
}
export function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  const labels = {
    NATIVE_VERIFIED: 'Source verified',
    SOURCE_LOCATED_UNVERIFIED: 'Source needs review',
    MISSING: 'Source not confirmed',
  }
  return (
    <div className="evidence-list">
      {!evidence.length ? (
        <p>No source references are available. Verify the original invoice.</p>
      ) : (
        evidence.map((ref, index) => (
          <details key={`${ref.field}-${index}`} className="evidence-item">
            <summary>
              <span>
                <strong>{fieldName(ref.field)}</strong>
                <span className="evidence-value">{ref.normalized_value ?? unknown}</span>
              </span>
              <span
                className={`evidence-state ${ref.evidence_state === 'NATIVE_VERIFIED' ? 'ready' : 'review'}`}
              >
                {ref.evidence_state === 'NATIVE_VERIFIED' ? (
                  <ShieldCheck size={14} aria-hidden="true" />
                ) : (
                  <TriangleAlert size={14} aria-hidden="true" />
                )}
                {labels[ref.evidence_state]}
              </span>
            </summary>
            <div className="disclosure-content">
              <p>{ref.page ? `Page ${ref.page}` : 'Page not located'}</p>
              {ref.evidence_state === 'NATIVE_VERIFIED' ? (
                <>
                  <strong>Verified source text</strong>
                  <blockquote>{ref.quote ?? unknown}</blockquote>
                </>
              ) : (
                <>
                  <p>
                    {ref.route === 'image_only' || ref.route === 'mixed'
                      ? 'The value was extracted from an image-based invoice and has not been independently text-verified.'
                      : 'This value has not been independently verified against the source text.'}
                  </p>
                  {ref.quote && (
                    <>
                      <strong>Extraction reference, not verified source text</strong>
                      <blockquote>{ref.quote}</blockquote>
                    </>
                  )}
                  {ref.normalized_value === null && ref.raw_value && (
                    <p>
                      Unverified model claim: {ref.raw_value}. The document-stated value remains
                      unknown.
                    </p>
                  )}
                </>
              )}
              <small className="reason-code">{ref.field}</small>
            </div>
          </details>
        ))
      )}
    </div>
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
  INVALID_RESPONSE:
    'A usable invoice extraction could not be produced. Verify the source PDF and try uploading again.',
}
export function Diagnostics({ run }: { run: Run }) {
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
function BusinessDecision({ run }: { run: Run }) {
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
          <p>This invoice passed AP Compass’s supported two-way controls.</p>
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
            Ready to process means the invoice passed AP Compass's supported two-way controls. It
            does not authorize payment or posting.
          </p>
        </section>
      ) : (
        <>
          <section
            className={`decision-brief ${decision.outcome === 'BLOCKED' ? 'blocked-brief' : 'review-brief'}`}
            aria-labelledby="primary-finding-title"
          >
            <div className="brief-label">
              <TriangleAlert size={18} aria-hidden="true" />
              {decision.outcome === 'BLOCKED' ? 'Resolution required' : 'Analyst review required'}
            </div>
            <h2 id="primary-finding-title">{primary?.title ?? 'This invoice needs attention'}</h2>
            <p>
              {primary?.code === 'SOURCE_EVIDENCE_MISSING'
                ? 'Some invoice fields have not been independently source verified. Review the source evidence before continuing.'
                : (primary?.explanation ??
                  'Review the findings and original invoice before continuing.')}
            </p>
            {primary && primary.code !== 'SOURCE_EVIDENCE_MISSING' && (
              <ExceptionValues finding={primary} currency={invoice?.currency} />
            )}
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
      <PolicyImpact key={run.id} run={run} />
      <DecisionTrace run={run} />
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
            Human confirmation required. These are alternatives; no PO can be confirmed here.
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
  const [copied, setCopied] = useState(false)
  const [copyError, setCopyError] = useState(false)
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
    <>
      <div className="workspace-breadcrumb">
        <Link className="text-link" to="/runs">
          <ArrowLeft size={16} aria-hidden="true" />
          Invoice Operations
        </Link>
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
      <header className="decision-header">
        <div>
          <Status state={run.execution_state} outcome={run.decision?.outcome} />
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
        <div className="invoice-header-amount">
          <span>Invoice total</span>
          <strong className="amount">{money(invoice?.total, invoice?.currency)}</strong>
          <small>
            {invoice?.currency ?? 'Currency pending extraction'}
            {invoice?.total ? ' including tax' : ''}
          </small>
        </div>
      </header>
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
          <DecisionTrace run={run} />
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
          <p>No financial decision was produced. This is not a financial rejection.</p>
          <Link className="button secondary" to="/runs#upload">
            Retry by uploading again
          </Link>
        </section>
      )}
      {failed && <DecisionTrace run={run} />}
      <div className="workspace-grid">
        <div className="decision-column">
          {run.decision && <BusinessDecision run={run} />}
          {invoice && (
            <section className="workspace-section" id="evidence">
              <h2>Source evidence</h2>
              <p>Verification describes support in the document, not financial approval.</p>
              <EvidenceList evidence={invoice.evidence} />
            </section>
          )}
          <Diagnostics run={run} />
        </div>
        <section className="document-panel" aria-labelledby="source-title">
          <div className="section-heading">
            <h2 id="source-title">Source invoice</h2>
            <a
              className="text-link"
              href={api.documentUrl(run.id)}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open source document
              <ArrowUpRight size={16} aria-hidden="true" />
              <span className="sr-only"> (new tab)</span>
            </a>
          </div>
          <p className="document-help">
            Original persisted PDF. Use the link if your browser cannot display it.
          </p>
          <iframe
            title="Original invoice PDF"
            src={`${api.documentUrl(run.id)}#toolbar=0&view=FitH`}
            loading="lazy"
          />
          <a
            className="document-fallback"
            href={api.documentUrl(run.id)}
            target="_blank"
            rel="noopener noreferrer"
          >
            <FileText size={17} aria-hidden="true" />
            Open PDF in a new tab
          </a>
        </section>
      </div>
    </>
  )
}
