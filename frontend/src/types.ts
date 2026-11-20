export type ExecutionState =
  'QUEUED' | 'RUNNING' | 'COMPLETED' | 'PROCESSING_FAILED' | 'INTERRUPTED'
export type Outcome = 'READY_FOR_AP' | 'REVIEW_REQUIRED' | 'BLOCKED'
export type EvidenceState = 'NATIVE_VERIFIED' | 'SOURCE_LOCATED_UNVERIFIED' | 'MISSING'
export type StageState = 'QUEUED' | 'RUNNING' | 'PASSED' | 'WARNING' | 'FAILED' | 'SKIPPED'
export interface Evidence {
  field: string
  raw_value: string | null
  normalized_value: string | null
  page: number | null
  quote: string | null
  route: string | null
  evidence_state: EvidenceState
}
export interface Finding {
  code: string
  severity: 'BLOCK' | 'REVIEW' | 'PASS' | 'INFO'
  title: string
  explanation: string
  owner: string | null
  next_action: string | null
  values: { name: string; value: string | null }[]
  evidence_refs: Evidence[]
}
export interface Decision {
  outcome: Outcome
  findings: Finding[]
  primary_reason_code: string | null
  owner: string | null
  next_action: string | null
  policy_version: string
}
export interface Invoice {
  vendor_name_raw: string | null
  vendor_name_normalized: string | null
  invoice_number: string | null
  invoice_date: string | null
  po_reference: string | null
  currency: string | null
  net: string | null
  tax: string | null
  total: string | null
  lines: {
    description: string | null
    item_code: string | null
    qty: string | null
    unit_price_net: string | null
    net: string | null
  }[]
  evidence: Evidence[]
}
export interface Candidate {
  po: {
    id: string
    vendor_id: string
    authorized_net: string
    currency: string
    status: string
    lines?: { item_code: string }[]
  }
  selection_provenance: string
  rank: number | null
}
export interface Stage {
  name: string
  state: StageState
  started_at: string | null
  finished_at: string | null
}
export interface Run {
  id: string
  execution_state: ExecutionState
  execution_error_code: string | null
  decision: Decision | null
  extracted_invoice: Invoice | null
  candidates: Candidate[]
  document_id: string
  stages: Stage[]
  created_at: string
  updated_at: string
  source_route: string | null
  model_id: string | null
  extraction_schema_version: string | null
  policy_snapshot: { version: string; price_tolerance_pct?: string } | null
  timings: { name: string; milliseconds: number }[]
  usage: {
    model_calls: number | null
    input_tokens: number | null
    output_tokens: number | null
  } | null
}
export interface RunSummary {
  reviewed_outcome?: Outcome | null
  reviewed_at?: string | null
  review_action_id?: string | null
  id: string
  created_at: string
  updated_at: string
  execution_state: ExecutionState
  outcome: Outcome | null
  vendor_name: string | null
  invoice_number: string | null
  total: string | null
  currency: string | null
  primary_reason_code: string | null
  owner: string | null
}
export interface VendorAttention {
  name: string
  source_names: string[]
  review_count: number
  blocked_count: number
  gross_by_currency: Record<string, string>
  missing_gross_count: number
}
export interface Dashboard {
  vendor_attention: VendorAttention[]
  procurement_capacity: {
    po_id: string
    vendor_name: string
    status: string
    currency: string
    approved_net: string
    previously_billed_net: string | null
    remaining_net: string | null
  }[]
  exception_insights: { code: string; count: number }[]
  total_runs: number
  in_progress: number
  completed: number
  ready: number
  review_required: number
  blocked: number
  processing_failed: number
  interrupted: number
  flagged_invoice_net_by_currency?: Record<string, string>
  flagged_invoice_net_missing_count?: number
  invoice_gross?: Record<
    'submitted' | 'ready' | 'review_required' | 'blocked',
    {
      by_currency: Record<string, string>
      missing_count: number
    }
  >
}
export type PriceTolerance = '0.02' | '0.05'
export interface PolicyPreview {
  original_policy: { version: string; price_tolerance_pct: string }
  preview_policy: { version: string; price_tolerance_pct: string }
  original_decision: Decision
  preview_decision: Decision
  changed: boolean
}

export interface ReviewAction {
  id: string
  source_run_id: string
  client_action_id: string
  action_type: 'CONFIRM_PO'
  selected_po_id: string
  reviewer_label: string
  reviewer_identity: 'Demo reviewer — identity not authenticated'
  rationale: string
  created_at: string
  original_decision: Decision
  reassessment: Decision
  policy_snapshot: { version: string; price_tolerance_pct: string }
  authority_fingerprint: string
  source_snapshot_fingerprint: string
  selection_provenance: string
  canonical_vendor_name: string
}
export interface ReviewHistory {
  actions: ReviewAction[]
  current_reviewed_assessment: Decision | null
  confirmation_available: boolean
  unavailable_reason: string | null
  candidates: Candidate[]
  canonical_vendor_name: string | null
  authority_basis: string
}
export interface POConfirmationInput {
  po_id: string
  reviewer_label: string
  rationale: string
  client_action_id: string
}
