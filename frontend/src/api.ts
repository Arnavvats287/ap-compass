import type {
  ReviewAction,
  ReviewHistory,
  POConfirmationInput,
  Dashboard,
  Run,
  RunSummary,
  PolicyPreview,
  PriceTolerance,
  ExecutionState,
  Outcome,
} from './types'

export class ApiError extends Error {
  constructor(public status: number) {
    super(status === 404 ? 'Not found' : 'Request failed')
  }
}
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, options)
  if (!response.ok) throw new ApiError(response.status)
  return response.json() as Promise<T>
}
export const api = {
  reviewHistory: (id: string, signal?: AbortSignal) =>
    request<ReviewHistory>(`/runs/${encodeURIComponent(id)}/review-history`, { signal }),
  confirmPO: (id: string, body: POConfirmationInput) =>
    request<ReviewAction>(`/runs/${encodeURIComponent(id)}/po-confirmations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  dashboard: (signal?: AbortSignal) => request<Dashboard>('/dashboard', { signal }),
  runs: (signal?: AbortSignal) => request<RunSummary[]>('/runs?limit=100', { signal }),
  run: (id: string, signal?: AbortSignal) =>
    request<Run>(`/runs/${encodeURIComponent(id)}`, { signal }),
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<{
      run_id: string
      execution_state: ExecutionState
      reused?: boolean
      outcome?: Outcome | null
    }>('/runs', {
      method: 'POST',
      body: form,
    })
  },
  exportInvoices: async () => {
    const response = await fetch('/api/exports/invoices.xlsx', { cache: 'no-store' })
    if (!response.ok) throw new ApiError(response.status)
    if (
      response.headers.get('content-type') !==
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
      throw new Error('Unexpected export format')
    const blob = await response.blob()
    const signature = new Uint8Array(await blob.slice(0, 4).arrayBuffer())
    if (signature.join(',') !== '80,75,3,4') throw new Error('Invalid workbook')
    const filename =
      response.headers
        .get('content-disposition')
        ?.match(/filename="(ap-compass-invoice-register-\d{4}-\d{2}-\d{2}\.xlsx)"/)?.[1] ??
      'ap-compass-invoice-register.xlsx'
    return { blob, filename }
  },
  documentUrl: (id: string) => `/api/runs/${encodeURIComponent(id)}/document`,
  preview: (id: string, tolerance: PriceTolerance) =>
    request<PolicyPreview>(`/runs/${encodeURIComponent(id)}/policy-preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ price_tolerance_pct: tolerance }),
    }),
}
