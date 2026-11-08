import { useEffect, useState } from 'react'
import { request } from './api'
import './evidence-research-v41.css'

type Summary = {
  status: string
  validation_status: string
  routing_authorized: boolean
  approval_authorized: boolean
  read_only: boolean
  synthetic_only: boolean
  protocol_id: string
  dataset: { customer_groups: number; cases: number; documents: number; positive_material_documents: number; critical_documents: number }
  prediction_sha256: string
  model_manifest_sha256: string
  model_artifacts: Array<{ model: string; path: string; sha256: string }>
  frozen_threshold: number
  semantic_hybrid: Record<string, number | null>
  semantic_hybrid_group_bootstrap_95: Record<string, { lower_95: number | null; upper_95: number | null }>
  boundary_uncertainty: { c1_c3_c5_groups_with_legitimate_records: number; c1_c3_c5_group_any_fp_events: number; c1_c3_c5_one_sided_95_upper_bound_group_any_fp: number; c1_c3_c5_hoeffding_one_sided_95_ucb_equal_group_weighted_fpr: number }
  models: Record<string, { availability: string; metrics: Record<string, number | null> | null }>
  scenarios: Array<Record<string, string | number | null>>
  sources: Array<Record<string, string | number | null>>
  false_positive_breakdown: Array<{ scenario: string; false_positives: number; legitimate_support: number }>
  acceptance: Record<string, boolean | number | string | null>
  data_quality_audit: { stale_as_current_records: number; critical_labels_missing: number }
  label_rule_overlap: {
    classification: string
    interpretation: string
    shared_field_thresholds_vnd: Record<string, number>
    comparator_critical_delta_multiple: number
    generator_conflict_delta_multiples: Record<string, number[]>
    shared_stale_critical_age_days: number
    generator_c4_stale_record_age_days: number
    direct_hidden_gold_or_corruption_ids_used_as_predictor_inputs: boolean
  }
  artifacts: string[]
  figures: string[]
  limitations: string[]
}

const pct = (v: number | null | undefined, n = 1) => v == null ? '—' : `${(v * 100).toFixed(n)}%`
const num = (v: number | null | undefined, n = 3) => v == null ? '—' : v.toFixed(n)
const interval = (v?: { lower_95: number | null; upper_95: number | null }, asPercent = true) =>
  v?.lower_95 == null || v.upper_95 == null ? '-' : asPercent
    ? `[${pct(v.lower_95)}, ${pct(v.upper_95)}]`
    : `[${num(v.lower_95)}, ${num(v.upper_95)}]`

const metricLabels: Record<string, string> = {
  critical_recall: 'Critical recall',
  overall_legitimate_fpr: 'Overall legitimate-document FPR',
  legitimate_discrepancy_fpr_c1_c3_c5: 'C1/C3/C5 legitimate-discrepancy FPR',
  c4_stale_as_current_recall: 'C4 stale-as-current recall',
  case_review_workload: 'Case review workload',
  material_average_precision: 'Material-defect AP',
  brier_score: 'Brier score',
  log_loss: 'Log loss',
}

const modelLabels: Record<string, string> = {
  SEMANTIC_HYBRID: 'Semantic Hybrid', SEMANTIC_RULE: 'Semantic rule',
  SEMANTIC_LOGISTIC: 'Semantic Logistic Regression', SEMANTIC_DEEP_SETS: 'Semantic Deep Sets',
  ABLATION_NO_TEMPORAL: 'Without temporal features',
  ABLATION_NO_COMPARABILITY: 'Without comparability features',
  ABLATION_NO_SOURCE_PROVENANCE: 'Without source/provenance features',
  M0_CS_V2: 'CS_V2', M1_LOGISTIC: 'Frozen V4 Logistic Regression',
  M2_XGBOOST: 'Frozen XGBoost', M3_DEEP_SETS: 'Frozen V4 Deep Sets',
}

export function EvidenceResearchV41() {
  const [data, setData] = useState<Summary | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    request<Summary>('/evidence-ai/v4.1/summary').then(setData).catch(e => setError(e instanceof Error ? e.message : 'V4.1 summary unavailable'))
  }, [])

  if (error) return <section className="v41-sheet" aria-labelledby="v41-title"><p role="status">V4.1 read-only summary unavailable: {error}</p><p>Evidence outputs remain blocked for checkout use.</p></section>
  if (!data) return <section className="v41-sheet" aria-busy="true">Loading verified V4.1 research summary…</section>

  const hybrid = data.semantic_hybrid
  const intervals = data.semantic_hybrid_group_bootstrap_95
  const ablationNames = ['SEMANTIC_HYBRID', 'ABLATION_NO_TEMPORAL', 'ABLATION_NO_COMPARABILITY', 'ABLATION_NO_SOURCE_PROVENANCE']
  const baselineNames = ['M0_CS_V2', 'M1_LOGISTIC', 'M2_XGBOOST', 'M3_DEEP_SETS', 'SEMANTIC_RULE', 'SEMANTIC_LOGISTIC', 'SEMANTIC_DEEP_SETS']

  return <section className="v41-research" aria-labelledby="v41-title">
    <header className="v41-hero">
      <span>V4.1 · EVIDENCE AI RESEARCH</span>
      <h1 id="v41-title">Semantic-aware validation</h1>
      <p>Frozen Semantic Hybrid predictions reconciled against registered synthetic Generator C labels. Labels have been opened; this page reports exploratory measurements, not a fresh blind test.</p>
      <strong>{data.validation_status} · SYNTHETIC ONLY · READ ONLY</strong>
    </header>

    <section className="v41-panel">
      <div className="v41-section-head"><div><span>01 / STUDY RECORD</span><h2>Experiment overview</h2></div><b>{data.status.replaceAll('_', ' ')}</b></div>
      <div className="v41-counts">
        <div><small>Customer groups</small><strong>{data.dataset.customer_groups.toLocaleString()}</strong></div>
        <div><small>Cases</small><strong>{data.dataset.cases.toLocaleString()}</strong></div>
        <div><small>Documents</small><strong>{data.dataset.documents.toLocaleString()}</strong></div>
        <div><small>Protocol</small><strong>{data.protocol_id}</strong></div>
      </div>
      <p className="v41-hash"><b>Prediction SHA-256:</b> {data.prediction_sha256}</p>
      <p className="v41-hash"><b>Frozen model manifest SHA-256:</b> {data.model_manifest_sha256}</p>
      <details className="v41-artifact-list"><summary>Frozen model artifacts and hashes</summary><ul>{data.model_artifacts.map(item => <li key={item.model}><b>{modelLabels[item.model] ?? item.model}</b> · {item.path} · <code>{item.sha256}</code></li>)}</ul></details>
      <p>Frozen threshold: {num(data.frozen_threshold, 8)}. Evaluation changed no models or thresholds. Every output is isolated from Workbench scoring and decision routing.</p>
    </section>

    <section className="v41-panel">
      <div className="v41-section-head"><div><span>02 / MEASURED ON C</span><h2>Semantic Hybrid results</h2></div><b>GROUP BOOTSTRAP · 500 DRAWS</b></div>
      <div className="v41-note"><b>Construct-independence caveat.</b> Generator C is independently implemented, but its gold criteria overlap with deterministic rules: C2/C6/C7 use the same field tolerances ({Object.entries(data.label_rule_overlap.shared_field_thresholds_vnd).map(([field, value]) => `${field} VND ${value.toLocaleString()}`).join('; ')}), and both the C4 gold and time rule use a {data.label_rule_overlap.shared_stale_critical_age_days}-day critical-staleness criterion. The generated C4 stale record is {data.label_rule_overlap.generator_c4_stale_record_age_days} days old. This is target-construct overlap, not direct hidden-label leakage; 100% recall does not independently validate those criteria.</div>
      <div className="v41-metric-grid">
        {Object.entries(metricLabels).map(([key, label]) => <article key={key}>
          <small>{label}</small><strong>{key.includes('score') || key === 'material_average_precision' || key === 'log_loss' ? num(hybrid[key] as number | null) : pct(hybrid[key] as number | null)}</strong>
          <span>95% interval {interval(intervals[key], !(key.includes('score') || key === 'material_average_precision' || key === 'log_loss'))}</span>
        </article>)}
      </div>
      <p>Counts: {hybrid.critical_tp}/{hybrid.critical_support} critical records detected; {hybrid.c4_stale_tp}/{hybrid.c4_stale_critical_support} C4 stale records detected; {hybrid.legitimate_discrepancy_fp_c1_c3_c5}/{hybrid.legitimate_discrepancy_support_c1_c3_c5} C1/C3/C5 legitimate records flagged; {hybrid.legitimate_fp}/{hybrid.legitimate_support} legitimate records flagged overall; {hybrid.flagged_case_count}/{hybrid.case_count} cases sent to review.</p>
      <div className="v41-note"><b>Boundary uncertainty.</b> The 0/2,927 observed C1/C3/C5 document FPs have a one-sided 95% upper bound of {pct(data.boundary_uncertainty.c1_c3_c5_hoeffding_one_sided_95_ucb_equal_group_weighted_fpr, 2)} for an equal-group-weighted FPR bound; at group level, 0/360 groups with any FP gives a one-sided exact upper bound of {pct(data.boundary_uncertainty.c1_c3_c5_one_sided_95_upper_bound_group_any_fp, 2)}. These are different estimands, not proof of zero population risk.</div>
    </section>

    <section className="v41-panel">
      <div className="v41-section-head"><div><span>03 / DIAGNOSTIC ONLY</span><h2>Feature ablation</h2></div><b>NOT CAUSAL</b></div>
      <p>Each ablation is a separately trained and calibrated semantic Logistic Regression arm. Semantic Hybrid combines deterministic rules with Logistic Regression, so comparisons below do not isolate a causal component effect.</p>
      <div className="v41-table-wrap"><table><thead><tr><th>Frozen arm</th><th>Critical recall</th><th>C4 stale recall</th><th>Legitimate FPR</th><th>C1/C3/C5 FPR</th><th>Review workload</th></tr></thead><tbody>
        {ablationNames.map(name => { const m = data.models[name]?.metrics; return <tr key={name}><th>{modelLabels[name]}</th><td>{pct(m?.critical_recall)}</td><td>{pct(m?.c4_stale_as_current_recall)}</td><td>{pct(m?.overall_legitimate_fpr)}</td><td>{pct(m?.legitimate_discrepancy_fpr_c1_c3_c5)}</td><td>{pct(m?.case_review_workload)}</td></tr> })}
      </tbody></table></div>
      <p>Observed scores show the Hybrid at 100% C4 recall and 100% aggregate critical recall, while the full Logistic arm and no-temporal arm both have 0% C4 recall. This weakens a claim that temporal features alone caused Hybrid’s C4 performance. Development-label inconsistency further limits learned-feature attribution.</p>
    </section>

    <section className="v41-panel">
      <div className="v41-section-head"><div><span>04 / FROZEN OUTPUTS ONLY</span><h2>Baseline comparison</h2></div><b>POST-UNBLINDING</b></div>
      <p>Existing frozen baselines with replayable artifacts are shown as descriptive results on C. They were not reselected or retuned. Missing XGBoost branches remain unavailable.</p>
      <div className="v41-table-wrap"><table><thead><tr><th>Model</th><th>Status</th><th>Critical recall</th><th>Legitimate FPR</th><th>Workload</th><th>AP</th></tr></thead><tbody>
        {baselineNames.map(name => { const entry = data.models[name]; const m = entry?.metrics; return <tr key={name}><th>{modelLabels[name]}</th><td>{entry?.availability === 'BLOCKED_DEPENDENCY' ? 'NOT_EVALUATED' : entry?.availability}</td><td>{pct(m?.critical_recall)}</td><td>{pct(m?.overall_legitimate_fpr)}</td><td>{pct(m?.case_review_workload)}</td><td>{num(m?.material_average_precision)}</td></tr> })}
      </tbody></table></div>
    </section>

    <section className="v41-panel">
      <div className="v41-section-head"><div><span>05 / SCENARIO SUPPORT</span><h2>Generator C outcomes</h2></div><b>DENOMINATORS INCLUDED</b></div>
      <div className="v41-table-wrap"><table><thead><tr><th>Scenario</th><th>Critical TP / support</th><th>Critical recall</th><th>Legitimate FP / support</th><th>FPR</th><th>Cases flagged / total</th><th>Workload</th></tr></thead><tbody>
        {data.scenarios.map(row => <tr key={String(row.scenario)}><th>{String(row.scenario).replaceAll('_', ' ')}</th><td>{row.critical_tp}/{row.critical_support}</td><td>{pct(row.critical_recall as number | null)}</td><td>{row.legitimate_fp}/{row.legitimate_support}</td><td>{pct(row.overall_legitimate_fpr as number | null)}</td><td>{row.flagged_case_count}/{row.case_count}</td><td>{pct(row.case_review_workload as number | null)}</td></tr>)}
      </tbody></table></div>
      <p>Scenario names and support counts describe the synthetic challenge design. No canonical values, corruption IDs, or hidden generator gold are exposed as model inputs.</p>
      <h3>Results by source type</h3>
      <div className="v41-table-wrap"><table><thead><tr><th>Source type</th><th>Critical TP / support</th><th>Critical recall</th><th>Legitimate FP / support</th><th>FPR</th><th>Case workload</th></tr></thead><tbody>
        {data.sources.map(row => <tr key={String(row.source_type)}><th>{row.source_type}</th><td>{row.critical_tp}/{row.critical_support}</td><td>{pct(row.critical_recall as number | null)}</td><td>{row.legitimate_fp}/{row.legitimate_support}</td><td>{pct(row.overall_legitimate_fpr as number | null)}</td><td>{row.flagged_case_count}/{row.case_count} · {pct(row.case_review_workload as number | null)}</td></tr>)}
      </tbody></table></div>
    </section>

    <section className="v41-panel">
      <div className="v41-section-head"><div><span>06 / PRESENTATION EVIDENCE</span><h2>Figures and downloadable artifacts</h2></div><b>CHECKSUM-VERIFIED</b></div>
      <div className="v41-figures">{data.figures.map(file => <figure key={file}><img src={'/api/evidence-ai/v4.1/figures/' + file} alt={file.replaceAll('_', ' ').replace('.svg', '')} /><figcaption>{file.replaceAll('_', ' ').replace('.svg', '')}</figcaption></figure>)}</div>
      <div className="v41-artifacts">{data.artifacts.map(file => <a key={file} href={'/api/evidence-ai/v4.1/artifacts/' + file} download>{file.split('/').pop()}</a>)}</div>
    </section>

    <section className="v41-panel">
      <div className="v41-section-head"><div><span>07 / FAILURE REVIEW</span><h2>What the result does and does not show</h2></div></div>
      <div className="v41-examples"><article><b>Stale evidence</b><p>The frozen Hybrid detected the registered C4 stale-as-current documents. D1.1 development labels omitted the critical label for {data.data_quality_audit.critical_labels_missing} stale records across train, validation, calibration and locked test, so attribution to learned temporal features is exploratory.</p></article><article><b>Legitimate differences</b><p>The Hybrid flagged 0/2,927 legitimate C1/C3/C5 documents. These are finite synthetic results. A no-comparability Logistic ablation flagged 494/2,927 in this endpoint and raised case workload to 63.0%.</p></article><article><b>Pair-level false positives</b><p>The Hybrid raised {hybrid.legitimate_fp} false-positive records: {data.false_positive_breakdown.map(row => `${row.false_positives} in ${row.scenario}`).join(', ')}. These were valid peers paired with true conflicts; the pair rule cannot identify the corrupt member alone.</p></article></div>
    </section>

    <section className="v41-panel">
      <div className="v41-section-head"><div><span>08 / REGISTERED ACCEPTANCE</span><h2>Four point-estimate criteria meet their thresholds</h2></div><b>ONE UNASSESSABLE</b></div>
      <div className="v41-table-wrap"><table><thead><tr><th>Criterion</th><th>Observed result</th><th>Status</th></tr></thead><tbody>
        <tr><th>Aggregate critical recall ≥ 90%</th><td>{hybrid.critical_tp}/{hybrid.critical_support} = {pct(hybrid.critical_recall)}</td><td>{data.acceptance.semantic_hybrid_aggregate_critical_recall_min_0_90 === true ? 'MEETS POINT TARGET' : 'DOES NOT MEET'}</td></tr>
        <tr><th>C4 stale-as-current recall ≥ 90%</th><td>{hybrid.c4_stale_tp}/{hybrid.c4_stale_critical_support} = {pct(hybrid.c4_stale_as_current_recall)}</td><td>{data.acceptance.C4_stale_recall_min_0_90 === true ? 'MEETS POINT TARGET' : 'DOES NOT MEET'}</td></tr>
        <tr><th>C1/C3/C5 legitimate FPR ≤ 20%</th><td>{hybrid.legitimate_discrepancy_fp_c1_c3_c5}/{hybrid.legitimate_discrepancy_support_c1_c3_c5} = {pct(hybrid.legitimate_discrepancy_fpr_c1_c3_c5)}</td><td>{data.acceptance.C1_C3_C5_legitimate_fpr_max_0_20 === true ? 'MEETS POINT TARGET' : 'DOES NOT MEET'}</td></tr>
        <tr><th>C7 critical recall ≥ 85%</th><td>{data.scenarios.find(row => row.scenario === 'C7_HELD_OUT_SOURCE_PAIR')?.critical_tp}/{data.scenarios.find(row => row.scenario === 'C7_HELD_OUT_SOURCE_PAIR')?.critical_support} = {pct(data.scenarios.find(row => row.scenario === 'C7_HELD_OUT_SOURCE_PAIR')?.critical_recall as number | null)}</td><td>{data.acceptance.C7_critical_recall_min_0_85 === true ? 'MEETS POINT TARGET' : 'DOES NOT MEET'}</td></tr>
        <tr><th>Recall within 2 percentage points of the best complete frozen baseline</th><td>Available baselines tie at 100%; XGBoost replay was blocked.</td><td>UNASSESSABLE AS REGISTERED</td></tr>
      </tbody></table></div>
    </section>

    <section className="v41-panel v41-limitations"><div className="v41-section-head"><div><span>09 / RESEARCH LIMITATIONS</span><h2>Validation remains blocked</h2></div><b>{data.validation_status}</b></div>
      <ul>{data.limitations.map(item => <li key={item}>{item}</li>)}</ul>
      <p>Workbench CS_V2, mandatory gates, affordability, routing, human review, officer authority, audit decisions, and the UCI credit-risk benchmark remain on their existing paths.</p>
    </section>
  </section>
}
