import { createContext, useContext, useEffect, useId, useRef, useState } from 'react'
import type { DragEvent, ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowUpRight, Files, FileText, LoaderCircle, Upload, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from './api'
import { Status } from './components'
import { fileSize, words } from './format'
import { active } from './queries'
import type { ExecutionState, Outcome } from './types'
import { uploadError, validatePdf } from './uploadValidation'

const LIMIT = 10
const POLL_INTERVAL_MS = 1000
const WAIT_LIMIT_MS = 5 * 60_000

type AcceptedRun = {
  id: string
  state: ExecutionState
  outcome?: Outcome
  errorCode?: string
}

type Entry = { key: number; file: File } & (
  | { phase: 'waiting' | 'uploading' }
  | { phase: 'upload-failed'; message: string }
  | { phase: 'accepted'; run: AcceptedRun }
)

const settled = (entry: Entry) =>
  entry.phase === 'upload-failed' || (entry.phase === 'accepted' && !active(entry.run.state))
const identify = (file: File) => JSON.stringify([file.name, file.size, file.lastModified])
const delay = () => new Promise<void>((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS))
const batchOutcomes = [
  { outcome: 'READY_FOR_AP', label: 'Ready' },
  { outcome: 'REVIEW_REQUIRED', label: 'Review' },
  { outcome: 'BLOCKED', label: 'Blocked' },
] as const

function useBatchState() {
  const queryClient = useQueryClient()
  const [entries, setEntries] = useState<Entry[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const [started, setStarted] = useState(false)
  const [busy, setBusy] = useState(false)
  const [paused, setPaused] = useState(false)
  const locked = useRef(false)
  const nextKey = useRef(0)

  function add(files: File[]) {
    if (started || locked.current) return
    const identifiers = new Set(entries.map((entry) => identify(entry.file)))
    const accepted: Entry[] = []
    const rejected: string[] = []
    for (const file of files) {
      const problem = validatePdf(file)
      if (problem) {
        rejected.push(file.name + ' · ' + problem)
        continue
      }
      const fingerprint = identify(file)
      if (identifiers.has(fingerprint)) {
        rejected.push(file.name + ' is already selected.')
        continue
      }
      if (entries.length + accepted.length === LIMIT) {
        rejected.push('Select up to ' + LIMIT + ' PDFs per batch.')
        break
      }
      identifiers.add(fingerprint)
      accepted.push({ key: nextKey.current++, file, phase: 'waiting' })
    }
    setEntries([...entries, ...accepted])
    setErrors(rejected)
  }

  function remove(key: number) {
    if (started || locked.current) return
    setEntries((current) => current.filter((entry) => entry.key !== key))
    setErrors([])
  }

  async function process() {
    if (locked.current || !entries.some((entry) => !settled(entry))) return
    locked.current = true
    setStarted(true)
    setBusy(true)
    setPaused(false)
    setErrors([])
    const update = (updated: Entry) =>
      setEntries((current) => current.map((entry) => (entry.key === updated.key ? updated : entry)))
    const refresh = () => {
      void queryClient.invalidateQueries({ queryKey: ['runs'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    }
    try {
      for (const entry of entries) {
        if (settled(entry)) continue
        const base = { key: entry.key, file: entry.file }
        let run: AcceptedRun
        if (entry.phase === 'accepted') {
          run = entry.run
        } else {
          update({ ...base, phase: 'uploading' })
          try {
            const accepted = await api.upload(entry.file)
            run = { id: accepted.run_id, state: accepted.execution_state }
          } catch (error) {
            update({ ...base, phase: 'upload-failed', message: uploadError(error) })
            continue
          }
          update({ ...base, phase: 'accepted', run })
          refresh()
        }
        const deadline = Date.now() + WAIT_LIMIT_MS
        let readFailures = 0
        while (active(run.state) && Date.now() < deadline && readFailures < 5) {
          try {
            const snapshot = await api.run(run.id, AbortSignal.timeout(10_000))
            run = {
              id: run.id,
              state: snapshot.execution_state,
              outcome: snapshot.decision?.outcome,
              errorCode: snapshot.execution_error_code ?? undefined,
            }
            readFailures = 0
            update({ ...base, phase: 'accepted', run })
          } catch {
            readFailures += 1
          }
          if (active(run.state) && readFailures < 5) await delay()
        }
        if (active(run.state)) {
          setPaused(true)
          return
        }
        refresh()
      }
    } finally {
      locked.current = false
      setBusy(false)
    }
  }

  function reset() {
    if (locked.current || entries.some((entry) => !settled(entry))) return
    setEntries([])
    setStarted(false)
    setPaused(false)
    setErrors([])
  }

  return {
    entries,
    errors,
    started,
    busy,
    paused,
    add,
    remove,
    process,
    reset,
  }
}

const BatchContext = createContext<ReturnType<typeof useBatchState> | null>(null)

export function BatchUploadProvider({ children }: { children: ReactNode }) {
  const batch = useBatchState()
  return <BatchContext.Provider value={batch}>{children}</BatchContext.Provider>
}

export default function BatchUpload({ launch = false }: { launch?: boolean }) {
  const batch = useContext(BatchContext)
  const input = useRef<HTMLInputElement>(null)
  const choose = useRef<HTMLButtonElement>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const focusAfterAction = useRef(false)
  const label = useId()
  const [dragging, setDragging] = useState(false)
  const [departing, setDeparting] = useState<Entry[]>([])
  const started = batch?.started ?? false
  useEffect(() => {
    if (!focusAfterAction.current) return
    focusAfterAction.current = false
    if (started) heading.current?.focus()
    else choose.current?.focus()
  }, [started])
  if (!batch) throw new Error('Batch upload requires its application provider')
  const { entries, errors, busy, paused, add, remove, process, reset } = batch
  const finished = entries.filter(settled)
  const outcomes = batchOutcomes.map(({ outcome, label }) => ({
    outcome,
    label,
    count: finished.filter((entry) => entry.phase === 'accepted' && entry.run.outcome === outcome)
      .length,
  }))
  const withoutDecision = finished.length - outcomes.reduce((sum, result) => sum + result.count, 0)

  const dropHandlers = {
    onDragOver(event: DragEvent<HTMLElement>) {
      event.preventDefault()
      if (!started) setDragging(true)
    },
    onDragLeave(event: DragEvent<HTMLElement>) {
      if (
        !(event.relatedTarget instanceof Node) ||
        !event.currentTarget.contains(event.relatedTarget)
      ) {
        setDragging(false)
      }
    },
    onDrop(event: DragEvent<HTMLElement>) {
      event.preventDefault()
      setDragging(false)
      add(Array.from(event.dataTransfer.files))
    },
  }

  const fileWarnings = errors.length > 0 && (
    <ul className="inline-error batch-errors" role="alert">
      {errors.map((error, index) => (
        <li key={index}>{error}</li>
      ))}
    </ul>
  )
  const files = (
    <>
      {!launch && fileWarnings}
      {(entries.length > 0 || (!started && departing.length > 0)) && (
        <ul
          className="batch-list"
          aria-label={started ? 'Individual invoice results' : 'Selected invoices'}
        >
          {[...entries, ...(started ? [] : departing)]
            .sort((left, right) => left.key - right.key)
            .map((entry) => {
              const leaving = departing.some((file) => file.key === entry.key)
              return (
                <li
                  key={entry.key}
                  data-phase={entry.phase}
                  data-leaving={leaving || undefined}
                  inert={leaving || undefined}
                  aria-hidden={leaving || undefined}
                  onAnimationEnd={
                    leaving
                      ? () =>
                          setDeparting((current) =>
                            current.filter((file) => file.key !== entry.key),
                          )
                      : undefined
                  }
                  data-state={entry.phase === 'accepted' ? entry.run.state : undefined}
                >
                  <span className="intake-file-icon">
                    {launch && entry.phase === 'uploading' ? (
                      <LoaderCircle className="composer-spinner" size={18} aria-hidden="true" />
                    ) : (
                      <FileText size={18} aria-hidden="true" />
                    )}
                  </span>
                  <div className="batch-file">
                    <strong title={launch && !started ? entry.file.name : undefined}>
                      {entry.file.name}
                    </strong>
                    <small>{fileSize(entry.file.size)}</small>
                    {entry.phase === 'upload-failed' && (
                      <p className="batch-item-error">{entry.message}</p>
                    )}
                    {entry.phase === 'accepted' && entry.run.errorCode && (
                      <p className="batch-item-error">{words(entry.run.errorCode)}</p>
                    )}
                  </div>
                  {!started ? (
                    <button
                      type="button"
                      className="icon-button"
                      aria-label={'Remove ' + entry.file.name}
                      onClick={() => {
                        if (
                          launch &&
                          window.matchMedia?.('(prefers-reduced-motion: no-preference)').matches
                        ) {
                          setDeparting((current) => [...current, entry])
                        }
                        remove(entry.key)
                        choose.current?.focus()
                      }}
                    >
                      <X size={18} aria-hidden="true" />
                    </button>
                  ) : (
                    <div className="batch-state">
                      {entry.phase === 'accepted' ? (
                        <>
                          <Status state={entry.run.state} outcome={entry.run.outcome} />
                          <Link
                            className="text-link"
                            to={'/runs/' + encodeURIComponent(entry.run.id)}
                            aria-label={'Open ' + entry.file.name}
                          >
                            Open invoice <ArrowUpRight size={15} aria-hidden="true" />
                          </Link>
                        </>
                      ) : (
                        <span
                          className={entry.phase === 'upload-failed' ? 'status failed' : 'status'}
                        >
                          {entry.phase === 'upload-failed'
                            ? 'Upload failed'
                            : entry.phase === 'uploading'
                              ? 'Uploading'
                              : 'Waiting'}
                        </span>
                      )}
                    </div>
                  )}
                </li>
              )
            })}
        </ul>
      )}
    </>
  )

  return (
    <div className={launch ? 'launch-batch' : 'ops-page batch-page'}>
      {!launch && (
        <>
          <Link className="text-link batch-back" to="/runs">
            <ArrowLeft size={16} aria-hidden="true" /> Invoice Operations
          </Link>
          <header className="page-heading ops-heading intake-heading">
            <div>
              <h1>Process invoices</h1>
              <p>
                Submit up to 10 PDFs in one batch. Open each invoice to see its own decision and
                source.
              </p>
            </div>
          </header>
        </>
      )}
      <div className={launch ? 'intake-desk launch-intake' : 'intake-desk'}>
        <section
          className="intake-console"
          aria-label={launch ? 'Invoice intake' : 'Batch controls'}
          data-dragging={launch && dragging ? true : undefined}
          {...(launch ? dropHandlers : {})}
          data-started={launch ? started : undefined}
        >
          <div className="intake-console-heading">
            {started ? (
              <h2 ref={heading} tabIndex={-1}>
                {paused ? 'Status checks paused' : busy ? 'Batch in progress' : 'Batch complete'}
              </h2>
            ) : (
              <h2>{launch ? 'Start a review' : 'Add invoice PDFs'}</h2>
            )}
          </div>
          {started && (
            <>
              <p className="intake-count" role="status">
                {finished.length} of {entries.length} finished
              </p>
              <dl className="intake-outcomes" aria-label="Recorded batch outcomes">
                {outcomes.map(({ outcome, label, count }) => (
                  <div key={outcome} data-outcome={outcome}>
                    <dt>{label}</dt>
                    <dd>{count}</dd>
                  </div>
                ))}
              </dl>
              {withoutDecision > 0 && (
                <p className="intake-note">{withoutDecision} finished without an AP decision.</p>
              )}
            </>
          )}
          {!started && (
            <div
              className={dragging ? 'batch-drop dragging' : 'batch-drop'}
              {...(!launch ? dropHandlers : {})}
            >
              <Files size={26} aria-hidden="true" />
              <div>
                <strong>{dragging ? 'Release to add PDFs' : 'Drop invoice PDFs here'}</strong>
                <p aria-live={launch ? 'polite' : undefined}>
                  {launch
                    ? entries.length
                      ? `${entries.length} ${entries.length === 1 ? 'PDF' : 'PDFs'} attached`
                      : 'Up to 10 PDFs, 8 MiB each.'
                    : 'Up to 8 MiB per file. Processed one at a time.'}
                </p>
              </div>
              <input
                type="file"
                accept="application/pdf"
                multiple
                hidden
                ref={input}
                aria-label="Invoice PDFs"
                onChange={(event) => {
                  add(Array.from(event.currentTarget.files ?? []))
                  event.currentTarget.value = ''
                }}
              />
              <button
                type="button"
                className="button secondary"
                ref={choose}
                onClick={() => input.current?.click()}
              >
                <Upload size={17} aria-hidden="true" /> Choose PDFs
              </button>
            </div>
          )}
          {launch && files}
          {launch && !started && (entries.length > 0 || errors.length > 0) && (
            <section className="intake-readiness" aria-labelledby={label + '-readiness'}>
              <h3 id={label + '-readiness'}>Intake readiness</h3>
              <dl>
                <div>
                  <dt>Selected PDFs</dt>
                  <dd>{entries.length}</dd>
                </div>
                <div>
                  <dt>Total size</dt>
                  <dd>{fileSize(entries.reduce((total, { file }) => total + file.size, 0))}</dd>
                </div>
                <div>
                  <dt>Valid files</dt>
                  <dd>{entries.length}</dd>
                </div>
              </dl>
              <p role="status">
                {entries.length ? 'Ready to submit.' : 'Choose a valid PDF to continue.'}
                {errors.length > 0 && ' Files listed below were not added.'}
              </p>
              {fileWarnings}
            </section>
          )}
          {paused && (
            <p className="inline-error intake-error" role="alert">
              The last accepted invoice’s status is unavailable. Resume status checks to continue
              without uploading it again.
            </p>
          )}
          <div className="batch-actions">
            {!started && (
              <button
                type="button"
                className="button primary"
                disabled={!entries.length}
                onClick={() => {
                  focusAfterAction.current = true
                  setDeparting([])
                  void process()
                }}
              >
                {launch
                  ? entries.length
                    ? `Process ${entries.length} ${entries.length === 1 ? 'invoice' : 'invoices'}`
                    : 'Process invoices'
                  : 'Process selected invoices'}
              </button>
            )}
            {busy && <p className="intake-note">Keep this tab open while the batch runs.</p>}
            {launch && busy && (
              <button type="button" className="button primary" disabled>
                <LoaderCircle className="composer-spinner" size={16} aria-hidden="true" />
                Processing invoices
              </button>
            )}
            {paused && (
              <button type="button" className="button primary" onClick={() => void process()}>
                Resume status checks
              </button>
            )}
            {started && !busy && !paused && (
              <button
                type="button"
                className="button secondary"
                onClick={() => {
                  focusAfterAction.current = true
                  reset()
                }}
              >
                Start another batch
              </button>
            )}
            {started && (
              <Link className="button secondary" to="/runs">
                View invoice queue
              </Link>
            )}
          </div>
        </section>
        {!launch && (
          <section className="ops-card batch-card" aria-labelledby={label}>
            <div className="batch-heading">
              <h2 id={label}>{started ? 'Invoice results' : 'Selected PDFs'}</h2>
              <span>
                {started ? `${entries.length} invoices` : `${entries.length} of ${LIMIT} selected`}
              </span>
            </div>
            {!entries.length && (
              <p className="intake-empty">Add PDFs to check the list before processing.</p>
            )}
            {files}
          </section>
        )}
      </div>
    </div>
  )
}
