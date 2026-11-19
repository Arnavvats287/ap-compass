import { useRef, useState } from 'react'
import { Download } from 'lucide-react'
import { api, ApiError } from './api'

export default function ExportInvoices() {
  const busy = useRef(false)
  const [state, setState] = useState<'idle' | 'pending' | 'done'>('idle')
  const [error, setError] = useState('')

  async function download() {
    if (busy.current) return
    busy.current = true
    setState('pending')
    setError('')
    try {
      const { blob, filename } = await api.exportInvoices()
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename
      document.body.appendChild(anchor)
      try {
        anchor.click()
      } finally {
        anchor.remove()
        window.setTimeout(() => URL.revokeObjectURL(url), 15_000)
      }
      setState('done')
    } catch (caught) {
      setState('idle')
      setError(
        caught instanceof ApiError && [401, 403].includes(caught.status)
          ? 'Sign in to the active AP Compass instance and try again.'
          : 'Excel export could not be downloaded. Try again.',
      )
    } finally {
      busy.current = false
    }
  }

  return (
    <div className="export-invoices">
      <button
        className="button secondary"
        type="button"
        onClick={() => void download()}
        disabled={state === 'pending'}
        aria-busy={state === 'pending'}
        aria-describedby="export-scope"
      >
        <Download size={17} aria-hidden="true" />
        {state === 'pending' ? 'Preparing Excel…' : 'Export Excel'}
      </button>
      <small id="export-scope">Latest 100 invoices across all filters</small>
      {state === 'done' && <p role="status">Excel download started.</p>}
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
