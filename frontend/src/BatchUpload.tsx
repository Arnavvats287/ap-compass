import { createContext, useContext, useId, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowUpRight, FileText, Upload, X } from 'lucide-react'
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

  return { entries, errors, started, busy, paused, add, remove, process, reset }
}

const BatchContext = createContext<ReturnType<typeof useBatchState> | null>(null)

export function BatchUploadProvider({ children }: { children: ReactNode }) {
  const batch = useBatchState()
  return <BatchContext.Provider value={batch}>{children}</BatchContext.Provider>
}

export default function BatchUpload() {
  const batch = useContext(BatchContext)
  const input = useRef<HTMLInputElement>(null)
  const choose = useRef<HTMLButtonElement>(null)
  const label = useId()
  const [dragging, setDragging] = useState(false)
  if (!batch) throw new Error('Batch upload requires its application provider')
  const { entries, errors, started, busy, paused, add, remove, process, reset } = batch
  const finished = entries.filter(settled).length

  return (
    <div className="ops-page batch-page">
      <Link className="text-link batch-back" to="/runs">
        <ArrowLeft size={16} aria-hidden="true" /> Invoice Operations
      </Link>
      <header className="page-heading ops-heading">
        <div>
          <h1>Process invoices</h1>
          <p>Submit up to 10 PDFs. Each invoice keeps its own decision and source record.</p>
        </div>
      </header>
      <section className="ops-card batch-card" aria-labelledby={label}>
        <div className="batch-heading">
          <h2 id={label}>{started ? 'Batch results' : 'Select invoice PDFs'}</h2>
          {started && (
            <p role="status">
              {finished} of {entries.length} finished
            </p>
          )}
        </div>
        {!started && (
          <div
            className={dragging ? 'batch-drop dragging' : 'batch-drop'}
            onDragOver={(event) => {
              event.preventDefault()
              setDragging(true)
            }}
            onDragLeave={(event) => {
              if (
                !(event.relatedTarget instanceof Node) ||
                !event.currentTarget.contains(event.relatedTarget)
              )
                setDragging(false)
            }}
            onDrop={(event) => {
              event.preventDefault()
              setDragging(false)
              add(Array.from(event.dataTransfer.files))
            }}
          >
            <div>
              <strong>Drop invoice PDFs here</strong>
              <p>Up to 8 MiB per file. AP Compass processes them one at a time.</p>
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
        {errors.length > 0 && (
          <ul className="inline-error batch-errors" role="alert">
            {errors.map((error, index) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
        )}
        {entries.length > 0 && (
          <ul
            className="batch-list"
            aria-label={started ? 'Individual invoice results' : 'Selected invoices'}
          >
            {entries.map((entry) => (
              <li key={entry.key}>
                <FileText size={20} aria-hidden="true" />
                <div className="batch-file">
                  <strong>{entry.file.name}</strong>
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
            ))}
          </ul>
        )}
        {paused && (
          <p className="inline-error" role="alert">
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
              onClick={() => void process()}
            >
              Process selected invoices
            </button>
          )}
          {busy && <p>Keep this tab open while the batch runs.</p>}
          {paused && (
            <button type="button" className="button primary" onClick={() => void process()}>
              Resume status checks
            </button>
          )}
          {started && !busy && !paused && (
            <button type="button" className="button secondary" onClick={reset}>
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
    </div>
  )
}
