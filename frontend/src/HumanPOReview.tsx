import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, GitCompareArrows, X } from 'lucide-react'
import { api, ApiError } from './api'
import { Status } from './components'
import { date, money } from './format'
import type { Finding, POConfirmationInput, Run } from './types'

export default function HumanPOReview({
  run,
  renderFinding,
}: {
  run: Run
  renderFinding: (finding: Finding) => ReactNode
}) {
  const client = useQueryClient()
  const eligible =
    run.execution_state === 'COMPLETED' &&
    !!run.decision &&
    !!run.extracted_invoice &&
    !run.extracted_invoice.po_reference?.trim()
  const history = useQuery({
    queryKey: ['review-history', run.id],
    queryFn: ({ signal }) => api.reviewHistory(run.id, signal),
    enabled: eligible,
    retry: false,
  })
  const dialog = useRef<HTMLDialogElement>(null)
  const opener = useRef<HTMLButtonElement>(null)
  const submitLock = useRef(false)
  const resultHeading = useRef<HTMLHeadingElement>(null)
  const [po, setPO] = useState('')
  const [reviewer, setReviewer] = useState('')
  const [rationale, setRationale] = useState('')
  const [key, setKey] = useState(() => crypto.randomUUID())
  const [confirming, setConfirming] = useState(false)
  const data = history.data
  const mutation = useMutation({
    mutationFn: (body: POConfirmationInput) => api.confirmPO(run.id, body),
    retry: false,
    onSuccess: (action) => {
      client.setQueryData(['review-history', run.id], {
        ...data,
        actions: [action],
        current_reviewed_assessment: action.reassessment,
        confirmation_available: false,
      })
      void client.invalidateQueries({ queryKey: ['runs'] })
      dialog.current?.close()
      opener.current?.focus()
    },
    onSettled: () => {
      submitLock.current = false
      setConfirming(false)
    },
  })
  useEffect(() => {
    if (mutation.isError) dialog.current?.querySelector<HTMLElement>('[role="alert"]')?.focus()
  }, [mutation.isError])
  useEffect(() => {
    if (mutation.isSuccess) resultHeading.current?.focus()
  }, [mutation.isSuccess])
  useEffect(() => {
    if (data?.actions.length && dialog.current?.open) {
      dialog.current.close()
      resultHeading.current?.focus()
    }
  }, [data?.actions[0]?.id])
  if (!eligible) return null
  if (history.isPending)
    return (
      <section className="human-review" role="status">
        Loading PO review history…
      </section>
    )
  if (history.isError)
    return (
      <section className="human-review" role="alert">
        <h2>PO review history unavailable</h2>
        <p>The recorded automated decision is unchanged.</p>
        <button className="button secondary" onClick={() => void history.refetch()}>
          Reload review history
        </button>
      </section>
    )
  if (!data) return null
  const action = data.actions[0]
  const assessment = data.current_reviewed_assessment
  const outstanding =
    assessment?.findings.filter((f) => f.severity === 'BLOCK' || f.severity === 'REVIEW') ?? []
  if (!action && !data.confirmation_available) return null
  const valid =
    !!po &&
    reviewer.trim().length > 0 &&
    rationale.trim().length >= 10 &&
    rationale.trim().length <= 2000
  return (
    <section className="human-review" aria-labelledby="human-review-title">
      <div className="section-heading">
        <h2 id="human-review-title" ref={resultHeading} tabIndex={-1}>
          {action ? 'Human-reviewed assessment' : 'Resolve purchase order identity'}
        </h2>
        <GitCompareArrows size={22} aria-hidden="true" />
      </div>
      <p className="demo-identity">Demo reviewer — identity not authenticated</p>
      {run.model_id?.startsWith('TEST_ONLY') && (
        <p className="review-test-note">
          Synthetic regression case · test-provider extraction. Review actions below are actually
          persisted.
        </p>
      )}
      {action && assessment ? (
        <>
          <div className="review-outcomes">
            <section aria-label="Original automated decision">
              <h3>Original automated decision</h3>
              <Status state="COMPLETED" outcome={action.original_decision.outcome} />
            </section>
            <section aria-label="Current reassessment">
              <h3>Current reassessment</h3>
              <Status state="COMPLETED" outcome={assessment.outcome} />
            </section>
          </div>
          <div className="review-saved" role="status" aria-live="polite">
            <Check size={18} aria-hidden="true" />
            <p>
              PO identity recorded.{' '}
              {assessment.outcome === 'READY_FOR_AP'
                ? 'Supported AP controls now pass.'
                : 'The invoice is still not ready to process.'}
            </p>
          </div>
          <dl className="review-action-facts">
            <div>
              <dt>Confirmed PO</dt>
              <dd>{action.selected_po_id}</dd>
            </div>
            <div>
              <dt>Saved</dt>
              <dd>
                <time dateTime={action.created_at}>{date(action.created_at, true)}</time>
              </dd>
            </div>
            <div>
              <dt>Demo reviewer label</dt>
              <dd>{action.reviewer_label}</dd>
            </div>
          </dl>
          <p>
            <strong>Rationale</strong>
            <br />
            {action.rationale}
          </p>
          <p>
            What changed: the missing-reference identity requirement was resolved by the recorded
            human selection. Financial and source controls were re-evaluated.
          </p>
          <h3>Outstanding findings</h3>
          {outstanding.length > 0 && (
            <p>
              {
                assessment.findings.find((f) => f.code === assessment.primary_reason_code)
                  ?.explanation
              }
            </p>
          )}
          {outstanding.length ? (
            outstanding.map((f) => <div key={f.code}>{renderFinding(f)}</div>)
          ) : (
            <p>No outstanding blocker or review finding in this reassessment.</p>
          )}
          {assessment.owner && (
            <p>
              <strong>Resolution owner:</strong> {assessment.owner}
            </p>
          )}
          {assessment.next_action && (
            <p>
              <strong>Next action:</strong> {assessment.next_action}
            </p>
          )}
          <details className="review-provenance">
            <summary>Review action & provenance</summary>
            <dl>
              <dt>Action ID</dt>
              <dd>{action.id}</dd>
              <dt>Recorded policy</dt>
              <dd>{action.policy_snapshot.version}</dd>
              <dt>Authority fingerprint</dt>
              <dd>{action.authority_fingerprint}</dd>
              <dt>Selection provenance</dt>
              <dd>{action.selection_provenance}</dd>
            </dl>
          </details>
        </>
      ) : (
        <>
          <p>
            Compare authoritative candidates and record the intended PO with a rationale.
            Confirmation identifies the order; it does not establish financial eligibility.
          </p>
          <button
            ref={opener}
            className="button"
            onClick={() => {
              mutation.reset()
              setKey(crypto.randomUUID())
              dialog.current?.showModal()
            }}
          >
            Review PO candidates
          </button>
        </>
      )}
      <p className="control-disclaimer">
        Uses current authoritative procurement and billed records with the source run’s recorded
        policy. Original automated decision, extraction and stages remain unchanged. This does not
        authorize payment or posting.
      </p>
      <dialog
        ref={dialog}
        className="po-review-dialog"
        aria-labelledby="po-dialog-title"
        onCancel={(event) => {
          if (confirming) event.preventDefault()
        }}
        onClose={() => opener.current?.focus()}
      >
        <div className="section-heading">
          <h2 id="po-dialog-title">Review PO candidates</h2>
          <button
            className="button quiet"
            aria-label="Close PO review"
            disabled={confirming}
            onClick={() => dialog.current?.close()}
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>
        <p className="demo-identity">Demo reviewer — identity not authenticated</p>
        <p>
          Financial eligibility is checked separately after selection. Missing invoice facts and
          uncertain source evidence remain unresolved.
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (!valid || confirming || submitLock.current) return
            submitLock.current = true
            setConfirming(true)
            mutation.mutate({
              po_id: po,
              reviewer_label: reviewer.trim(),
              rationale: rationale.trim(),
              client_action_id: key,
            })
          }}
        >
          <fieldset disabled={confirming}>
            <legend>Choose the intended authoritative PO</legend>
            <div className="po-choice-list">
              {data.candidates.map((candidate) => (
                <label className="po-choice" key={candidate.po.id}>
                  <input
                    type="radio"
                    name="confirmed-po"
                    value={candidate.po.id}
                    checked={po === candidate.po.id}
                    onChange={() => setPO(candidate.po.id)}
                    required
                  />
                  <span>
                    <strong>{candidate.po.id}</strong>
                    <span>
                      {data.canonical_vendor_name} · {candidate.po.vendor_id}
                    </span>
                    <span>
                      {candidate.po.status} · Authorized net{' '}
                      {money(candidate.po.authorized_net, candidate.po.currency)}
                    </span>
                    <small>{candidate.selection_provenance}</small>
                  </span>
                </label>
              ))}
            </div>
            <label className="review-field">
              Demo reviewer label
              <input
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                maxLength={80}
                required
                autoComplete="off"
              />
            </label>
            <label className="review-field">
              Reason for confirming this PO
              <textarea
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                minLength={10}
                maxLength={2000}
                required
                rows={3}
                aria-describedby="rationale-help"
              />
            </label>
            <p id="rationale-help">
              10–2000 characters. Record how the intended PO was verified. Do not enter account
              details or secrets.
            </p>
          </fieldset>
          {mutation.isError && (
            <div role="alert" tabIndex={-1}>
              <p>
                {mutation.error instanceof ApiError && mutation.error.status === 409
                  ? 'A confirmation may already exist. Close this dialog and reload review history before acting again.'
                  : 'The confirmation could not be saved. The original decision is unchanged. You can retry the same request safely.'}
              </p>
            </div>
          )}
          <p>
            You are confirming PO identity and saving a permanent demo audit action, not approving
            this invoice.
          </p>
          <div className="review-dialog-actions">
            <button
              type="button"
              className="button secondary"
              disabled={confirming}
              onClick={() => dialog.current?.close()}
            >
              Cancel
            </button>
            <button type="submit" className="button" disabled={!valid || confirming}>
              {confirming ? 'Saving reassessment…' : 'Confirm PO & re-evaluate'}
            </button>
          </div>
        </form>
      </dialog>
      {mutation.isError && !confirming && (
        <button className="button secondary" onClick={() => void history.refetch()}>
          Reload review history
        </button>
      )}
    </section>
  )
}
