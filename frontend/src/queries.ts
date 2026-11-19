import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import type { ExecutionState } from './types'
export const active = (state?: ExecutionState) => state === 'QUEUED' || state === 'RUNNING'
export const detailInterval = (state?: ExecutionState) => (active(state) ? 1000 : false)
export function useRuns() {
  return useQuery({
    queryKey: ['runs'],
    queryFn: ({ signal }) => api.runs(signal),
    refetchInterval: (query) =>
      query.state.data?.some((run) => active(run.execution_state)) ? 1000 : false,
  })
}
export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: ({ signal }) => api.dashboard(signal),
    refetchInterval: (query) => (query.state.data?.in_progress ? 1000 : false),
  })
}
export function useRun(id: string) {
  const client = useQueryClient()
  const announced = useRef<string | null>(null)
  const query = useQuery({
    queryKey: ['run', id],
    queryFn: ({ signal }) => api.run(id, signal),
    enabled: !!id,
    refetchInterval: (query) => detailInterval(query.state.data?.execution_state),
    refetchOnWindowFocus: (query) => active(query.state.data?.execution_state),
    retry: false,
  })
  useEffect(() => {
    if (query.data && !active(query.data.execution_state) && announced.current !== id) {
      announced.current = id
      void client.invalidateQueries({ queryKey: ['runs'] })
      void client.invalidateQueries({ queryKey: ['dashboard'] })
    }
  }, [query.data, id, client])
  return query
}
