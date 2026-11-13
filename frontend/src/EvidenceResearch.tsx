import { useEffect, useState } from 'react'
import { Download, FlaskConical, LockKeyhole } from 'lucide-react'
import { request } from './api'
import './evidence-research.css'

type Dataset = { name: string; status: string; license: string; task: string; labels: string; source: string | null }
type Reliability = { lower: number; count: number; mean_prediction: number; event_rate: number }
type Model = {
  test: Record<string, number>
  ci95: Record<string, [number, number]>
  reliability: Reliability[]
  threshold_lock: { threshold: number; achieved_critical_recall: number }
}
type Trial = {
  status: string
  selected_deep_sets?: string
  models?: Record<string, Model>
  cohorts?: Record<string, { cases: number; groups: number }>
  training_summary?: { candidate: string; validation_log_loss: number; runs: { seed: number; best_step: number }[] }[]
  example?: { case: string; partition: string; explanation: string; documents: {
    source: string; material_probability: number; field_probabilities: Record<string, number>
    other_documents_mean_probability_change_without_this_source: number
  }[] }
  artifacts?: string[]
}
type Receipt = { status: string; scope?: string; artifacts?: string[]; replay_uncertainty?: { ci95: [number, number] }; test?: {
  documents: number; exact_field_micro_f1: number; exact_field_precision: number; exact_field_recall: number
  counts: { words: number; visible_words: number }; field_metrics: Record<string, { f1: number; gold: number }>
} }
type V4Model = {
  cases: number; documents: number; critical_errors: number; critical_false_negatives: number
  critical_recall: number; critical_fnr: number; average_precision: number; brier: number; log_loss: number
  review_workload: number; critical_fn_per_case: number; ci95: Record<string, [number, number]>
}
type V4CostConfig = {
  application_volumes: number[]
  review_cost_per_flagged_case: Record<string, number>
  missed_critical_document_cost: Record<string, number>
  inference_cost_per_application: { cs_v2: number; learned_model: number }
  fixed_operating_cost: { cs_v2: number; learned_model: number }
}
type V4Summary = {
  status: string; validation_status: string
  e1?: { dataset: { cases: number; customer_groups: number; documents: number }; models: Record<string, V4Model> }
  e2?: {
    models: Record<string, V4Model>
    scenario_results: Record<string, Record<string, V4Model>>
    generalization_gaps: Record<string, { AP_A_minus_AP_B: number; CriticalRecall_A_minus_B: number; LogLoss_B_minus_A: number;
      independent_customer_bootstrap_ci95: Record<string, [number, number] | null> }>
    legitimate_discrepancies_B5: Record<string, { documents: number; flagged_legitimate_documents: number; false_positive_rate_on_legitimate_documents: number }>
    base_rates: Record<string, { cases: number; documents: number; material_prevalence: number; critical_prevalence: number }>
  }
  e3?: { assumptions: V4CostConfig; measured_v3_synthetic_rates: Record<string, { case_workload: number; critical_fn_per_case: number }> }
}
const baselineLabels: Record<string, string> = {
  M0_CS_V2: 'CS V2', M1_LOGISTIC: 'Logistic regression', M2_XGBOOST: 'XGBoost', M3_DEEP_SETS: 'Deep Sets',
}
const columns = [['critical_recall', 'Critical recall'], ['critical_fnr', 'FNR'], ['average_precision', 'AP'],
  ['brier', 'Brier'], ['log_loss', 'Log loss'], ['review_workload', 'Case workload']] as const
const pct = (value: number | null | undefined) => value == null ? 'N/A' : (value * 100).toFixed(1) + '%'
const money = (value: number) => new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(value) + ' ₫'
const v4Models = ['M0_CS_V2', 'M1_LOGISTIC', 'M2_XGBOOST', 'M3_DEEP_SETS']

export function EvidenceResearch() {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [trial, setTrial] = useState<Trial>()
  const [receipt, setReceipt] = useState<Receipt>()
  const [v4, setV4] = useState<V4Summary>()
  const [costVolume, setCostVolume] = useState(10000)
  const [reviewLevel, setReviewLevel] = useState('medium')
  const [missedLevel, setMissedLevel] = useState('medium')
  const [error, setError] = useState('')
  const [modelId, setModelId] = useState('M3_DEEP_SETS')

  async function refresh() {
    setError('')
    try {
      const [sources, synthetic, extraction, v4Summary] = await Promise.all([
        request<{ datasets: Dataset[] }>('/evidence-ai/status'),
        request<Trial>('/evidence-ai/experiments/synthetic'),
        request<Receipt>('/evidence-ai/experiments/cord-extraction'),
        request<V4Summary>('/evidence-ai/v4/summary'),
      ])
      setDatasets(sources.datasets)
      setTrial(synthetic)
      setReceipt(extraction)
      setV4(v4Summary)
    } catch (cause) {
      setTrial(undefined)
      setReceipt(undefined)
      setV4(undefined)
      setError(cause instanceof Error ? cause.message : 'Evidence releases could not be read.')
    }
  }
  useEffect(() => { void refresh() }, [])
  const selected = trial?.models?.[modelId]
  const assumptions = v4?.e3?.assumptions
  const costRates = v4?.e3?.measured_v3_synthetic_rates
  const reviewCost = assumptions?.review_cost_per_flagged_case[reviewLevel] ?? 0
  const missedCost = assumptions?.missed_critical_document_cost[missedLevel] ?? 0
  const costRows = costRates ? v4Models.map(id => {
    const rate = costRates[id]
    const inference = id === 'M0_CS_V2' ? assumptions?.inference_cost_per_application.cs_v2 ?? 0
      : assumptions?.inference_cost_per_application.learned_model ?? 0
    const fixed = id === 'M0_CS_V2' ? assumptions?.fixed_operating_cost.cs_v2 ?? 0
      : assumptions?.fixed_operating_cost.learned_model ?? 0
    const flagged = costVolume * rate.case_workload
    const missed = costVolume * rate.critical_fn_per_case
    const total = flagged * reviewCost + missed * missedCost + costVolume * inference + fixed
    return { id, flagged, missed, total }
  }) : []
  const csCost = costRows.find(row => row.id === 'M0_CS_V2')?.total ?? 0
  return <article className="evidence-research">
    <header className="evidence-hero"><span><FlaskConical size={17} /> Adudu / V3 BASELINE + V4 STUDY</span>
      <h1>Evidence AI Research</h1>
      <p>Controlled evidence-error detection and public receipt field extraction. Checkout validation requires independently adjudicated bank-document labels.</p>
      <strong><LockKeyhole size={15} /> EVIDENCE_AI_VALIDATION_BLOCKED</strong>
    </header>
    {error && <div role="alert" className="evidence-sheet">{error} <button className="button button-outline" onClick={() => void refresh()}>Retry</button></div>}
    <section className="evidence-sheet">
      <span className="evidence-kicker">01 / DATA AND LABELS</span><h2>What each dataset measures</h2>
      <dl className="evidence-catalog">{datasets.map(row => <div key={row.name}><dt>{row.name}</dt><dd><b>{row.status}</b><p>{row.task}. {row.labels}</p>
        <small>{row.license} {row.source && <a href={row.source} target="_blank" rel="noreferrer">Source</a>}</small></dd></div>)}</dl>
    </section>
    <section className="evidence-sheet">
      <span className="evidence-kicker">02 / CONTROLLED SYNTHETIC DEFECTS</span><h2>Model comparison on the locked test</h2>
      <p>Each threshold targets 90% critical recall on calibration. Workload is the fraction of cases flagged on test. Brackets show 95% customer bootstrap intervals.</p>
      {trial?.models ? <>
        <p className="evidence-kicker">{trial.status} · {Object.entries(trial.cohorts ?? {}).map(([name, count]) => name + ' ' + count.cases + ' cases').join(' / ')}</p>
        <div className="evidence-scroll"><table><thead><tr><th>Model</th>{columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead>
          <tbody>{Object.entries(trial.models).map(([id, model]) => <tr key={id} className={modelId === id ? 'evidence-selected' : ''}>
            <th scope="row"><button type="button" onClick={() => setModelId(id)} aria-pressed={id === modelId}>{baselineLabels[id] ?? 'Drop ' + id.replace('ABLATE_', '')}</button></th>
            {columns.map(([key]) => <td key={key}><b>{model.test[key].toFixed(3)}</b><small>[{model.ci95[key].map(v => v.toFixed(3)).join(', ')}]</small></td>)}
          </tr>)}</tbody></table></div>
        <details><summary>Candidate training summary</summary><ul>{trial.training_summary?.map(candidate =>
          <li key={candidate.candidate}><b>{candidate.candidate}</b> · validation log loss {candidate.validation_log_loss.toFixed(5)} · {candidate.runs.map(run => 'seed ' + run.seed + ' / best ' + run.best_step).join(', ')}</li>)}</ul></details>
        <ArtifactLinks run="synthetic" names={trial.artifacts ?? []} />
      </> : <p role="status">{trial?.status ?? 'Reading the local release…'}</p>}
    </section>
    {selected && <div className="evidence-pair">
      <section className="evidence-sheet"><span className="evidence-kicker">03 / CALIBRATION</span><h2>{baselineLabels[modelId] ?? modelId}</h2>
        <p>Frozen threshold {selected.threshold_lock.threshold.toFixed(3)} · Calibration critical recall {pct(selected.threshold_lock.achieved_critical_recall)}.</p>
        <ReliabilityPlot bins={selected.reliability} />
        <details><summary>Reliability bin counts</summary><table><thead><tr><th>Bin start</th><th>Documents</th><th>Mean prediction</th><th>Observed</th></tr></thead>
          <tbody>{selected.reliability.map(bin => <tr key={bin.lower}><td>{bin.lower.toFixed(1)}</td><td>{bin.count}</td><td>{pct(bin.mean_prediction)}</td><td>{pct(bin.event_rate)}</td></tr>)}</tbody></table></details>
      </section>
      <section className="evidence-sheet"><span className="evidence-kicker">04 / RESEARCH EXAMPLE</span><h2>Suspected field errors</h2>
        <p>Deep Sets · {trial?.example?.partition}. Probabilities describe a generated case under the technical experiment.</p>
        {trial?.example?.documents.map((doc, index) => <details key={index} open={index === 0}>
          <summary>{doc.source} {index + 1} · material error {pct(doc.material_probability)}</summary>
          <p>{Object.entries(doc.field_probabilities).map(([field, value]) => field + ' ' + pct(value)).join(' · ')}</p>
          <small>Mean change in other documents when masked {pct(doc.other_documents_mean_probability_change_without_this_source)} points.</small>
        </details>)}
        <p>{trial?.example?.explanation}</p>
      </section>
    </div>}
    <section className="evidence-sheet"><span className="evidence-kicker">05 / PUBLIC DOCUMENT EXTRACTION</span><h2>LayoutLMv3 on CORD v2</h2>
      <p>Receipt field tagging with dataset-supplied words and boxes. This separate experiment measures extraction and has no bank authenticity or evidence-error labels.</p>
      {receipt?.test ? <><p><b>Exact field F1 {receipt.test.exact_field_micro_f1.toFixed(3)}</b> · Precision {pct(receipt.test.exact_field_precision)} · Recall {pct(receipt.test.exact_field_recall)} · {receipt.test.documents} test receipts</p>
        {receipt.replay_uncertainty && <p>95% receipt bootstrap CI [{receipt.replay_uncertainty.ci95.map(value => value.toFixed(3)).join(', ')}], conditional on one seed.</p>}
        <p>{receipt.scope} · {receipt.test.counts.visible_words}/{receipt.test.counts.words} visible words.</p>
        <details><summary>Per-field results</summary><table><thead><tr><th>Field</th><th>Support</th><th>F1</th></tr></thead><tbody>{Object.entries(receipt.test.field_metrics).map(([label, row]) =>
          <tr key={label}><td>{label}</td><td>{row.gold}</td><td>{row.f1.toFixed(3)}</td></tr>)}</tbody></table></details>
        <ArtifactLinks run="cord-extraction" names={receipt.artifacts ?? []} /></> : <p role="status">{receipt?.status ?? 'Reading the local release…'}</p>}
    </section>
    <section className="evidence-sheet evidence-v4">
      <span className="evidence-kicker">06 / V4 INDEPENDENT SYNTHETIC CHALLENGE</span>
      <h2>Frozen V3 models under Generator B</h2>
      {v4?.e2?.models && v4.e1?.models ? <>
        <p>V3 test results are retrospective; Generator B uses programmatic synthetic gold. Model weights, preprocessing, calibration and thresholds stayed frozen. Bank validation remains blocked.</p>
        <p><b>Generator B:</b> {v4.e2.base_rates.Generator_B.cases.toLocaleString()} cases, {v4.e2.base_rates.Generator_B.documents.toLocaleString()} documents across 6 registered scenarios. Material-defect prevalence {pct(v4.e2.base_rates.Generator_B.material_prevalence)}; critical-defect prevalence {pct(v4.e2.base_rates.Generator_B.critical_prevalence)}.</p>
        <div className="evidence-scroll"><table><thead><tr><th>Model</th><th>V3 recall</th><th>V3 workload</th><th>B recall</th><th>B FN / critical</th><th>B AP</th><th>B workload</th></tr></thead>
          <tbody>{v4Models.map(id => {
            const a = v4.e1!.models[id]; const b = v4.e2!.models[id]
            return <tr key={id}><th scope="row">{baselineLabels[id]}</th><td>{pct(a.critical_recall)}</td><td>{pct(a.review_workload)}</td>
              <td><b>{pct(b.critical_recall)}</b><small>[{b.ci95.critical_recall.map(x => x.toFixed(3)).join(', ')}]</small></td>
              <td>{b.critical_false_negatives} / {b.critical_errors}</td><td>{b.average_precision.toFixed(3)}</td><td>{pct(b.review_workload)}</td></tr>
          })}</tbody></table></div>
        <div className="evidence-scroll"><table><thead><tr><th>Scenario</th><th>Model</th><th>Critical recall</th><th>FN count</th><th>AP</th><th>Workload</th></tr></thead><tbody>
          {Object.entries(v4.e2.scenario_results).flatMap(([scenario, models]) => v4Models.map(id => {
            const row = models[id]
            return <tr key={scenario + id}><td>{scenario}</td><td>{baselineLabels[id]}</td><td>{pct(row.critical_recall)}</td><td>{row.critical_false_negatives}</td><td>{row.average_precision.toFixed(3)}</td><td>{pct(row.review_workload)}</td></tr>
          }))}
        </tbody></table></div>
        <details><summary>False positives on legitimate discrepancies in B5</summary><table><thead><tr><th>Model</th><th>Legitimate documents flagged</th><th>False-positive rate</th></tr></thead><tbody>
          {v4Models.map(id => <tr key={id}><td>{baselineLabels[id]}</td><td>{v4.e2!.legitimate_discrepancies_B5[id].flagged_legitimate_documents.toLocaleString()}</td><td>{pct(v4.e2!.legitimate_discrepancies_B5[id].false_positive_rate_on_legitimate_documents)}</td></tr>)}
        </tbody></table></details>
        <div className="evidence-chart-grid">
          {['generator_shift_performance.svg', 'scenario_failure_matrix.svg', 'generalization_gap.svg'].map(file =>
            <figure key={file}><img src={'/api/evidence-ai/v4/figures/' + file} alt={file.replaceAll('_', ' ').replace('.svg', '')} /><figcaption>{file.replaceAll('_', ' ').replace('.svg', '')}</figcaption></figure>)}
        </div>
      </> : <p role="status">{v4?.status ?? 'V4 results are not available.'}</p>}
      <small>Critical recall and workload use frozen V3 thresholds. AP depends on label prevalence. Generator B is technical synthetic evidence, not evidence of real-bank performance.</small>
    </section>
    <section className="evidence-sheet evidence-v4">
      <span className="evidence-kicker">07 / BUSINESS COST SENSITIVITY</span><h2>Explore explicit cost assumptions</h2>
      {assumptions && costRates ? <>
        <p>Illustrative scenario simulation only. Unit costs are assumptions, not bank quotations; results are not realized savings.</p>
        <div className="evidence-cost-controls">
          <label>Applications <select value={costVolume} onChange={event => setCostVolume(Number(event.target.value))}>
            {assumptions.application_volumes.map(value => <option key={value} value={value}>{value.toLocaleString()}</option>)}
          </select></label>
          <label>Review cost per flagged case <select value={reviewLevel} onChange={event => setReviewLevel(event.target.value)}>
            {Object.entries(assumptions.review_cost_per_flagged_case).map(([key, value]) => <option key={key} value={key}>{key} — {money(value)}</option>)}
          </select></label>
          <label>Missed critical document cost <select value={missedLevel} onChange={event => setMissedLevel(event.target.value)}>
            {Object.entries(assumptions.missed_critical_document_cost).map(([key, value]) => <option key={key} value={key}>{key} — {money(value)}</option>)}
          </select></label>
        </div>
        <div className="evidence-scroll"><table><thead><tr><th>Model</th><th>Expected flagged cases</th><th>Expected missed critical documents</th><th>Simulated total cost</th><th>Difference vs CS V2</th></tr></thead><tbody>
          {costRows.map(row => <tr key={row.id}><th scope="row">{baselineLabels[row.id]}</th><td>{row.flagged.toFixed(0)}</td><td>{row.missed.toFixed(1)}</td><td>{money(row.total)}</td><td>{money(csCost - row.total)}</td></tr>)}
        </tbody></table></div>
        <small>Formula: flagged cases × review cost + missed critical documents × missed-error cost + inference cost + fixed operating cost. Sampling uncertainty and assumption sensitivity are separate in the downloadable report.</small>
        <div className="evidence-chart-grid">
          {['business_cost_sensitivity.svg', 'business_break_even.svg'].map(file =>
            <figure key={file}><img src={'/api/evidence-ai/v4/figures/' + file} alt={file.replaceAll('_', ' ').replace('.svg', '')} /><figcaption>{file.replaceAll('_', ' ').replace('.svg', '')}</figcaption></figure>)}
        </div>
      </> : <p role="status">V4 cost simulation is not available.</p>}
    </section>

  </article>
}

function ArtifactLinks({ run, names }: { run: string; names: string[] }) {
  return <div className="evidence-artifacts">{names.map(name =>
    <a key={name} href={'/api/evidence-ai/experiments/' + run + '/artifacts/' + name} download><Download size={13} />{name}</a>)}</div>
}

function ReliabilityPlot({ bins }: { bins: Reliability[] }) {
  const coordinates = bins.map(bin => [36 + 310 * bin.mean_prediction, 160 - 135 * bin.event_rate])
  return <svg viewBox="0 0 365 187" role="img" aria-label="Observed defect rate versus mean predicted probability">
    <path d="M36 25V160H346" fill="none" stroke="#a0aca6" />
    <path d="M36 160L346 25" stroke="#7e8a85" strokeDasharray="4 5" />
    <polyline fill="none" stroke="#0f7864" strokeWidth="2" points={coordinates.map(point => point.join(',')).join(' ')} />
    {coordinates.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={4} fill="#0f7864"><title>{bins[i].count} documents</title></circle>)}
    <text x="1" y="28">1.0</text><text x="4" y="161">0.0</text><text x="98" y="182">Mean predicted probability</text>
  </svg>
}

export function EvidenceShadow({ applicationId, onResearch }: { applicationId: string; onResearch: () => void }) {
  const [record, setRecord] = useState<{ application_id: string; status: string; reason: string }>()
  useEffect(() => {
    let active = true
    void request<{ application_id: string; status: string; reason: string }>('/evidence-ai/shadow/' + applicationId)
      .then(result => { if (active) setRecord(result) }).catch(() => { if (active) setRecord(undefined) })
    return () => { active = false }
  }, [applicationId])
  return <aside className="evidence-shadow">
    <LockKeyhole size={16} /><div><strong>Evidence AI · shadow only</strong>
      <p>{record?.application_id === applicationId ? record.reason : 'Workbench evidence predictions require validated labels and policy authorization.'}</p></div>
    <button className="button button-outline" onClick={onResearch}>Open evidence research</button>
  </aside>
}
