import { useId, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ArrowRight, LockKeyhole, SlidersHorizontal } from 'lucide-react'
import { api, ApiError } from './api'
import { Status } from './components'
import { toleranceLabel } from './format'
import type { PriceTolerance, Run } from './types'

export default function PolicyImpact({ run }: { run: Run }) {
  const group = useId()
  const [choice, setChoice] = useState<PriceTolerance | null>(null)
  const preview = useMutation({
    mutationFn: (tolerance: PriceTolerance) => api.preview(run.id, tolerance),
    retry: false,
  })
  const result = !preview.isPending && !preview.isError ? preview.data : undefined
  return (
    <details className="policy-impact">
      <summary>
        <SlidersHorizontal size={19} aria-hidden="true" />
        <span>
          <strong>Policy impact</strong>
          <small>Explore a different unit-price tolerance</small>
        </span>
        <span className="policy-current">
          {toleranceLabel(run.policy_snapshot?.price_tolerance_pct)} recorded
        </span>
      </summary>
      <div className="policy-body">
        <div className="policy-notice">
          <h3>Policy preview</h3>
          <p>Original AP decision unchanged. No document reprocessing required.</p>
          <p>
            Uses stored extraction and current trusted procurement records. This simulation does not
            change the active policy or authorize payment.
          </p>
        </div>
        <div className="policy-compare">
          <section aria-label="Current evaluation">
            <h3>Current evaluation</h3>
            <p>
              Unit-price tolerance{' '}
              <strong>{toleranceLabel(run.policy_snapshot?.price_tolerance_pct)}</strong>
            </p>
            <Status state="COMPLETED" outcome={run.decision?.outcome} />
            <small>Recorded AP decision</small>
          </section>
          <section aria-label="Policy preview result" aria-busy={preview.isPending}>
            <fieldset disabled={preview.isPending}>
              <legend>Preview unit-price tolerance</legend>
              <div className="tolerance-options" data-choice={choice ?? ''}>
                <span className="tolerance-thumb" aria-hidden="true" />
                {(['0.02', '0.05'] as const).map((value) => (
                  <label key={value}>
                    <input
                      type="radio"
                      name={group}
                      value={value}
                      checked={choice === value}
                      onChange={() => {
                        setChoice(value)
                        preview.mutate(value)
                      }}
                    />
                    <span>{toleranceLabel(value)}</span>
                  </label>
                ))}
              </div>
            </fieldset>
            <div
              className="preview-status"
              data-settled={!!result}
              role="status"
              aria-live="polite"
            >
              {preview.isPending ? (
                <p>Evaluating stored facts…</p>
              ) : result ? (
                <>
                  <span className="preview-outcome-label">Preview outcome</span>
                  <Status state="COMPLETED" outcome={result.preview_decision.outcome} />
                  <p>
                    {result.changed
                      ? 'Decision changes under this preview.'
                      : 'Decision unchanged under this preview.'}
                  </p>
                </>
              ) : !preview.isError ? (
                <p>Select a tolerance to request a preview.</p>
              ) : null}
            </div>
          </section>
        </div>
        {preview.isError && (
          <div className="preview-error" role="alert">
            <p>
              {preview.error instanceof ApiError && preview.error.status === 409
                ? 'A completed business analysis is required for a policy preview.'
                : 'Policy preview is unavailable. The recorded decision is unchanged.'}
            </p>
            <button className="button secondary" onClick={() => choice && preview.mutate(choice)}>
              Try preview again
            </button>
          </div>
        )}
        {result && (
          <div className="preview-detail">
            <ol className="preview-path" aria-label="Policy preview path">
              {[
                'Stored extraction',
                'Current trusted records',
                `${toleranceLabel(result.preview_policy.price_tolerance_pct)} policy snapshot`,
                'Controls re-evaluated',
              ].map((step, i) => (
                <li key={step}>
                  {i > 0 && <ArrowRight size={13} aria-hidden="true" />}
                  {step}
                </li>
              ))}
            </ol>
            <p>No document reprocessing. Preview only; original AP decision unchanged.</p>
            <details className="preview-findings">
              <summary>Preview findings</summary>
              {result.preview_decision.findings.map((finding, index) => (
                <div key={`${finding.code}-${index}`}>
                  <strong>{finding.title}</strong>
                  <p>{finding.explanation}</p>
                  {finding.owner && <p>Owner: {finding.owner}</p>}
                  {finding.next_action && <p>Next action: {finding.next_action}</p>}
                  <small className="reason-code">{finding.code}</small>
                </div>
              ))}
            </details>
          </div>
        )}
        <div className="protected-controls">
          <h3>Protected controls</h3>
          <p>Changing price tolerance does not override PO authorization.</p>
          <ul>
            {[
              ['PO commitment ceiling', 'Cannot be bypassed'],
              ['PO quantity authorization', 'Cannot be bypassed'],
              ['Exact duplicate protection', 'Cannot be bypassed'],
              ['Explicit PO requirement', 'Required under the current control framework'],
            ].map(([name, detail]) => (
              <li key={name}>
                <LockKeyhole size={15} aria-hidden="true" />
                <span>
                  <strong>{name}</strong>
                  <small>{detail}</small>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </details>
  )
}
