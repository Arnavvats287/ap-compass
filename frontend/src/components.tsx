import { useEffect, useId, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  ArrowUpRight,
  Check,
  CircleCheck,
  CirclePause,
  FileText,
  LoaderCircle,
  ShieldAlert,
  Upload,
  X,
} from 'lucide-react'
import { api, ApiError } from './api'
import { active } from './queries'
import { date, money, relative, reasonLabel, fileSize } from './format'
import type { ExecutionState, Outcome, RunSummary } from './types'

export const statusInfo = {
  READY_FOR_AP: { label: 'Ready to process', tone: 'ready', icon: CircleCheck },
  REVIEW_REQUIRED: { label: 'Needs review', tone: 'review', icon: AlertCircle },
  BLOCKED: { label: 'Blocked', tone: 'blocked', icon: ShieldAlert },
  QUEUED: { label: 'Queued', tone: 'processing', icon: CirclePause },
  RUNNING: { label: 'Processing', tone: 'processing', icon: LoaderCircle },
  PROCESSING_FAILED: { label: 'Processing failed', tone: 'failed', icon: AlertCircle },
  INTERRUPTED: { label: 'Interrupted', tone: 'interrupted', icon: CirclePause },
}
export function Status({ state, outcome }: { state: ExecutionState; outcome?: Outcome | null }) {
  const info =
    statusInfo[
      state === 'COMPLETED' && outcome ? outcome : (state as Exclude<ExecutionState, 'COMPLETED'>)
    ]
  if (!info) return <span className="status">Decision unavailable</span>
  const Icon = info.icon
  return (
    <span className={`status ${info.tone}`}>
      <Icon size={15} aria-hidden="true" />
      {info.label}
    </span>
  )
}
export function Loading({ label = 'Loading invoice data…' }: { label?: string }) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span>{label}</span>
      <div className="skeleton" />
      <div className="skeleton short" />
      <div className="skeleton" />
    </div>
  )
}
export function ErrorState({
  title = 'Invoice data is unavailable',
  retry,
}: {
  title?: string
  retry?: () => void
}) {
  return (
    <section className="empty-state" role="alert">
      <AlertCircle size={26} aria-hidden="true" />
      <h2>{title}</h2>
      <p>Check the connection and try again. Your persisted invoices have not been changed.</p>
      {retry && (
        <button className="button secondary" onClick={retry}>
          Try again
        </button>
      )}
    </section>
  )
}
export function Empty({ filtered = false, clear }: { filtered?: boolean; clear?: () => void }) {
  return (
    <div className="empty-state">
      <FileText size={28} aria-hidden="true" />
      <h2>{filtered ? 'No invoices match these filters' : 'Your invoice queue starts here'}</h2>
      <p>
        {filtered
          ? 'Try another invoice number or supplier, or clear your filters.'
          : 'Upload a PDF to bring its source, AP controls and next action into one workspace.'}
      </p>
      {clear ? (
        <button className="button secondary" onClick={clear}>
          Clear filters
        </button>
      ) : (
        <a className="text-link" href="#upload">
          Choose an invoice PDF
        </a>
      )}
    </div>
  )
}
export function UploadPanel({ compact = false }: { compact?: boolean }) {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [drag, setDrag] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const errorRef = useRef<HTMLParagraphElement>(null)
  const id = useId()
  const navigate = useNavigate()
  const client = useQueryClient()
  const mutation = useMutation({
    mutationFn: (file: File) => api.upload(file),
    retry: false,
    onSuccess: (created) => {
      void client.invalidateQueries({ queryKey: ['runs'] })
      void client.invalidateQueries({ queryKey: ['dashboard'] })
      navigate(`/runs/${encodeURIComponent(created.run_id)}`)
    },
    onError: (caught) =>
      setError(
        caught instanceof ApiError
          ? ({
              413: 'This file exceeds 8 MiB. Choose a smaller PDF.',
              415: 'Choose a PDF with the application/pdf file type.',
              400: 'The upload was rejected. Choose one readable PDF.',
              403: 'New invoice uploads are disabled or unavailable from this page. Existing runs are still available.',
              408: 'The upload timed out. Choose the PDF and try again.',
              429: 'The demo is at invoice capacity. Wait for an active run to finish before uploading.',
            }[caught.status] ??
              'The invoice could not be uploaded. Try again; no run was confirmed.')
          : 'The upload could not reach the server. Check the connection and try again.',
      ),
  })
  useEffect(() => {
    if (error) errorRef.current?.focus()
  }, [error])
  const choose = (files: File[]) => {
    if (mutation.isPending) return
    setError('')
    setFile(null)
    mutation.reset()
    if (files.length !== 1) {
      setError('Choose one PDF at a time.')
      return
    }
    const selected = files[0]
    if (selected.type !== 'application/pdf') {
      setError('Choose a PDF with the application/pdf file type.')
      return
    }
    if (!selected.size) {
      setError('This PDF is empty. Choose a readable invoice.')
      return
    }
    if (selected.size > 8 * 1024 * 1024) {
      setError('This file exceeds 8 MiB. Choose a smaller PDF.')
      return
    }
    setFile(selected)
  }
  return (
    <section
      id="upload"
      className={`upload-panel ${compact ? 'compact' : ''} ${drag ? 'dragging' : ''}`}
      aria-labelledby={id}
      onDragOver={(e) => {
        e.preventDefault()
        if (!mutation.isPending) setDrag(true)
      }}
      onDragLeave={(e) => {
        if (!(e.relatedTarget instanceof Node) || !e.currentTarget.contains(e.relatedTarget))
          setDrag(false)
      }}
      onDrop={(e) => {
        e.preventDefault()
        setDrag(false)
        choose(Array.from(e.dataTransfer.files))
      }}
    >
      <div className="upload-heading">
        <Upload size={22} aria-hidden="true" />
        <div>
          <h2 id={id}>Process an invoice</h2>
          <p>One PDF. A clear decision and next step.</p>
        </div>
      </div>
      <input
        ref={input}
        type="file"
        accept="application/pdf"
        aria-label="Invoice PDF"
        hidden
        disabled={mutation.isPending}
        onChange={(e) => {
          choose(Array.from(e.target.files ?? []))
          e.currentTarget.value = ''
        }}
      />
      {file ? (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (!mutation.isPending) mutation.mutate(file)
          }}
        >
          <div className="selected-file">
            <FileText size={20} aria-hidden="true" />
            <span>
              <strong>{file.name}</strong>
              <small>PDF, {fileSize(file.size)}</small>
            </span>
            <button
              type="button"
              className="icon-button"
              aria-label="Remove selected PDF"
              disabled={mutation.isPending}
              onClick={() => {
                setFile(null)
                setError('')
                mutation.reset()
              }}
            >
              <X size={18} aria-hidden="true" />
            </button>
          </div>
          <button
            type="submit"
            className="button primary"
            disabled={mutation.isPending}
            aria-busy={mutation.isPending}
          >
            {mutation.isPending ? (
              <LoaderCircle size={18} className="spin" aria-hidden="true" />
            ) : (
              <Upload size={18} aria-hidden="true" />
            )}
            {mutation.isPending ? 'Uploading…' : 'Process invoice'}
          </button>
        </form>
      ) : (
        <div className="drop-copy">
          <p>Drop an invoice here, or choose a file.</p>
          <button type="button" className="button primary" onClick={() => input.current?.click()}>
            Choose PDF
            <Upload size={17} aria-hidden="true" />
          </button>
        </div>
      )}
      {error && (
        <p className="inline-error" role="alert" tabIndex={-1} ref={errorRef}>
          {error}
        </p>
      )}
      <p className="upload-help" aria-live="polite">
        {mutation.isPending
          ? 'Sending your PDF. Processing begins after the server accepts it.'
          : 'PDF only, up to 8 MiB. The server validates every upload.'}
      </p>
    </section>
  )
}
export function RunTable({ runs }: { runs: RunSummary[] }) {
  const navigate = useNavigate()
  return (
    <div className="table-scroll">
      <table>
        <caption className="sr-only">
          Invoice operations, newest first. Amounts are invoice totals including tax. Recorded
          automated outcomes and current reviewed assessments are labelled separately.
        </caption>
        <thead>
          <tr>
            <th scope="col">Invoice / supplier</th>
            <th scope="col" className="numeric">
              Invoice total
            </th>
            <th scope="col">Status</th>
            <th scope="col">Primary issue / outcome</th>
            <th scope="col">Owner</th>
            <th scope="col">Updated</th>
            <th scope="col">
              <span className="sr-only">Open invoice</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.id}
              onClick={(e) => {
                if (
                  e.target instanceof Element &&
                  !e.target.closest('a,button') &&
                  !window.getSelection()?.toString()
                )
                  navigate(`/runs/${run.id}`)
              }}
            >
              <td>
                <Link className="invoice-link" to={`/runs/${run.id}`}>
                  {run.invoice_number || `Invoice ${run.id.slice(0, 8)}`}
                </Link>
                <span className="table-secondary">
                  {run.vendor_name || 'Supplier pending extraction'}
                </span>
              </td>
              <td className="numeric amount">
                {money(run.total, run.currency)}
                <span className="table-secondary">{run.currency ?? 'Currency pending'}</span>
              </td>
              <td>
                {run.reviewed_outcome && (
                  <span className="table-secondary">Original automated</span>
                )}
                <Status state={run.execution_state} outcome={run.outcome} />
                {run.reviewed_outcome && (
                  <div className="table-reviewed">
                    <span className="table-secondary">Current reviewed</span>
                    <Status state="COMPLETED" outcome={run.reviewed_outcome} />
                  </div>
                )}
              </td>
              <td className="issue-cell">
                {run.execution_state === 'PROCESSING_FAILED'
                  ? 'No AP decision produced'
                  : run.execution_state === 'INTERRUPTED'
                    ? 'Processing interrupted'
                    : active(run.execution_state)
                      ? 'Analysis in progress'
                      : reasonLabel(run.primary_reason_code)}
              </td>
              <td>{run.owner ?? '—'}</td>
              <td>
                <time dateTime={run.updated_at} title={date(run.updated_at, true)}>
                  {relative(run.updated_at)}
                </time>
              </td>
              <td>
                <Link
                  className="icon-button"
                  to={`/runs/${run.id}`}
                  aria-label={`Open ${run.invoice_number ?? 'invoice ' + run.id.slice(0, 8)}`}
                >
                  <ArrowUpRight size={18} aria-hidden="true" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
export function CheckNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="check-note">
      <Check size={16} aria-hidden="true" />
      {children}
    </p>
  )
}
