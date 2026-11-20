import { Copy, FilePenLine, ShieldCheck, X } from 'lucide-react'
import { useId, useRef, useState } from 'react'
import { draftText, followUpDrafts, processingSummary, type Audience } from './follow-up'
import type { Run } from './types'
import './follow-up.css'

export default function FollowUpAction({ run }: { run: Run }) {
  const titleId = useId()
  const noticeId = useId()
  const drawer = useRef<HTMLDialogElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const close = useRef<HTMLButtonElement>(null)
  const [drafts, setDrafts] = useState<ReturnType<typeof followUpDrafts> | null>(null)
  const [audience, setAudience] = useState<Audience>('internal')
  const [feedback, setFeedback] = useState('')
  if (run.execution_state !== 'COMPLETED' || !run.decision) return null

  const ready = run.decision.outcome === 'READY_FOR_AP'
  const draft = drafts?.[audience]
  const invoice = run.extracted_invoice
  const context = [invoice?.invoice_number, invoice?.vendor_name_raw].filter(Boolean).join(' · ')

  async function copy(text: string, success: string) {
    try {
      await navigator.clipboard.writeText(text)
      setFeedback(success)
    } catch {
      setFeedback('Clipboard unavailable. Check browser permissions and try again.')
    }
  }

  function openDrawer() {
    const next = followUpDrafts(run)
    setDrafts(next)
    setAudience(next.defaultAudience)
    setFeedback('')
    drawer.current?.showModal()
    close.current?.focus()
  }

  function edit(field: 'subject' | 'body', value: string) {
    if (!drafts || !draft) return
    setDrafts({ ...drafts, [audience]: { ...draft, [field]: value } })
    setFeedback('')
  }

  return (
    <div className="follow-up-actions">
      <button
        type="button"
        ref={trigger}
        className="button secondary"
        aria-haspopup={ready ? undefined : 'dialog'}
        onClick={
          ready ? () => void copy(processingSummary(run), 'Processing summary copied.') : openDrawer
        }
      >
        {ready ? <Copy size={16} aria-hidden /> : <FilePenLine size={16} aria-hidden />}
        {ready ? 'Copy processing summary' : 'Prepare follow-up'}
      </button>
      {ready ? (
        <p role="status">{feedback}</p>
      ) : (
        <dialog
          ref={drawer}
          className="follow-up-drawer"
          aria-labelledby={titleId}
          aria-describedby={noticeId}
          onClose={(event) => {
            event.stopPropagation()
            setFeedback('')
            trigger.current?.focus()
          }}
        >
          <header className="follow-up-header">
            <div>
              <h2 id={titleId}>Prepare follow-up</h2>
              {context && (
                <p className="follow-up-context">Extracted invoice context · {context}</p>
              )}
            </div>
            <button
              ref={close}
              className="icon-button"
              type="button"
              aria-label="Close follow-up"
              onClick={() => drawer.current?.close()}
            >
              <X size={22} aria-hidden />
            </button>
          </header>
          {drafts?.supplier ? (
            <fieldset className="follow-up-audience">
              <legend>Audience</legend>
              {(['internal', 'supplier'] as const).map((option) => (
                <label key={option}>
                  <input
                    type="radio"
                    name={titleId}
                    checked={audience === option}
                    onChange={() => {
                      setAudience(option)
                      setFeedback('')
                    }}
                  />
                  {option === 'internal' ? 'Internal' : 'Supplier'}
                </label>
              ))}
            </fieldset>
          ) : (
            <p className="follow-up-audience-note">Audience · Internal</p>
          )}
          <label className="follow-up-field">
            Subject
            <input
              value={draft?.subject ?? ''}
              onChange={(event) => edit('subject', event.target.value)}
            />
          </label>
          <label className="follow-up-field">
            Message
            <textarea
              rows={10}
              value={draft?.body ?? ''}
              onChange={(event) => edit('body', event.target.value)}
            />
          </label>
          <p className="follow-up-notice" id={noticeId}>
            <ShieldCheck size={17} aria-hidden />
            <span>
              Drafted from the recorded findings and verified PDF details. Check the wording before
              sharing. AP Compass only copies the draft.
            </span>
          </p>
          <footer className="follow-up-footer">
            <p role="status">{feedback}</p>
            <button
              className="button primary"
              type="button"
              disabled={!draft?.subject.trim() || !draft?.body.trim()}
              onClick={() => {
                if (draft) void copy(draftText(draft), 'Draft copied.')
              }}
            >
              <Copy size={16} aria-hidden /> Copy draft
            </button>
          </footer>
        </dialog>
      )}
    </div>
  )
}
