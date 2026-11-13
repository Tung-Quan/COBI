import { useEffect, useState } from 'react'
import { ArrowUpRight, Beaker, Download, RefreshCw, ShieldCheck } from 'lucide-react'
import { request } from './api'
import './research.css'

const experimentId = 'uci350-v2.0'
const experimentPath = '/research/experiments/' + experimentId
const artifactPath = '/api' + experimentPath + '/artifacts/'

type Dataset = {
  dataset_id: string
  status: string
  source_url?: string
  license?: string
  rows?: number
  label_counts?: Record<string, number>
  normalized_sha256?: string
  feature_allowlist?: string[]
  missingness?: Record<string, number>
  unique_sample_ids?: number
}
type Loss = { step: number; train_loss: number; validation_loss: number }
type Candidate = { candidate: string; family: string; validation_loss: number; history: Loss[]; parameters: object }
type Metric = { estimate: number; ci95: [number, number] }
type ReliabilityBin = { lower: number; upper: number; n: number; mean_predicted: number | null; observed_rate: number | null }
type Result = {
  selected_candidate: string
  split: { seed: number; cohorts: Record<string, { n: number; events: number; prevalence: number }> }
  models: Record<string, { metrics: Record<string, Metric>; reliability: ReliabilityBin[] }>
  paired_log_loss: (Metric & { comparison: string[] })[]
}
type Experiment = { status: string; report?: Result; candidates?: Candidate[]; model_id?: string; artifacts?: string[] }
type Model = { model_id: string; feature_signature: string; status: string; human_risk_review: string; sha256: Record<string, string> }

const labels: Record<string, string> = {
  dummy: 'Train prevalence', logistic: 'Logistic Regression', selected_raw: 'XGBoost raw', selected_calibrated: 'XGBoost sigmoid',
  roc_auc: 'ROC-AUC', average_precision: 'Average precision', brier: 'Brier score', log_loss: 'Log loss',
  calibration_intercept: 'Calibration intercept', calibration_slope: 'Calibration slope', prevalence: 'Default prevalence',
  expected_events: 'Expected defaults', observed_events: 'Observed defaults', observed_minus_expected: 'Observed − expected',
  expected_to_observed: 'Expected / observed',
}
const format = (value: number) => value.toFixed(4)
const metric = (value: Metric | undefined) => value ? <><b>{format(value.estimate)}</b><small>[{format(value.ci95[0])}, {format(value.ci95[1])}]</small></> : '—'

export function ResearchLab() {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [experiment, setExperiment] = useState<Experiment>()
  const [model, setModel] = useState<Model>()
  const [selected, setSelected] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function refresh() {
    setError('')
    try {
      const [catalog, run, registry] = await Promise.all([
        request<{ items: Dataset[] }>('/research/datasets'), request<Experiment>(experimentPath),
        request<{ items: Model[] }>('/research/models'),
      ])
      setDatasets(catalog.items)
      setExperiment(run)
      setModel(registry.items[0])
      setSelected(current => current || run.report?.selected_candidate || '')
    } catch (cause) {
      setExperiment(undefined)
      setModel(undefined)
      setError(cause instanceof Error ? cause.message : 'Research data could not be loaded.')
    }
  }

  useEffect(() => { void refresh() }, [])
  useEffect(() => {
    if (experiment?.status !== 'RUNNING' && experiment?.status !== 'QUEUED') return
    const timer = window.setInterval(() => { void refresh() }, 3000)
    return () => window.clearInterval(timer)
  }, [experiment?.status])

  async function queue() {
    setBusy(true)
    setError('')
    try {
      await request('/research/experiments', { method: 'POST', body: JSON.stringify({ dataset_id: 'UCI_350', protocol: experimentId }) })
      await refresh()
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not queue the experiment.') }
    finally { setBusy(false) }
  }

  const uci = datasets.find(dataset => dataset.dataset_id === 'UCI_350')
  const report = experiment?.report
  const active = experiment?.candidates?.find(candidate => candidate.candidate === selected)
  const missing = Object.values(uci?.missingness ?? {}).reduce((sum, count) => sum + count, 0)

  return <article className="research-lab">
    <header className="research-banner">
      <div className="research-title"><span><Beaker size={16} /> ADDUDU / RESEARCH RECORD 01</span><h1>Research Lab</h1>
        <p>Historical Taiwan credit-card default, next payment month. Vietnamese checkout use requires independent bank validation.</p></div>
      <div className="research-stamp"><ShieldCheck size={19} /><strong>BENCHMARK ONLY</strong><small>{experiment?.status ?? 'Checking release…'}</small></div>
    </header>
    {error && <div role="alert" className="research-alert">{error} <button className="button button-outline" onClick={() => void refresh()}><RefreshCw size={14} /> Retry</button></div>}
    <div className="research-pair">
      <section className="research-sheet"><div className="research-kicker">01 / DATA LINEAGE</div><h2>UCI dataset 350</h2>
        <p>Credit-card payment histories from Taiwan, April to September 2005.</p>
        <dl className="research-facts"><div><dt>Rows</dt><dd>{uci?.rows?.toLocaleString() ?? '—'}</dd></div><div><dt>Defaults</dt><dd>{uci?.label_counts?.['1']?.toLocaleString() ?? '—'}</dd></div>
          <div><dt>Predictors</dt><dd>{uci?.feature_allowlist?.length ?? '—'}</dd></div><div><dt>Missing cells</dt><dd>{uci?.status === 'VERIFIED' ? missing : '—'}</dd></div></dl>
        <p>{uci?.license} · {uci?.status ?? 'Checking provenance…'} · IDs and demographics excluded from predictors.</p>
        {uci?.normalized_sha256 && <details><summary>Normalized SHA-256</summary><code>{uci.normalized_sha256}</code></details>}
        {uci?.source_url && <a className="research-link" href={uci.source_url} target="_blank" rel="noreferrer">Yeh (2009) · UCI source <ArrowUpRight size={14} /></a>}
      </section>
      <section className="research-sheet"><div className="research-kicker">02 / LOCKED PROTOCOL</div><h2>Four separate cohorts</h2>
        <p>Stratified random holdout · seed 42 · application dates unavailable.</p>
        {report ? <><div className="research-split" aria-hidden="true">{Object.entries(report.split.cohorts).map(([name, cohort]) => <span key={name} style={{ flex: cohort.n }} />)}</div>
          <table><thead><tr><th>Cohort</th><th>Rows</th><th>Defaults</th><th>Rate</th></tr></thead><tbody>
            {Object.entries(report.split.cohorts).map(([name, cohort]) => <tr key={name}><th scope="row">{name}</th><td>{cohort.n.toLocaleString()}</td><td>{cohort.events.toLocaleString()}</td><td>{(100 * cohort.prevalence).toFixed(2)}%</td></tr>)}
          </tbody></table></> : <p role="status">{experiment?.status === 'QUEUED' ? 'Queued. A local operator starts the frozen protocol with python -m ml.train_pd.' : experiment?.status ?? 'Checking run status…'}</p>}
        {experiment?.status === 'NOT_EXECUTED' && <button className="button button-dark" disabled={busy || uci?.status !== 'VERIFIED'} onClick={() => void queue()}>Queue frozen UCI protocol</button>}
      </section>
    </div>
    {report && <>
      <section className="research-sheet"><div className="research-kicker">03 / VALIDATION SEARCH</div><h2>Candidate comparison</h2>
        <p>Selected by validation log loss with a predeclared margin for more complex models. Winner <code>{report.selected_candidate}</code>.</p>
        <div className="research-pair research-candidates"><div className="research-scroll"><table><thead><tr><th>Candidate</th><th>Validation log loss</th></tr></thead><tbody>
          {experiment?.candidates?.map(row => <tr key={row.candidate} className={row.candidate === selected ? 'research-current' : ''}>
            <th scope="row"><button className="research-candidate" aria-pressed={row.candidate === selected} onClick={() => setSelected(row.candidate)}>{row.candidate}</button></th><td>{format(row.validation_loss)}</td>
          </tr>)}
        </tbody></table></div><div>{active && <><h3>{active.candidate} training trace</h3>
          <LossChart candidate={active} /><details><summary>Recorded hyperparameters</summary><pre>{JSON.stringify(active.parameters, null, 2)}</pre></details></>}</div></div>
      </section>
      <section className="research-sheet"><div className="research-kicker">04 / LOCKED TEST · 95% PAIRED BOOTSTRAP</div><h2>Final probability metrics</h2>
        <div className="research-scroll"><table><thead><tr><th>Metric</th>{Object.keys(report.models).map(name => <th key={name}>{labels[name]}</th>)}</tr></thead><tbody>
          {Object.keys(report.models.selected_calibrated.metrics).map(name => <tr key={name}><th scope="row">{labels[name]}</th>
            {Object.entries(report.models).map(([id, result]) => <td key={id}>{metric(result.metrics[name])}</td>)}</tr>)}
        </tbody></table></div>
        <h3>Predeclared paired log-loss differences</h3><div className="research-scroll"><table><thead><tr><th>First minus second</th><th>Difference and 95% CI</th></tr></thead><tbody>
          {report.paired_log_loss.map(row => <tr key={row.comparison.join('/')}><th scope="row">{row.comparison.map(name => labels[name]).join(' − ')}</th><td>{metric(row)}</td></tr>)}
        </tbody></table></div>
      </section>
      <div className="research-pair">
        <section className="research-sheet"><div className="research-kicker">05 / CALIBRATION</div><h2>Reliability on the locked test</h2>
          {experiment?.artifacts?.includes('reliability.svg') && <img className="research-plot" src={artifactPath + 'reliability.svg'} alt="Raw and calibrated reliability against the diagonal. Bin counts are listed in the table." />}
          <details><summary>Calibrated reliability bins and counts</summary><table><thead><tr><th>Bin</th><th>Rows</th><th>Mean p</th><th>Observed</th></tr></thead><tbody>
            {report.models.selected_calibrated.reliability.map(bin => <tr key={bin.lower}><th scope="row">{bin.lower.toFixed(1)}–{bin.upper.toFixed(1)}</th><td>{bin.n}</td><td>{bin.mean_predicted?.toFixed(3) ?? '—'}</td><td>{bin.observed_rate?.toFixed(3) ?? '—'}</td></tr>)}
          </tbody></table></details>
        </section>
        <section className="research-sheet"><div className="research-kicker">06 / MODEL REGISTRY</div><h2>Reproduce the benchmark</h2>
          {model && <><p><strong>{model.model_id}</strong><br />{model.status} · {model.human_risk_review}</p><details><summary>Feature signature and component hashes</summary><code>{model.feature_signature}</code><pre>{JSON.stringify(model.sha256, null, 2)}</pre></details></>}
          <div className="research-artifacts">{experiment?.artifacts?.map(name => <a key={name} className="research-link" href={artifactPath + name} download><Download size={14} /> {name}</a>)}</div>
          <p>Credit Review Workbench uses its own synthetic inputs and policy. Bank and fairness validation require separate evidence.</p>
        </section>
      </div>
    </>}
  </article>
}

function LossChart({ candidate }: { candidate: Candidate }) {
  const history = candidate.history
  if (history.length === 0) return <p>Constant baseline fitted from train prevalence. No optimizer steps.</p>
  if (history.length === 1) return <p>Full-batch LBFGS, {history[0].step} iterations. Final training log loss {format(history[0].train_loss)}.</p>
  const values = history.flatMap(row => [row.train_loss, row.validation_loss])
  const min = Math.min(...values), max = Math.max(...values)
  const point = (value: number, index: number) => [40 + index / (history.length - 1) * 340, 140 - (value - min) / Math.max(max - min, 0.001) * 120]
  return <>
    <svg className="research-plot" viewBox="0 0 400 165" role="img" aria-label={'Train and validation log loss for ' + candidate.candidate}>
      <path d="M40 20V140H380" fill="none" stroke="#b9c8c4" />
      <text x="0" y="23">{max.toFixed(2)}</text><text x="0" y="142">{min.toFixed(2)}</text>
      <text x="40" y="157">1</text><text x="380" y="157" textAnchor="end">{history.length}</text>
      <polyline points={history.map((row, i) => point(row.train_loss, i).join(',')).join(' ')} fill="none" stroke="#17695e" strokeWidth="2" />
      <polyline points={history.map((row, i) => point(row.validation_loss, i).join(',')).join(' ')} fill="none" stroke="#a65415" strokeWidth="2" />
    </svg>
    <p className="research-legend"><span>Train</span><span>Validation</span> · {candidate.family === 'mlp' ? 'Epoch' : 'Boosting round'}</p>
  </>
}
