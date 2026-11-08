export type RouteName =
  | 'HOLD_FOR_HUMAN_HANDLING'
  | 'FAST_TRACK_CANDIDATE'
  | 'STANDARD_REVIEW'
  | 'ENHANCED_REVIEW'

export type CaseRecord = {
  application_id: string
  borrower_label: string
  merchant: string
  purchase_description: string
  purchase_amount_vnd: number
  loan_amount_vnd: number
  own_funds_vnd?: number | null
  proposed_installment_vnd: number
  term_months?: number
  annual_interest_rate?: number
  submitted_at: string
  consent: boolean
  consent_revoked_at?: string
  identity_verified: boolean
  source_permission: boolean
  funding_reconciled: boolean
  existing_monthly_debt_vnd: number
  essential_monthly_expenses_vnd: number
  monthly_income_vnd: number[]
  evidence: {
    reconciliation_fields_consistent: number
    reconciliation_fields_total: number
    verified_sources: number
    available_sources: number
    age_days: number
    sources: { name: string; type: string; months: number; verified: boolean; permission: string }[]
    reconciliation_notes: string[]
  }
  tags: string[]
  assessment: Assessment
  routing: Routing
  review_history: AuditEvent[]
}

export type Assessment = {
  policy_version: string
  fixture_version: string
  risk_source: 'SYNTHETIC_HEURISTIC' | 'PUBLIC_BENCHMARK_ONLY' | 'APPLICATION_COMPATIBLE_VALIDATED' | 'UNAVAILABLE'
  pd_status: string
  checkout_pd: null
  model: { version: string | null; scope: string }
  status: string
  scoring_performed: boolean
  notice?: string
  gates: { key: string; label: string; passed: boolean; mandatory: boolean }[]
  features: Record<string, number> | null
  confidence: {
    score: number
    label: string
    subscores: Record<string, number>
    weights: Record<string, number>
    weighted_contributions: Record<string, number>
    inputs: Record<string, number>
    completeness_gaps: Record<string, number>
  } | null
  risk: {
    score: number
    label: string
    calibration_status: string
    reference_parity: string
    model_type: string
    formula: string
    intercept: number
    slopes: Record<string, number>
    linear_terms: Record<string, number>
    logit: number
    source_note: string
  } | null
  affordability: {
    income_residual_vnd: number
    stress_income_vnd: number
    dti_capacity_vnd: number
    residual_capacity_vnd: number
    residual_buffer_assumption: number
    installment_basis: string
    stated_installment_differs_from_pmt: boolean
    stressed_payment_capacity_vnd: number
    repayment_buffer_vnd: number
    installment_eligible: boolean
    proposed_installment_vnd: number
    max_dti_assumption: number
    essential_monthly_expenses_vnd: number
    pmt_vnd: number | null
    pmt_calculation: string
    calculation: string
  } | null
  expected_loss: {
    status: string
    sensitivity: { lgd: number; ead_vnd: number; amount_vnd: number }[]
    amount_vnd: number
    pd_demo: number
    lgd_assumption: number
    ead_assumption_vnd: number
    calculation: string
  } | null
  human_decision_required?: boolean
}

export type Routing = {
  eligible_routes: RouteName[]
  recommended_route: RouteName
  human_confirmation_required: boolean
  loan_approval_available: boolean
  policy_status: string
  objective: string
  estimated_route_costs_vnd: Record<RouteName, number>
  route_comparison: { route: RouteName; eligible: boolean; estimated_cost_vnd: number; selected: boolean; reason: string }[]
  explanations: string[]
}

export type AuditEvent = {
  event_id: number
  action: string
  route: RouteName | null
  reason: string
  actor: string
  created_at: string
  details: Record<string, unknown>
}

export type PortfolioMetrics = {
  synthetic_operational_snapshot: boolean
  interpretation: string
  application_count: number
  scoreable_count: number
  blocked_count: number
  route_distribution: Record<RouteName, number>
  mean_confidence_index: number | null
  mean_demo_pd: number | null
  proposed_routing_cost_estimate_vnd: number
  baseline_all_standard_cost_estimate_vnd: number
  estimated_cost_difference_vnd: number
  baseline_note: string
}
