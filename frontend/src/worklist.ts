import type { RunSummary } from './types'

const supplierOrder = new Intl.Collator('en', { sensitivity: 'base', numeric: true })
const compareText = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0)
const compareSupplier = (a: string, b: string) => supplierOrder.compare(a, b) || compareText(a, b)

export const isAttention = (run: RunSummary) =>
  run.outcome === 'BLOCKED' || run.outcome === 'REVIEW_REQUIRED'
export const newestFirst = (a: RunSummary, b: RunSummary) =>
  Date.parse(b.updated_at) - Date.parse(a.updated_at) || compareText(a.id, b.id)
export const invoiceUrl = (id: string) => '/runs/' + encodeURIComponent(id)

export function attentionRuns(runs: RunSummary[]) {
  return runs
    .filter(isAttention)
    .sort(
      (a, b) =>
        Number(b.outcome === 'BLOCKED') - Number(a.outcome === 'BLOCKED') || newestFirst(a, b),
    )
}

export function rankVendors(runs: RunSummary[]) {
  const counts = new Map<string, number>()
  for (const run of runs) {
    const name = run.vendor_name
    if (name?.trim() && isAttention(run)) counts.set(name, (counts.get(name) ?? 0) + 1)
  }
  return Array.from(counts, ([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || compareSupplier(a.name, b.name))
    .slice(0, 10)
}

export const sortChoices = [
  ['latest', 'Newest first'],
  ['oldest', 'Oldest first'],
  ['supplier', 'Supplier A–Z'],
] as const

export function sortRuns(runs: RunSummary[], sort: string) {
  return [...runs].sort((a, b) => {
    if (sort === 'oldest') return -newestFirst(a, b)
    if (sort === 'supplier') {
      if (!a.vendor_name || !b.vendor_name)
        return Number(!a.vendor_name) - Number(!b.vendor_name) || newestFirst(a, b)
      return compareSupplier(a.vendor_name, b.vendor_name) || newestFirst(a, b)
    }
    return newestFirst(a, b)
  })
}
