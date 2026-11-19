import type { Dashboard, Run, RunSummary, PolicyPreview, PriceTolerance } from './types'

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
  dashboard: (signal?: AbortSignal) => request<Dashboard>('/dashboard', { signal }),
  runs: (signal?: AbortSignal) => request<RunSummary[]>('/runs?limit=100', { signal }),
  run: (id: string, signal?: AbortSignal) =>
    request<Run>(`/runs/${encodeURIComponent(id)}`, { signal }),
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<{ run_id: string; execution_state: 'QUEUED' }>('/runs', {
      method: 'POST',
      body: form,
    })
  },
  documentUrl: (id: string) => `/api/runs/${encodeURIComponent(id)}/document`,
  preview: (id: string, tolerance: PriceTolerance) =>
    request<PolicyPreview>(`/runs/${encodeURIComponent(id)}/policy-preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ price_tolerance_pct: tolerance }),
    }),
}
