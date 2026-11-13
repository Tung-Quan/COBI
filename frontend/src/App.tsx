import { useEffect, useMemo, useState, type CSSProperties, type FormEvent, type ReactNode } from 'react'
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BadgeCheck, Banknote,
  BarChart3, BookOpen, Check, CheckCircle2, ChevronDown, ChevronRight,
  CircleAlert, Download, FileCheck2, FileClock, FileSearch, Gauge,
  HelpCircle, History, Info, Landmark, LayoutDashboard, LockKeyhole,
  LogOut, Menu, ReceiptText, RefreshCw, Search, ShieldAlert,
  ShieldCheck, SlidersHorizontal, Sparkles, UserRound, Users, WalletCards, X,
} from 'lucide-react'
import { createApplication, downloadExport, getApplications, getMetrics, request, revokeConsent, runSimulation, sendReviewAction } from './api'
import type { Assessment, AuditEvent, CaseRecord, PortfolioMetrics, RouteName } from './types'
import { ResearchLab } from './ResearchLab'
import { EvidenceResearch, EvidenceShadow } from './EvidenceResearch'
import { EvidenceResearchV41 } from './EvidenceResearchV41'
import { authClient, authEnabled } from './auth'

type PageName = 'Dashboard' | 'Applications' | 'AI Assessment' | 'Decision Routing' | 'Officer Review' | 'What-if Simulator' | 'Monitoring & export' | 'Research Lab' | 'Evidence AI Research'

const routeLabels: Record<RouteName, string> = {
  HOLD_FOR_HUMAN_HANDLING: 'Hold for handling',
  FAST_TRACK_CANDIDATE: 'Fast-track candidate',
  STANDARD_REVIEW: 'Standard review',
  ENHANCED_REVIEW: 'Enhanced review',
}

const routeShort: Record<RouteName, string> = {
  HOLD_FOR_HUMAN_HANDLING: 'Hold',
  FAST_TRACK_CANDIDATE: 'Fast-track',
  STANDARD_REVIEW: 'Standard',
  ENHANCED_REVIEW: 'Enhanced',
}

const money = (value?: number | null) => value == null
  ? '—'
  : new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(value) + ' ₫'

const moneyCompact = (value?: number | null) => {
  if (value == null) return '—'
  const absolute = Math.abs(value)
  const unit = absolute >= 1_000_000_000 ? 'tỷ' : absolute >= 1_000_000 ? 'triệu' : absolute >= 1_000 ? 'nghìn' : null
  const divisor = absolute >= 1_000_000_000 ? 1_000_000_000 : absolute >= 1_000_000 ? 1_000_000 : absolute >= 1_000 ? 1_000 : 1
  const amount = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 }).format(value / divisor)
  return unit ? `${amount} ${unit} ₫` : money(value)
}

const percent = (value?: number | null, places = 1) => value == null ? '—' : `${(value * 100).toFixed(places)}%`
const dateLabel = (value: string) => new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value))
const timeLabel = (value: string) => new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' }).format(new Date(value))

function routeClass(route: RouteName) {
  if (route === 'FAST_TRACK_CANDIDATE') return 'route-fast'
  if (route === 'ENHANCED_REVIEW') return 'route-enhanced'
  if (route === 'HOLD_FOR_HUMAN_HANDLING') return 'route-hold'
  return 'route-standard'
}

function scoreClass(value?: number | null) {
  if (value == null) return 'muted'
  return value >= 0.75 ? 'positive' : value >= 0.5 ? 'caution' : 'negative'
}

function App() {
  if (authEnabled) return <AuthGate />
  return <WorkspaceApp userName="Demo reviewer" />
}

function AuthGate() {
  const { data: session, isPending } = authClient.useSession()
  if (isPending) return <div className="loading-screen"><div className="loader-mark"><Activity size={20} /></div><span>Opening your secure workspace…</span></div>
  if (!session?.user) return <AuthPage />
  return <WorkspaceApp userName={session.user.name || session.user.email || 'COBI reviewer'} onSignOut={() => void authClient.signOut()} />
}

function AuthPage() {
  const [mode, setMode] = useState<'sign-in' | 'sign-up'>('sign-in')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const result = mode === 'sign-up'
        ? await authClient.signUp.email({ name: name.trim(), email: email.trim(), password })
        : await authClient.signIn.email({ email: email.trim(), password })
      if (result.error) setError(result.error.message || 'We could not sign you in. Check your details and try again.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'We could not reach the sign-in service. Try again.')
    } finally { setBusy(false) }
  }

  return <main className="auth-screen">
    <section className="auth-story">
      <div className="auth-brand"><span className="brand-mark"><Landmark size={20} /></span><div><strong>COBI</strong><small>Credit operations workspace</small></div></div>
      <div className="auth-story-copy"><span className="auth-kicker"><span /> PRIVATE DEMO WORKSPACE</span><h1>Review every case<br /><em>with the evidence in view.</em></h1><p>Organize synthetic application data, trace each review step and keep every final decision with a human reviewer.</p>
        <div className="auth-proof"><div><ShieldCheck size={17} /><span>Account-scoped case data</span></div><div><History size={17} /><span>Traceable review history</span></div><div><Info size={17} /><span>Synthetic demonstration only</span></div></div>
      </div>
      <div className="auth-story-footer">COBI · DEMO ENVIRONMENT <span>NO LIVE CREDIT DECISIONS</span></div>
    </section>
    <section className="auth-panel-wrap"><form className="auth-panel" onSubmit={submit}>
      <span className="eyebrow">YOUR WORKSPACE</span><h2>{mode === 'sign-in' ? 'Welcome back' : 'Create your account'}</h2><p>{mode === 'sign-in' ? 'Sign in to continue to your review desk.' : 'Set up a private demo workspace in a few steps.'}</p>
      {mode === 'sign-up' && <label className="auth-field"><span>Full name</span><input autoComplete="name" value={name} onChange={event => setName(event.target.value)} placeholder="Your name" required maxLength={120} /></label>}
      <label className="auth-field"><span>Email address</span><input type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="you@example.com" required maxLength={254} /></label>
      <label className="auth-field"><span>Password</span><input type="password" autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'} value={password} onChange={event => setPassword(event.target.value)} placeholder="At least 8 characters" required minLength={8} maxLength={128} /></label>
      {error && <div className="auth-error" role="alert"><CircleAlert size={15} />{error}</div>}
      <button className="button button-dark auth-submit" type="submit" disabled={busy}>{busy ? 'Please wait…' : mode === 'sign-in' ? 'Sign in to COBI' : 'Create account'}<ArrowRight size={16} /></button>
      <div className="auth-switch">{mode === 'sign-in' ? 'New to COBI?' : 'Already have an account?'} <button type="button" onClick={() => { setMode(mode === 'sign-in' ? 'sign-up' : 'sign-in'); setError('') }}>{mode === 'sign-in' ? 'Create an account' : 'Sign in'}</button></div>
      <div className="auth-privacy"><LockKeyhole size={13} /><span>Your cases are private to your account. The workspace uses synthetic demo data only.</span></div>
    </form></section>
  </main>
}

function WorkspaceApp({ userName, onSignOut }: { userName: string; onSignOut?: () => void }) {
  const [page, setPage] = useState<PageName>('Dashboard')
  const [cases, setCases] = useState<CaseRecord[]>([])
  const [metrics, setMetrics] = useState<PortfolioMetrics | null>(null)
  const [activeId, setActiveId] = useState('DEMO-001')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [mobileNav, setMobileNav] = useState(false)

  const refresh = async () => {
    try {
      const [nextCases, nextMetrics] = await Promise.all([getApplications(), getMetrics()])
      setCases(nextCases)
      setMetrics(nextMetrics)
      setActiveId(current => nextCases.some(item => item.application_id === current) ? current : nextCases[0]?.application_id ?? '')
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not connect to the workspace service. Check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void refresh() }, [])

  const active = useMemo(() => cases.find(item => item.application_id === activeId) ?? cases[0], [cases, activeId])
  const selectPage = (next: PageName) => {
    setPage(next)
    setMobileNav(false)
    setNotice('')
  }

  const selectCase = (id: string) => {
    setActiveId(id)
    setNotice('')
  }

  if (loading) return <div className="loading-screen"><div className="loader-mark"><Activity size={20} /></div><span>Preparing the synthetic review queue…</span></div>
  if (error && cases.length === 0) return <div className="connection-screen">
    <div className="connection-card">
      <div className="brand-mark"><Landmark size={20} /></div>
      <span className="eyebrow">WORKSPACE CONNECTION</span>
      <h1>We couldn’t reach your review workspace.</h1>
      <p>Check your connection and retry. If the problem continues, contact your workspace administrator.</p>
      <div className="connection-error"><CircleAlert size={16} />{error}</div>
      <button className="button button-dark" onClick={() => { setLoading(true); void refresh() }}><RefreshCw size={15} /> Try again</button>
    </div>
  </div>

  return <div className="app-shell">
    <Sidebar page={page} onNavigate={selectPage} mobileOpen={mobileNav} userName={userName} />
    {mobileNav && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
    <main className="main-shell">
      <header className="topbar">
        <button className="icon-button mobile-menu" aria-label="Open menu" onClick={() => setMobileNav(true)}><Menu size={19} /></button>
        <div className="breadcrumbs"><span>Workspace</span><ChevronRight size={14} /><strong>{page}</strong></div>
        <div className="topbar-right">
          <span className="sandbox-pill"><span className="status-dot" /> {page === 'Research Lab' || page === 'Evidence AI Research' ? 'Research benchmark' : 'Synthetic demo workspace'}</span>
          <div className="user-avatar" title={userName}>{userName.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase()}</div>
          {onSignOut && <button className="sign-out-button" onClick={onSignOut}><LogOut size={14} /><span>Sign out</span></button>}
        </div>
      </header>
      {error && <div className="inline-alert"><CircleAlert size={16} />{error}<button onClick={() => void refresh()}>Retry</button></div>}
      {notice && <div className="success-toast"><CheckCircle2 size={16} />{notice}<button aria-label="Dismiss" onClick={() => setNotice('')}><X size={14} /></button></div>}
      <div className="page-content">
        {page === 'Dashboard' && active && <DashboardPage cases={cases} activeId={activeId} metrics={metrics} onOpen={id => { selectCase(id); selectPage('Applications') }} onNavigate={selectPage} />}
        {page === 'Applications' && active && <ApplicationsPage cases={cases} active={active} onSelect={selectCase} onNavigate={selectPage} onCreated={async id => { await refresh(); setActiveId(id); setNotice('Synthetic application added to the local case queue.') }} />}
        {page === 'AI Assessment' && active && <AssessmentPage active={active} onNavigate={selectPage} />}
        {page === 'Decision Routing' && active && <RoutingPage active={active} onNavigate={selectPage} />}
        {page === 'Officer Review' && active && <ReviewPage active={active} onNavigate={selectPage} onUpdated={async message => { await refresh(); setNotice(message) }} />}
        {page === 'What-if Simulator' && active && <SimulatorPage active={active} onNavigate={selectPage} />}
        {page === 'Monitoring & export' && <EvaluationPage />}
        {page === 'Research Lab' && <ResearchLab />}
        {page === 'Evidence AI Research' && <><EvidenceResearch /><EvidenceResearchV41 /></>}
      </div>
    </main>
  </div>
}

function Sidebar({ page, onNavigate, mobileOpen, userName }: { page: PageName; onNavigate: (page: PageName) => void; mobileOpen: boolean; userName: string }) {
  const items: { name: PageName; icon: typeof LayoutDashboard; group: string }[] = [
    { name: 'Dashboard', icon: LayoutDashboard, group: 'WORKSPACE' },
    { name: 'Applications', icon: WalletCards, group: 'WORKSPACE' },
    { name: 'AI Assessment', icon: Gauge, group: 'DECISION SUPPORT' },
    { name: 'Decision Routing', icon: Activity, group: 'DECISION SUPPORT' },
    { name: 'Officer Review', icon: FileCheck2, group: 'DECISION SUPPORT' },
    { name: 'What-if Simulator', icon: SlidersHorizontal, group: 'TOOLS' },
    { name: 'Monitoring & export', icon: BarChart3, group: 'TOOLS' },
    { name: 'Research Lab', icon: BookOpen, group: 'RESEARCH' },
    { name: 'Evidence AI Research', icon: FileSearch, group: 'RESEARCH' },
  ]
  let lastGroup = ''
  return <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
    <div className="sidebar-brand">
      <div className="brand-mark"><Landmark size={19} strokeWidth={1.8} /></div>
      <div><strong>COBI</strong><small>Credit operations</small></div>
    </div>
    <div className="workspace-picker" aria-label="Current workspace"><div className="workspace-glyph">C</div><div><strong>Operations workspace</strong><small>Synthetic demo data</small></div></div>
    <nav aria-label="Main navigation">
      {items.map(item => {
        const Icon = item.icon
        const heading = item.group !== lastGroup ? <div className="nav-group-label" key={`${item.group}-heading`}>{item.group}</div> : null
        lastGroup = item.group
        return <div key={item.name}>{heading}<button className={`nav-link ${page === item.name ? 'nav-link-active' : ''}`} aria-current={page === item.name ? 'page' : undefined} onClick={() => onNavigate(item.name)}>
          <Icon size={17} strokeWidth={1.8} /><span>{item.name}</span>
        </button></div>
      })}
    </nav>
    <div className="sidebar-spacer" />
    <div className="sandbox-card">
      <div className="sandbox-icon"><ShieldCheck size={15} /></div>
      <div><strong>Safe demo mode</strong><p>No live credit decisions</p></div>
      <span className="sandbox-check"><Check size={12} /></span>
    </div>
    <div className="sidebar-footer"><div className="officer-avatar">{userName.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase()}</div><div className="officer-meta"><strong>{userName}</strong><small>Human review · demo</small></div></div>
  </aside>
}

function PageTitle({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="page-heading">
    <div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description && <p>{description}</p>}</div>
    {action && <div className="heading-action">{action}</div>}
  </div>
}

function MetricCard({ label, value, subline, trend, icon: Icon, accent = 'teal' }: {
  label: string; value: string; subline: string; trend?: 'up' | 'down' | 'neutral'; icon: typeof Users; accent?: string
}) {
  return <div className={`metric-card metric-${accent}`}>
    <div className="metric-head"><span>{label}</span><span className="metric-icon"><Icon size={16} /></span></div>
    <div className="metric-value">{value}</div>
    <div className="metric-foot">{trend && <span className={`trend trend-${trend}`}>{trend === 'up' ? <ArrowUpRight size={13} /> : trend === 'down' ? <ArrowDownRight size={13} /> : <Activity size={12} />}</span>}{subline}</div>
  </div>
}

function DashboardPage({ cases, activeId, metrics, onOpen, onNavigate }: {
  cases: CaseRecord[]; activeId: string; metrics: PortfolioMetrics | null; onOpen: (id: string) => void; onNavigate: (page: PageName) => void
}) {
  const displayed = cases.slice(0, 5)
  const todayLabel = new Intl.DateTimeFormat('en-US', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }).format(new Date())
  return <>
    <PageTitle eyebrow={`${todayLabel} · ICT`} title="Review overview" description="Prioritize the synthetic application queue and keep each review traceable." action={<button className="button button-outline" onClick={() => onNavigate('Applications')}><FileSearch size={15} /> Browse applications</button>} />
    <div className="hero-panel">
      <div className="hero-copy"><div className="hero-overline"><span className="hero-pulse" /> TODAY'S REVIEW DESK <span>·</span> ALL TIMES ICT</div>
        <h2>Every case has<br /><em>a clear next step.</em></h2>
        <p>Evidence, affordability and review routing in one transparent workspace.</p>
        <button className="hero-link" onClick={() => onNavigate('Applications')}>Open the queue <ArrowRight size={15} /></button>
      </div>
      <div className="hero-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit-core"><div className="orbit-core-inner"><Landmark size={27} strokeWidth={1.25} /></div></div><span className="orbit-node node-a"><Check size={12} /></span><span className="orbit-node node-b"><ShieldCheck size={12} /></span><span className="orbit-node node-c"><Activity size={12} /></span><div className="orbit-caption"><small>ASSESSMENT</small><b>Human-led</b></div></div>
      <div className="hero-aside"><span>PORTFOLIO SNAPSHOT</span><strong>{metrics?.application_count ?? cases.length}<small> cases</small></strong><div className="hero-aside-line"><span>Ready for review</span><b>{cases.filter(item => item.assessment.scoring_performed).length}</b></div><div className="hero-aside-line"><span>Held for handling</span><b>{metrics?.blocked_count ?? 0}</b></div><button onClick={() => onNavigate('Officer Review')}>Review cases <ArrowRight size={14} /></button></div>
    </div>
    <div className="metric-grid">
      <MetricCard label="In the queue" value={String(metrics?.application_count ?? cases.length).padStart(2, '0')} subline="Synthetic applications" icon={Users} accent="navy" />
      <MetricCard label="Evidence ready" value={String(metrics?.scoreable_count ?? 0).padStart(2, '0')} subline="Mandatory checks passed" trend="up" icon={FileCheck2} />
      <MetricCard label="Mean confidence" value={percent(metrics?.mean_confidence_index)} subline="Evidence quality index" icon={Gauge} accent="amber" />
      <MetricCard label="Review cost estimate" value={moneyCompact(metrics?.proposed_routing_cost_estimate_vnd)} subline="Illustrative · VND" icon={Banknote} accent="plum" />
    </div>
    <div className="dashboard-lower">
      <section className="surface route-overview">
        <div className="section-head"><div><div className="eyebrow">ROUTING MIX</div><h2>Review paths</h2></div><button className="text-button" onClick={() => onNavigate('Decision Routing')}>See routing logic <ArrowRight size={14} /></button></div>
        <div className="routing-bars">
          {(['FAST_TRACK_CANDIDATE', 'STANDARD_REVIEW', 'ENHANCED_REVIEW', 'HOLD_FOR_HUMAN_HANDLING'] as RouteName[]).map(route => {
            const count = metrics?.route_distribution[route] ?? 0
            const share = cases.length ? count / cases.length : 0
            return <div className="routing-bar-row" key={route}><div className="routing-bar-label"><span className={`route-dot ${routeClass(route)}`} /><span>{routeLabels[route]}</span><b>{count}</b></div><div className="routing-track"><div className={`routing-fill ${routeClass(route)}`} style={{ width: `${Math.max(share * 100, count ? 8 : 0)}%` }} /></div></div>
          })}
        </div>
        <div className="routing-note"><Info size={14} /><span>Routing distribution is calculated from this synthetic queue using illustrative rules.</span></div>
      </section>
      <section className="surface focus-card">
        <div className="section-head"><div><div className="eyebrow">PICK UP WHERE YOU LEFT OFF</div><h2>Case spotlight</h2></div><span className="spotlight-label">BASELINE</span></div>
        {cases.find(item => item.application_id === activeId) && <Spotlight item={cases.find(item => item.application_id === activeId)!} onOpen={onOpen} />}
      </section>
    </div>
    <section className="surface recent-section">
      <div className="section-head"><div><div className="eyebrow">YOUR QUEUE</div><h2>Recent applications <span className="section-count">{cases.length}</span></h2></div><button className="text-button" onClick={() => onNavigate('Applications')}>View all applications <ArrowRight size={14} /></button></div>
      <CaseTable cases={displayed} onSelect={onOpen} compact />
      <div className="table-footnote"><Info size={13} />All names and financial records shown are synthetic demonstration data.</div>
    </section>
  </>
}

function Spotlight({ item, onOpen }: { item: CaseRecord; onOpen: (id: string) => void }) {
  return <div className="spotlight-content">
    <div className="spotlight-person"><div className="case-avatar avatar-gold">{item.application_id.slice(-2)}</div><div><strong>{item.borrower_label}</strong><span>{item.application_id} <i>·</i> {dateLabel(item.submitted_at)}</span></div></div>
    <div className="spotlight-purchase"><span>{item.purchase_description}</span><strong>{money(item.purchase_amount_vnd)}</strong></div>
    <div className="spotlight-stats"><div><small>Confidence</small><strong className={scoreClass(item.assessment.confidence?.score)}>{percent(item.assessment.confidence?.score, 2)}</strong></div><div><small>Scenario score</small><strong>{percent(item.assessment.risk?.score, 3)}</strong></div></div>
    <div className="spotlight-route"><RouteBadge route={item.routing.recommended_route} /><span>{item.assessment.scoring_performed ? 'Suggested review path' : 'Scoring paused'}</span></div>
    <button className="button button-dark spotlight-button" onClick={() => onOpen(item.application_id)}>Open case <ArrowRight size={15} /></button>
  </div>
}

function ApplicationsPage({ cases, active, onSelect, onNavigate, onCreated }: { cases: CaseRecord[]; active: CaseRecord; onSelect: (id: string) => void; onNavigate: (page: PageName) => void; onCreated: (id: string) => Promise<void> }) {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('All cases')
  const [showCreate, setShowCreate] = useState(false)
  const filtered = cases.filter(item => {
    const matchesText = `${item.application_id} ${item.borrower_label} ${item.merchant} ${item.purchase_description} ${item.tags.join(' ')}`.toLowerCase().includes(query.toLowerCase())
    const matchesFilter = filter === 'All cases' || (filter === 'Needs human handling' && !item.assessment.scoring_performed) || (filter === 'Evidence ready' && item.assessment.scoring_performed)
    return matchesText && matchesFilter
  })
  return <>
    <PageTitle eyebrow="APPLICATION INBOX" title="Applications" description="Inspect submitted synthetic cases and follow each through the review workflow." action={<div className="heading-button-group"><button className="button button-outline" onClick={() => onNavigate('AI Assessment')}><HelpCircle size={15} /> How assessment works</button><button className="button button-dark" onClick={() => setShowCreate(true)}><BadgeCheck size={15} /> New synthetic case</button></div>} />
    <div className="queue-summary-row"><div className="queue-summary"><span className="queue-summary-icon"><WalletCards size={17} /></span><div><strong>{cases.length}</strong><span>Total cases</span></div></div><div className="queue-summary"><span className="queue-summary-icon queue-icon-green"><BadgeCheck size={17} /></span><div><strong>{cases.filter(item => item.assessment.scoring_performed).length}</strong><span>Evidence ready</span></div></div><div className="queue-summary"><span className="queue-summary-icon queue-icon-amber"><ShieldAlert size={17} /></span><div><strong>{cases.filter(item => !item.assessment.scoring_performed).length}</strong><span>Held for handling</span></div></div><div className="queue-summary queue-summary-note"><Info size={16} /><span>Every route remains a human review recommendation.</span></div></div>
    <div className="case-workspace">
      <section className="surface cases-list-panel">
        <div className="list-toolbar"><div className="list-title"><h2>Case inbox</h2><span>{filtered.length} shown</span></div><div className="list-controls"><label className="search-field"><Search size={15} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search cases" aria-label="Search applications" /><kbd>⌘ K</kbd></label><label className="select-wrap"><SlidersHorizontal size={14} /><select value={filter} onChange={event => setFilter(event.target.value)} aria-label="Filter applications"><option>All cases</option><option>Evidence ready</option><option>Needs human handling</option></select><ChevronDown size={13} /></label></div></div>
        <CaseTable cases={filtered} onSelect={onSelect} />
      </section>
      <aside className="surface case-preview">
        <div className="preview-top"><span className="eyebrow">SELECTED APPLICATION</span></div>
        <div className="preview-id">{active.application_id} <span className="tag-demo">DEMO</span></div>
        <h2>{active.borrower_label}</h2><p className="preview-sub">{active.merchant}</p>
        <div className="preview-amount"><span>Purchase amount</span><strong>{money(active.purchase_amount_vnd)}</strong><small>{active.purchase_description}</small></div>
        <div className="preview-divider" />
        <div className="preview-history"><div className="preview-section-title"><span>Income history</span><small>{active.monthly_income_vnd.length} months</small></div><div className="income-sparkline" aria-label="Synthetic monthly income trend">{active.monthly_income_vnd.map((amount, index) => <span key={index} title={money(amount)} style={{ height: `${Math.max(12, amount / Math.max(...active.monthly_income_vnd) * 100)}%` }} />)}</div><div className="preview-history-footer"><span>Monthly mean</span><b>{moneyCompact(active.assessment.features?.mean_income_vnd)}</b></div></div>
        <div className="preview-evidence"><div className="preview-section-title"><span>Financial evidence</span><small>{active.evidence.sources.length} sources</small></div>{active.evidence.sources.map((source, index) => <div className="evidence-source-mini" key={`${source.type}-${index}`}><span className={`evidence-source-icon ${source.verified ? 'source-verified' : 'source-unverified'}`}>{source.verified ? <Check size={10} /> : <Info size={10} />}</span><span><b>{source.name}</b><small>{source.months} months · {source.type.replaceAll('_', ' ').toLowerCase()}</small></span></div>)}<div className="preview-history-footer"><span>Reconciliation</span><b>{active.evidence.reconciliation_fields_consistent}/{active.evidence.reconciliation_fields_total} fields</b></div></div>
        <div className="preview-line"><span>Evidence score</span><strong className={scoreClass(active.assessment.confidence?.score)}>{percent(active.assessment.confidence?.score, 2)}</strong></div>
        <div className="preview-line"><span>Proposed path</span><RouteBadge route={active.routing.recommended_route} /></div>
        <div className="preview-line"><span>Submitted</span><strong className="preview-muted">{dateLabel(active.submitted_at)}</strong></div>
        <div className="preview-gates"><div className="eyebrow">MANDATORY CHECKS</div>{active.assessment.gates.map(gate => <div className="gate-mini" key={gate.key}><span className={`gate-mini-icon ${gate.passed ? 'gate-pass' : 'gate-fail'}`}>{gate.passed ? <Check size={12} /> : <X size={12} />}</span><span>{gate.label}</span></div>)}</div>
        <button className="button button-dark full-button" onClick={() => onNavigate('AI Assessment')}>Open assessment <ArrowRight size={15} /></button>
      </aside>
    </div>
    {showCreate && <NewCaseModal onClose={() => setShowCreate(false)} onCreated={async id => { setShowCreate(false); await onCreated(id) }} />}
  </>
}

function NewCaseModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => Promise<void> }) {
  const [borrower, setBorrower] = useState('Synthetic applicant')
  const [merchant, setMerchant] = useState('Northstar Electronics (synthetic)')
  const [purchase, setPurchase] = useState(8_000_000)
  const [income, setIncome] = useState(12_000_000)
  const [debt, setDebt] = useState(1_000_000)
  const [installment, setInstallment] = useState(2_000_000)
  const [consent, setConsent] = useState(true)
  const [identity, setIdentity] = useState(true)
  const [sourcePermission, setSourcePermission] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('')
    const stamp = Date.now()
    const id = `SYN-${String(stamp).slice(-6)}`
    const incomes = [0.91, 0.96, 1.02, 0.98, 1.04, 1.09].map(factor => Math.round(income * factor))
    try {
      await createApplication({
        application_id: id,
        borrower_label: borrower,
        product: 'Checkout installment',
        merchant,
        purchase_description: 'Synthetic checkout purchase',
        purchase_amount_vnd: purchase,
        loan_amount_vnd: purchase,
        proposed_installment_vnd: installment,
        submitted_at: new Date().toISOString(),
        consent,
        identity_verified: identity,
        source_permission: sourcePermission,
        funding_reconciled: true,
        existing_monthly_debt_vnd: debt,
        essential_monthly_expenses_vnd: income * 0.28,
        monthly_income_vnd: incomes,
        evidence: {
          reconciliation_fields_consistent: 7,
          reconciliation_fields_total: 8,
          verified_sources: 5,
          available_sources: 6,
          age_days: 2,
          sources: [{ name: 'Synthetic transaction history', type: 'BANK_FEED_DEMO', months: 6, verified: true, permission: sourcePermission ? 'synthetic consent fixture' : 'not granted' }],
          reconciliation_notes: ['Values entered for a local synthetic demonstration.'],
        },
      })
      await onCreated(id)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not add this synthetic case.') }
    finally { setBusy(false) }
  }
  return <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}><form className="surface create-modal" onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="create-title">
    <div className="modal-head"><div><div className="eyebrow">LOCAL FIXTURE · NOT A REAL APPLICATION</div><h2 id="create-title">Add synthetic case</h2></div><button type="button" className="icon-button" aria-label="Close" onClick={onClose}><X size={17} /></button></div>
    <div className="modal-fields"><label>Applicant label<input required value={borrower} onChange={event => setBorrower(event.target.value)} maxLength={100} /></label><label>Merchant<input required value={merchant} onChange={event => setMerchant(event.target.value)} maxLength={120} /></label><label>Purchase amount · VND<input required type="number" min={1} value={purchase} onChange={event => setPurchase(Number(event.target.value))} /></label><label>Mean monthly income · VND<input required type="number" min={1} value={income} onChange={event => setIncome(Number(event.target.value))} /></label><label>Existing monthly debt · VND<input required type="number" min={0} value={debt} onChange={event => setDebt(Number(event.target.value))} /></label><label>Proposed installment · VND<input required type="number" min={1} value={installment} onChange={event => setInstallment(Number(event.target.value))} /></label></div>
    <div className="modal-toggles"><Toggle label="Consent" checked={consent} onChange={setConsent} /><Toggle label="Identity passed" checked={identity} onChange={setIdentity} /><Toggle label="Source permission" checked={sourcePermission} onChange={setSourcePermission} /></div>
    {error && <div className="form-error"><CircleAlert size={14} />{error}</div>}
    <div className="modal-actions"><button type="button" className="button button-outline" onClick={onClose}>Cancel</button><button className="button button-dark" type="submit" disabled={busy}>{busy ? 'Adding…' : 'Add to case queue'} <ArrowRight size={14} /></button></div>
  </form></div>
}

function CaseTable({ cases, onSelect, compact = false }: { cases: CaseRecord[]; onSelect: (id: string) => void; compact?: boolean }) {
  return <div className={`table-wrap ${compact ? 'table-compact' : ''}`}>
    <table className="cases-table"><thead><tr><th>APPLICATION</th><th>AMOUNT</th><th>EVIDENCE CS</th><th>SCENARIO SCORE</th><th>REVIEW PATH</th><th aria-label="Open case" /></tr></thead><tbody>
      {cases.map(item => <tr key={item.application_id} className={item.assessment.scoring_performed ? '' : 'row-held'} onClick={() => onSelect(item.application_id)} tabIndex={0} onKeyDown={event => { if (event.key === 'Enter') onSelect(item.application_id) }}>
        <td><div className="table-case"><div className={`case-avatar ${item.application_id === 'DEMO-001' ? 'avatar-gold' : ''}`}>{item.application_id.slice(-2)}</div><div><strong>{item.borrower_label}</strong><span>{item.application_id} <i>·</i> {item.merchant.split(' ')[0]}</span></div></div></td>
        <td><strong className="table-money">{moneyCompact(item.purchase_amount_vnd)}</strong><small>{item.purchase_description}</small></td>
        <td><span className={`score-cell ${scoreClass(item.assessment.confidence?.score)}`}>{percent(item.assessment.confidence?.score, 2)}</span></td>
        <td><span className="pd-cell">{percent(item.assessment.risk?.score, 3)}</span></td>
        <td><RouteBadge route={item.routing.recommended_route} /></td>
        <td><ChevronRight className="table-chevron" size={16} /></td>
      </tr>)}
      {cases.length === 0 && <tr><td colSpan={6} className="empty-row">No applications match those filters.</td></tr>}
    </tbody></table>
  </div>
}

function AssessmentPage({ active, onNavigate }: { active: CaseRecord; onNavigate: (page: PageName) => void }) {
  const assessment = active.assessment
  return <>
    <CaseContext active={active} onNavigate={onNavigate} current="AI Assessment" />
    <EvidenceShadow applicationId={active.application_id} onResearch={() => onNavigate('Evidence AI Research')} />
    <PageTitle eyebrow="TRANSPARENT CALCULATIONS" title="AI assessment" description="A review aid that shows the inputs, formulas and provenance behind every number." action={<span className="demo-status"><Sparkles size={14} /> Synthetic demonstration</span>} />
    <p className="research-policy"><ShieldCheck size={15} /> Checkout PD and expected loss require bank validation. Policy {assessment.policy_version} · Fixture {assessment.fixture_version}</p>
    {!assessment.scoring_performed ? <BlockedPanel assessment={assessment} /> : <>
      <div className="assessment-hero-grid">
        <section className="surface confidence-feature">
          <div className="assessment-card-top"><div><div className="eyebrow">EVIDENCE CONFIDENCE SCORE</div><h2>How complete is the picture?</h2></div><HelpCircle size={17} /></div>
          <div className="confidence-main"><div className="confidence-ring" style={{ '--score': `${(assessment.confidence!.score * 100).toFixed(3)}%` } as CSSProperties}><div><strong>{assessment.confidence!.score.toFixed(2)}</strong><small>of 1.00</small></div></div><div className="confidence-copy"><span className="score-kicker">QUALITY INDEX</span><h3>Evidence confidence</h3><p>This score summarizes evidence coverage and quality. It is not a probability of default.</p><div className="formula-chip">CS = Σ (weight × evidence subscore)</div></div></div>
          <div className="confidence-breakdown">{Object.entries(assessment.confidence!.subscores).map(([key, value]) => <div className="confidence-row" key={key}><div className="confidence-label"><span>{prettyKey(key)}</span><strong>{value.toFixed(3)}</strong></div><div className="confidence-track"><span style={{ width: `${value * 100}%` }} /></div><small>{percent(assessment.confidence!.weights[key])} weight <i>·</i> {assessment.confidence!.weighted_contributions[key].toFixed(3)} contribution</small></div>)}</div>
          <div className="provenance-note"><FileSearch size={14} /><span>Computed from {assessment.confidence!.inputs.income_history_months} monthly records, {assessment.confidence!.inputs.reconciliation_fields_consistent}/{assessment.confidence!.inputs.reconciliation_fields_total} reconciled fields and {assessment.confidence!.inputs.verified_sources}/{assessment.confidence!.inputs.available_sources} verified sources.</span></div>
          <details className="method-details"><summary>Completeness gaps</summary><ul>{Object.entries(assessment.confidence!.completeness_gaps).map(([key, count]) => <li key={key}>{prettyKey(key)} · {count}</li>)}</ul></details>
        </section>
        <div className="assessment-side-stack">
          <section className="surface risk-card"><div className="assessment-card-top"><div><div className="eyebrow">SYNTHETIC RISK SCENARIO</div><h2>Synthetic score</h2></div><div className="risk-stamp"><Activity size={15} /></div></div>
            <div className="risk-number">{percent(assessment.risk?.score, 3)}<span>synthetic score</span></div><div className="risk-caution"><CircleAlert size={14} /><span>Not trained or calibrated. Do not use for real credit decisions.</span></div><details className="method-details"><summary>Show calculation <ChevronDown size={13} /></summary><p>{assessment.risk?.formula}</p><div className="method-inline">Logit <b>{assessment.risk?.logit.toFixed(4)}</b><span /> Intercept <b>{assessment.risk?.intercept.toFixed(4)}</b></div><small>{assessment.risk?.reference_parity}</small></details>
          </section>
          <section className="surface loss-card"><div className="assessment-card-top"><div><div className="eyebrow">ILLUSTRATIVE EXPECTED LOSS</div><h2>Exposure estimate</h2></div><Banknote size={17} /></div><div className="loss-number">{money(assessment.expected_loss?.amount_vnd)}</div><p className="loss-formula">{assessment.expected_loss?.calculation}</p><div className="loss-inputs"><div><span>Scenario score</span><b>{percent(assessment.expected_loss?.pd_demo, 3)}</b></div><div><span>LGD assumption</span><b>{percent(assessment.expected_loss?.lgd_assumption, 0)}</b></div><div><span>EAD assumption</span><b>{money(assessment.expected_loss?.ead_assumption_vnd)}</b></div></div></section>
        </div>
      </div>
      <section className="surface feature-engineering-card"><div className="section-head"><div><div className="eyebrow">P3 · DERIVED FROM MONTHLY INCOME HISTORY</div><h2>Financial features</h2></div><FileSearch size={16} /></div><div className="financial-feature-grid">{[
        ['Mean monthly income', money(assessment.features?.mean_income_vnd), 'Arithmetic mean of the supplied records'],
        ['Income standard deviation', money(assessment.features?.income_standard_deviation_vnd), 'Population standard deviation'],
        ['Income coefficient of variation', percent(assessment.features?.income_cv, 2), 'Standard deviation ÷ mean income'],
        ['25th percentile income', money(assessment.features?.income_p25_vnd), 'Linear interpolation at (n − 1) × 0.25'],
        ['Existing debt-to-income', percent(assessment.features?.existing_dti_ratio, 2), 'Existing monthly debt ÷ mean income'],
        ['History coverage', percent(assessment.features?.history_coverage, 1), `${assessment.features?.history_months} observed of 12 months`],
      ].map(([label, value, note]) => <div className="financial-feature" key={label}><small>{label}</small><strong>{value}</strong><span>{note}</span></div>)}</div></section>
      <section className="surface affordability-section"><div className="section-head"><div><div className="eyebrow">MONTHLY PAYMENT CAPACITY</div><h2>Affordability check</h2></div><span className={`eligibility-pill ${assessment.affordability?.installment_eligible ? 'eligible' : 'not-eligible'}`}>{assessment.affordability?.installment_eligible ? <><CheckCircle2 size={14} /> Within illustrative capacity</> : <><ShieldAlert size={14} /> Outside capacity</>}</span></div>
        <div className="capacity-layout"><div className="capacity-main"><div className="capacity-label"><span>Stressed payment capacity</span><HelpCircle size={14} /></div><strong>{money(assessment.affordability?.stressed_payment_capacity_vnd)}</strong><div className="capacity-track"><div className="capacity-payment" style={{ width: `${Math.min(100, (assessment.affordability!.proposed_installment_vnd / Math.max(assessment.affordability!.stressed_payment_capacity_vnd, 1)) * 100)}%` }} /><div className="capacity-limit" /></div><div className="capacity-legend"><span><i className="legend-square" /> Proposed instalment {money(assessment.affordability?.proposed_installment_vnd)}</span><span><i className="legend-dash" /> Available capacity</span></div></div><div className="capacity-details"><div><span>Income residual</span><strong>{money(assessment.affordability?.income_residual_vnd)}</strong></div><div><span>Repayment buffer</span><strong className={assessment.affordability!.repayment_buffer_vnd >= 0 ? 'positive' : 'negative'}>{money(assessment.affordability?.repayment_buffer_vnd)}</strong></div><div><span>PMT calculation</span><strong>{assessment.affordability?.pmt_vnd ? money(assessment.affordability.pmt_vnd) : 'Not supplied'}</strong></div></div></div>
        <details className="method-details affordability-method"><summary>Formula and inputs <ChevronDown size={13} /></summary>
          <p>{assessment.affordability?.calculation}</p>
          <p>DTI capacity {money(assessment.affordability?.dti_capacity_vnd)} · Residual capacity {money(assessment.affordability?.residual_capacity_vnd)} · P25 income {money(assessment.affordability?.stress_income_vnd)} · Buffer {percent(assessment.affordability?.residual_buffer_assumption, 0)}</p>
          <small>Mean income {money(assessment.features?.mean_income_vnd)} · Existing debt {money(assessment.features?.existing_monthly_debt_vnd)} · Essentials {money(assessment.affordability?.essential_monthly_expenses_vnd)} · DTI cap {percent(assessment.affordability?.max_dti_assumption, 0)} · {assessment.affordability?.installment_basis}</small>
          {assessment.affordability?.stated_installment_differs_from_pmt && <p>Declared installment differs from contract PMT. Capacity uses the contract calculation.</p>}
        </details>
      </section>
      <section className="surface affordability-section">
        <details className="method-details"><summary>Illustrative loss sensitivity</summary>
          <div className="table-wrap"><table className="cases-table"><thead><tr><th>LGD</th><th>EAD</th><th>Scenario loss</th></tr></thead><tbody>
            {assessment.expected_loss?.sensitivity.map(row => <tr key={[row.lgd, row.ead_vnd].join('/')}><td>{percent(row.lgd, 0)}</td><td>{money(row.ead_vnd)}</td><td>{money(row.amount_vnd)}</td></tr>)}
          </tbody></table></div>
        </details>
        <details className="method-details"><summary>Income observations and model provenance</summary><p>{active.monthly_income_vnd.map(money).join(' · ')}</p><p>{assessment.model.version} · {assessment.model.scope} · {assessment.pd_status}</p></details>
      </section>
      <div className="assessment-actions"><div><span>Still a human decision</span><small>This assessment can inform review, but cannot create or approve a loan.</small></div><button className="button button-dark" onClick={() => onNavigate('Decision Routing')}>Continue to routing <ArrowRight size={15} /></button></div>
    </>}
  </>
}

function BlockedPanel({ assessment }: { assessment: Assessment }) {
  return <section className="surface blocked-panel"><div className="blocked-icon"><LockKeyhole size={22} /></div><div><div className="eyebrow">SCORING PAUSED</div><h2>Mandatory checks need attention</h2><p>{assessment.notice}</p><div className="blocked-gates">{assessment.gates.filter(gate => !gate.passed).map(gate => <div key={gate.key}><X size={14} />{gate.label}</div>)}</div><p className="blocked-foot">No confidence score, demo risk score or expected loss was calculated for this case.</p></div></section>
}

function RoutingPage({ active, onNavigate }: { active: CaseRecord; onNavigate: (page: PageName) => void }) {
  const routing = active.routing
  return <>
    <CaseContext active={active} onNavigate={onNavigate} current="Decision Routing" />
    <PageTitle eyebrow="POLICY-CONSTRAINED ROUTING" title="Decision routing" description="Hard checks first. Then compare the estimated cost of eligible review paths." action={<span className="policy-status"><ShieldAlert size={14} /> Illustrative policy</span>} />
    <div className="routing-summary-grid"><section className="surface proposed-route-card"><div className="eyebrow">RECOMMENDED NEXT STEP</div><div className="proposed-route-title"><div className={`route-illustration ${routeClass(routing.recommended_route)}`}>{routing.recommended_route === 'HOLD_FOR_HUMAN_HANDLING' ? <LockKeyhole size={23} /> : <Activity size={23} />}</div><div><span>Review path</span><h2>{routeLabels[routing.recommended_route]}</h2></div></div><p>{routing.explanations[0]}</p><div className="route-card-footer"><span><UserRound size={14} /> Requires officer confirmation</span><b>{money(routing.estimated_route_costs_vnd[routing.recommended_route])}</b></div></section>
      <section className="surface route-objective-card"><div className="objective-icon"><BarChart3 size={17} /></div><div className="eyebrow">COST OBJECTIVE</div><h3>Lowest-cost eligible path</h3><p>{routing.objective}</p><div className="objective-flag"><Info size={14} /> Route costs and eligibility thresholds are demo assumptions. Bank validation is pending.</div></section></div>
    <section className="surface policy-gates-card"><div className="section-head"><div><div className="eyebrow">P1 · HARD CONSTRAINTS</div><h2>Mandatory policy gates</h2></div><span className={`gate-summary ${active.assessment.scoring_performed ? 'gate-summary-pass' : 'gate-summary-fail'}`}>{active.assessment.scoring_performed ? 'All passed' : 'Automated scoring stopped'}</span></div><div className="policy-gates-grid">{active.assessment.gates.map((gate, index) => <div className={`policy-gate ${gate.passed ? 'passed' : 'failed'}`} key={gate.key}><span className="policy-gate-number">0{index + 1}</span><span className="policy-gate-icon">{gate.passed ? <Check size={14} /> : <X size={14} />}</span><div><strong>{gate.label}</strong><small>{gate.passed ? 'Verified for this synthetic scenario' : 'Failed · blocks automated scoring'}</small></div></div>)}</div></section>
    <section className="surface route-compare-card"><div className="section-head"><div><div className="eyebrow">P8 · FEASIBLE ROUTES</div><h2>Compare review cost</h2></div><span className="estimate-label"><Info size={13} /> Estimates · VND</span></div><div className="route-compare-list">{routing.route_comparison.map(item => <div className={`route-compare-row ${item.selected ? 'route-row-selected' : ''} ${!item.eligible ? 'route-row-disabled' : ''}`} key={item.route}><div className="route-compare-name"><span className={`route-dot ${routeClass(item.route)}`} /><div><strong>{routeLabels[item.route]}</strong><small>{item.reason}</small></div></div><div className="route-compare-cost"><strong>{money(item.estimated_cost_vnd)}</strong>{item.selected ? <span className="selected-chip"><Check size={11} /> Recommended</span> : !item.eligible && <span className="ineligible-chip">Not eligible</span>}</div><div className="route-compare-bar"><span className={routeClass(item.route)} style={{ width: `${Math.max(8, item.estimated_cost_vnd / Math.max(...routing.route_comparison.map(row => row.estimated_cost_vnd)) * 100)}%` }} /></div></div>)}</div><div className="route-compare-foot"><ShieldCheck size={15} /><span>Route eligibility depends on the policy gates. Costs determine the order among eligible paths.</span></div></section>
    <section className="surface routing-explanation"><div className="explanation-icon"><FileSearch size={17} /></div><div><div className="eyebrow">WHY THIS ROUTE?</div><h3>Route rationale</h3><ul>{routing.explanations.map((reason, index) => <li key={index}>{reason}</li>)}</ul></div></section>
  </>
}

function ReviewPage({ active, onNavigate, onUpdated }: { active: CaseRecord; onNavigate: (page: PageName) => void; onUpdated: (message: string) => Promise<void> }) {
  const [action, setAction] = useState<'confirm_route' | 'request_evidence' | 'escalate' | 'override_route' | 'consent_revoked'>('confirm_route')
  const [route, setRoute] = useState<RouteName>(active.routing.recommended_route)
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [history, setHistory] = useState<AuditEvent[]>(active.review_history)
  useEffect(() => { setRoute(active.routing.recommended_route); setHistory(active.review_history) }, [active.application_id, active.review_history, active.routing.recommended_route])
  const isOverride = action === 'override_route'
  const canSubmit = reason.trim().length >= 12 && !saving && (!isOverride || active.routing.eligible_routes.includes(route))
    && (action !== 'consent_revoked' || !active.consent_revoked_at)
  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true); setError('')
    try {
      if (action === 'consent_revoked') {
        await revokeConsent(active.application_id, reason)
        setAction('confirm_route')
      } else {
        await sendReviewAction(active.application_id, { action, reason, ...(isOverride ? { route } : {}) })
      }
      setReason('')
      await onUpdated('Review action recorded in the audit history.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save this review action.')
    } finally { setSaving(false) }
  }
  return <>
    <CaseContext active={active} onNavigate={onNavigate} current="Officer Review" />
    <PageTitle eyebrow="HUMAN REVIEW · APPEND-ONLY AUDIT" title="Officer review" description="Record a reasoned review action. This screen does not approve a loan." action={<span className="human-only-badge"><UserRound size={14} /> Human authority only</span>} />
    <div className="review-layout"><div className="review-main-column">
      <section className="surface review-decision-card"><div className="review-card-header"><div><div className="eyebrow">PROPOSED REVIEW PATH</div><h2>{routeLabels[active.routing.recommended_route]}</h2></div><RouteBadge route={active.routing.recommended_route} /></div><div className="review-case-row"><div className="review-mini-metric"><span>Evidence confidence</span><strong>{percent(active.assessment.confidence?.score, 2)}</strong></div><div className="review-mini-metric"><span>Scenario score</span><strong>{percent(active.assessment.risk?.score, 3)}</strong></div><div className="review-mini-metric"><span>Installment eligible</span><strong className={active.assessment.affordability?.installment_eligible ? 'positive' : 'negative'}>{active.assessment.affordability ? active.assessment.affordability.installment_eligible ? 'Yes' : 'No' : 'Not scored'}</strong></div></div><div className="review-guardrail"><ShieldCheck size={15} /><span>Permitted actions record review, evidence requests or escalation. No action here creates a credit offer or loan approval.</span></div></section>
      <form className="surface review-action-form" onSubmit={handleSubmit}><div className="section-head"><div><div className="eyebrow">REVIEW ACTION</div><h2>What should happen next?</h2></div><FileCheck2 size={17} /></div>
        <div className="action-choice-grid">{[
          ['confirm_route', 'Confirm review path', 'Acknowledge the current recommendation.', <CheckCircle2 size={16} />],
          ['request_evidence', 'Request more evidence', 'Pause for a specific missing item.', <FileClock size={16} />],
          ['escalate', 'Escalate case', 'Send the case for additional human review.', <ShieldAlert size={16} />],
          ['override_route', 'Change review path', 'Choose another eligible route with a reason.', <RefreshCw size={16} />],
          ...(!active.consent_revoked_at ? [['consent_revoked', 'Record consent withdrawal', 'Stop scoring for this synthetic case.', <LockKeyhole size={16} />]] : []),
        ].map(([id, label, desc, icon]) => <button type="button" key={String(id)} className={`action-choice ${action === id ? 'action-choice-active' : ''}`} onClick={() => { setAction(id as typeof action); setError('') }}><span className="action-choice-icon">{icon as ReactNode}</span><span className="action-choice-copy"><strong>{label as string}</strong><small>{desc as string}</small></span>{action === id && <span className="action-choice-check"><Check size={12} /></span>}</button>)}</div>
        {isOverride && <label className="form-field route-select-field"><span>New review route <i>· choose an eligible path</i></span><div className="select-field-control"><select value={route} onChange={event => setRoute(event.target.value as RouteName)}>{active.routing.eligible_routes.map(value => <option value={value} key={value}>{routeLabels[value]}</option>)}</select><ChevronDown size={15} /></div></label>}
        <label className="form-field reason-field"><span>Reason for this action <b>Required</b></span><textarea value={reason} onChange={event => setReason(event.target.value)} rows={4} maxLength={1000} placeholder="Write the evidence or policy context behind this action. The reason becomes part of the case audit record." /><small>{reason.trim().length}/1000 characters · Minimum 12 characters</small></label>
        {error && <div className="form-error"><CircleAlert size={14} />{error}</div>}
        <div className="form-submit-row"><p><LockKeyhole size={13} />Audit events are append-only and timestamped.</p><button className="button button-dark" type="submit" disabled={!canSubmit}>{saving ? 'Recording…' : 'Record review action'} <ArrowRight size={15} /></button></div>
      </form>
    </div><aside className="surface audit-panel"><div className="audit-panel-head"><div><div className="eyebrow">CASE RECORD</div><h2>Audit history</h2></div><span className="audit-count">{history.length}</span></div><div className="audit-timeline">{history.length === 0 ? <div className="audit-empty"><History size={20} /><span>No actions recorded yet.</span><small>Your review actions will appear here.</small></div> : history.map((event, index) => <div className="audit-event" key={event.event_id}><div className={`audit-event-marker ${index === 0 ? 'audit-event-current' : ''}`}>{auditIcon(event.action)}</div><div className="audit-event-content"><div className="audit-event-title">{actionLabel(event.action)}</div><span className="audit-event-time">{timeLabel(event.created_at)}</span><p>{event.reason}</p>{event.route && <RouteBadge route={event.route} />}<small className="audit-event-actor"><UserRound size={11} /> {event.actor}</small></div></div>)}</div><div className="audit-integrity"><ShieldCheck size={15} /><span>Protected log<br /><small>Events cannot be edited or removed.</small></span></div></aside></div>
  </>
}

function auditIcon(action: string) {
  if (action === 'confirm_route') return <Check size={13} />
  if (action === 'request_evidence') return <FileSearch size={13} />
  if (action === 'escalate') return <ArrowUpRight size={13} />
  if (action === 'override_route') return <RefreshCw size={13} />
  return <ReceiptText size={13} />
}

function actionLabel(action: string) {
  return ({ application_received: 'Application received', confirm_route: 'Review path confirmed', request_evidence: 'Evidence requested', escalate: 'Case escalated', override_route: 'Review path changed' } as Record<string, string>)[action] ?? action
}

function SimulatorPage({ active, onNavigate }: { active: CaseRecord; onNavigate: (page: PageName) => void }) {
  const [income, setIncome] = useState(average(active.monthly_income_vnd) / 1_000_000)
  const [debt, setDebt] = useState(active.existing_monthly_debt_vnd / 1_000_000)
  const [installment, setInstallment] = useState(active.proposed_installment_vnd / 1_000_000)
  const [quality, setQuality] = useState(baseEvidenceQuality(active))
  const [consent, setConsent] = useState(active.consent)
  const [identityVerified, setIdentityVerified] = useState(active.identity_verified)
  const [maxDti, setMaxDti] = useState(0.35)
  const [residualBuffer, setResidualBuffer] = useState(0.25)
  const [checkBenchmark, setCheckBenchmark] = useState(false)
  const [fastCost, setFastCost] = useState(42000)
  const [standardCost, setStandardCost] = useState(110000)
  const [result, setResult] = useState<Awaited<ReturnType<typeof runSimulation>> | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setIncome(average(active.monthly_income_vnd) / 1_000_000)
    setDebt(active.existing_monthly_debt_vnd / 1_000_000)
    setInstallment(active.proposed_installment_vnd / 1_000_000)
    setQuality(baseEvidenceQuality(active))
    setConsent(active.consent); setIdentityVerified(active.identity_verified); setResult(null)
  }, [active.application_id, active.assessment.features, active.existing_monthly_debt_vnd, active.proposed_installment_vnd, active.evidence, active.consent, active.identity_verified, active.monthly_income_vnd])

  const simulate = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('')
    const baselineAverage = average(active.monthly_income_vnd)
    const incomeFactor = income * 1_000_000 / baselineAverage
    try {
      const response = await runSimulation(active.application_id, {
        ...(income !== baselineAverage / 1_000_000 ? { monthly_income_vnd: active.monthly_income_vnd.map(value => Math.round(value * incomeFactor)) } : {}),
        ...(debt !== active.existing_monthly_debt_vnd / 1_000_000 ? { existing_monthly_debt_vnd: Math.round(debt * 1_000_000) } : {}),
        ...(installment !== active.proposed_installment_vnd / 1_000_000 ? { proposed_installment_vnd: Math.round(installment * 1_000_000) } : {}),
        ...(quality !== baseEvidenceQuality(active) ? { evidence_quality: quality } : {}),
        consent,
        identity_verified: identityVerified,
        max_dti: maxDti,
        residual_buffer: residualBuffer,
        ...(checkBenchmark ? { benchmark_model_id: 'uci350-v2.0-selected' } : {}),
        route_costs_vnd: { FAST_TRACK_CANDIDATE: fastCost, STANDARD_REVIEW: standardCost },
      })
      setResult(response)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not run this scenario.') }
    finally { setBusy(false) }
  }
  const displayedAssessment = result?.assessment ?? active.assessment
  const displayedRoute = result?.routing ?? active.routing
  return <>
    <CaseContext active={active} onNavigate={onNavigate} current="What-if Simulator" />
    <PageTitle eyebrow="SCENARIO WORKBENCH" title="What-if simulator" description="Adjust synthetic inputs, rerun the transparent calculations and compare the proposed path." action={<span className="demo-status"><SlidersHorizontal size={14} /> Changes are not saved</span>} />
    <div className="simulator-grid"><form className="surface simulator-controls" onSubmit={simulate}><div className="simulator-form-head"><div className="eyebrow">CHANGE SCENARIO INPUTS</div><h2>Adjust the numbers</h2><p>Each run is temporary and scoped to {active.application_id}.</p></div>
      <div className="sim-controls-grid">
        <label className="sim-control"><span>Stressed residual buffer <b>{percent(residualBuffer, 0)}</b></span><input type="range" min="0" max="0.75" step="0.01" value={residualBuffer} onChange={event => setResidualBuffer(Number(event.target.value))} /></label>
        <label className="sim-control"><span>Mean monthly income <b>{income.toFixed(1)}m ₫</b></span><input type="range" min="4" max="30" step="0.1" value={income} onChange={event => setIncome(Number(event.target.value))} /><div className="range-minmax"><small>4m</small><small>30m VND</small></div></label>
        <label className="sim-control"><span>Existing monthly debt <b>{debt.toFixed(2)}m ₫</b></span><input type="range" min="0" max="15" step="0.05" value={debt} onChange={event => setDebt(Number(event.target.value))} /><div className="range-minmax"><small>0</small><small>15m VND</small></div></label>
        <label className="sim-control"><span>Proposed instalment <b>{installment.toFixed(2)}m ₫</b></span><input type="range" min="0.2" max="8" step="0.05" value={installment} onChange={event => setInstallment(Number(event.target.value))} /><div className="range-minmax"><small>0.2m</small><small>8m VND</small></div></label>
        <label className="sim-control"><span>Evidence quality <b>{percent(quality, 0)}</b></span><input type="range" min="0" max="1" step="0.01" value={quality} onChange={event => setQuality(Number(event.target.value))} /><div className="range-minmax"><small>Incomplete</small><small>Fully checked</small></div></label>
        <label className="sim-control"><span>Maximum DTI assumption <b>{percent(maxDti, 0)}</b></span><input type="range" min="0.15" max="0.55" step="0.01" value={maxDti} onChange={event => setMaxDti(Number(event.target.value))} /><div className="range-minmax"><small>15%</small><small>55%</small></div></label>
      </div>
      <label><input type="checkbox" checked={checkBenchmark} onChange={event => setCheckBenchmark(event.target.checked)} /> Check UCI benchmark compatibility</label>
      <div className="sim-costs"><div className="eyebrow">ILLUSTRATIVE ROUTE COSTS</div><div className="sim-cost-fields"><label>Fast-track estimate <span><input type="number" min="0" step="1000" value={fastCost} onChange={event => setFastCost(Number(event.target.value))} /> ₫</span></label><label>Standard estimate <span><input type="number" min="0" step="1000" value={standardCost} onChange={event => setStandardCost(Number(event.target.value))} /> ₫</span></label></div><small>These costs are demo assumptions, not bank estimates.</small></div>
      <div className="sim-toggle-row"><div><strong>Mandatory checks</strong><small>Consent, identity and source access gate scoring.</small></div><div className="sim-toggles"><Toggle label="Consent" checked={consent} onChange={setConsent} /><Toggle label="Identity" checked={identityVerified} onChange={setIdentityVerified} /></div></div>
      <button className="button button-dark simulate-button" type="submit" disabled={busy}>{busy ? <><RefreshCw size={15} className="spin" /> Recalculating…</> : <><Activity size={15} /> Run scenario</>}</button>
      {error && <div className="form-error"><CircleAlert size={14} />{error}</div>}
    </form>
    <div className="simulator-output"><section className="surface scenario-result"><div className="scenario-result-head"><div><div className="eyebrow">SCENARIO RESULT</div><h2>{result ? 'Updated calculation' : 'Current baseline'}</h2></div><span className={`unsaved-pill ${result ? 'unsaved-updated' : ''}`}><span />{result ? 'SIMULATED' : 'BASELINE'}</span></div><p className="scenario-muted">{result ? 'Result is traceable to the inputs at left and has not been saved to the case.' : 'Run the scenario to see how changed inputs affect the outputs.'}</p>
      {displayedAssessment.pd_status === 'PD_UNAVAILABLE_SCHEMA_MISMATCH' && <p role="status" className="research-alert">PD_UNAVAILABLE_SCHEMA_MISMATCH · UCI features and label horizon differ from checkout. The panel below shows only synthetic calculations.</p>}
      {!displayedAssessment.scoring_performed ? <div className="scenario-blocked"><LockKeyhole size={17} /><div><strong>Scoring blocked</strong><span>{displayedAssessment.notice}</span></div></div> : <>
        <div className="scenario-stat-grid"><ScenarioStat label="Confidence score" value={displayedAssessment.confidence?.score.toFixed(3) ?? '—'} note="Evidence quality" /><ScenarioStat label="Scenario score" value={percent(displayedAssessment.risk?.score, 3)} note="Not calibrated" /><ScenarioStat label="Payment capacity" value={moneyCompact(displayedAssessment.affordability?.stressed_payment_capacity_vnd)} note={displayedAssessment.affordability?.installment_eligible ? 'Within capacity' : 'Outside capacity'} /><ScenarioStat label="Expected loss" value={moneyCompact(displayedAssessment.expected_loss?.amount_vnd)} note="Illustrative" /></div>
        <div className="scenario-recommendation"><div className="scenario-route-icon"><Activity size={16} /></div><div><small>RECOMMENDED REVIEW PATH</small><strong>{routeLabels[displayedRoute.recommended_route]}</strong></div><RouteBadge route={displayedRoute.recommended_route} /></div>
      </>}
      {result && <details className="scenario-trace"><summary><FileSearch size={13} /> View input trace <ChevronDown size={13} /></summary><pre>{JSON.stringify(result.scenario_inputs, null, 2)}</pre></details>}
      <div className="scenario-footnote"><Info size={13} />No changed values are written to the application record.</div></section>
      <section className="surface scenario-compare"><div className="eyebrow">ROUTE COST COMPARISON</div><h3>Eligible path estimates</h3>{displayedRoute.route_comparison.map(row => <div className={`scenario-route-row ${row.selected ? 'scenario-route-selected' : ''}`} key={row.route}><span className={`route-dot ${routeClass(row.route)}`} /><span>{routeShort[row.route]}</span><strong>{money(row.estimated_cost_vnd)}</strong>{row.selected ? <Check size={14} /> : !row.eligible && <LockKeyhole size={12} />}</div>)}<div className="scenario-compare-note">Cost optimization is applied only after mandatory and affordability gates.</div></section></div></div>
  </>
}

function EvaluationPage() {
  const [logs, setLogs] = useState<{ application_id: string; assessment_status: string; recommended_route: RouteName; eligible_routes: RouteName[]; confidence_index: number | null; pd_demo: number | null; risk_label: string | null }[]>([])
  const [metrics, setMetrics] = useState<PortfolioMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState(false)
  useEffect(() => {
    Promise.all([
      request<{ logs: typeof logs }>('/evaluation'),
      getMetrics(),
    ]).then(([evaluation, nextMetrics]) => { setLogs(evaluation.logs); setMetrics(nextMetrics) })
      .catch(cause => setError(cause instanceof Error ? cause.message : 'Could not load this demonstration snapshot.'))
      .finally(() => setLoading(false))
  }, [])
  const handleExport = async () => {
    setExporting(true); setError('')
    try { await downloadExport() } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not export the case data.') }
    finally { setExporting(false) }
  }
  return <>
    <PageTitle eyebrow="SIMULATED OPERATIONS · NOT OBSERVED PERFORMANCE" title="Monitoring & export" description="Inspect the seeded evaluation log, cost comparison and synthetic route mix." action={<button className="button button-dark" onClick={() => void handleExport()} disabled={exporting}><Download size={15} />{exporting ? 'Preparing…' : 'Export JSON'}</button>} />
    {error && <div className="form-error evaluation-error"><CircleAlert size={14} />{error}</div>}
    {loading ? <div className="surface evaluation-loading">Loading the synthetic evaluation snapshot…</div> : <>
      <div className="evaluation-banner"><div className="evaluation-banner-icon"><Info size={17} /></div><div><strong>Illustrative comparison only</strong><span>These counts and cost estimates describe the six synthetic fixtures currently in this workspace. They are not measured portfolio outcomes or model performance.</span></div><span className="evaluation-banner-tag">SIMULATED</span></div>
      <div className="evaluation-metrics-grid"><div className="surface evaluation-metric"><span>Applications evaluated</span><strong>{metrics?.application_count ?? 0}</strong><small>{metrics?.scoreable_count ?? 0} scoreable <i>·</i> {metrics?.blocked_count ?? 0} blocked</small></div><div className="surface evaluation-metric"><span>Estimated routing cost</span><strong>{moneyCompact(metrics?.proposed_routing_cost_estimate_vnd)}</strong><small>Illustrative current recommendations</small></div><div className="surface evaluation-metric"><span>Reference baseline cost</span><strong>{moneyCompact(metrics?.baseline_all_standard_cost_estimate_vnd)}</strong><small>Fixed order among eligible routes</small></div><div className="surface evaluation-metric"><span>Estimated difference</span><strong className={metrics && metrics.estimated_cost_difference_vnd >= 0 ? 'positive' : 'negative'}>{moneyCompact(metrics?.estimated_cost_difference_vnd)}</strong><small>Scenario arithmetic, not realized savings</small></div></div>
      <div className="evaluation-grid"><section className="surface evaluation-routes"><div className="section-head"><div><div className="eyebrow">CURRENT FIXTURE ROUTING</div><h2>Route distribution</h2></div><Activity size={16} /></div><div className="evaluation-route-list">{(['FAST_TRACK_CANDIDATE', 'STANDARD_REVIEW', 'ENHANCED_REVIEW', 'HOLD_FOR_HUMAN_HANDLING'] as RouteName[]).map(route => { const count = metrics?.route_distribution[route] ?? 0; const share = metrics?.application_count ? count / metrics.application_count : 0; return <div className="evaluation-route" key={route}><div><span className={`route-dot ${routeClass(route)}`} /><b>{routeLabels[route]}</b><strong>{count}</strong></div><div className="evaluation-track"><span className={routeClass(route)} style={{ width: `${Math.max(count ? 6 : 0, share * 100)}%` }} /></div></div> })}</div><p className="evaluation-baseline-note">{metrics?.baseline_note}</p></section>
        <section className="surface evaluation-method"><div className="eyebrow">MODEL STATUS</div><div className="model-status-line"><span className="model-status-icon"><Activity size={18} /></span><strong>DEMO_RISK_SCORE_NOT_CALIBRATED</strong></div><p>No training data, validated repayment labels, holdout results or calibration evidence was supplied. The demo score is shown only to demonstrate calculation and routing behavior.</p><div className="model-status-row"><span>Model performance</span><b>Not measured</b></div><div className="model-status-row"><span>Reference parity</span><b>Unverified</b></div><div className="model-status-row"><span>Decision authority</span><b>Human officer</b></div></section></div>
      <section className="surface evaluation-log"><div className="section-head"><div><div className="eyebrow">EVALUATION LOG</div><h2>Case-by-case output</h2></div><span className="evaluation-log-count">{logs.length} records</span></div><div className="table-wrap"><table className="cases-table eval-table"><thead><tr><th>APPLICATION</th><th>STATUS</th><th>CONFIDENCE</th><th>SCENARIO SCORE</th><th>RECOMMENDED PATH</th></tr></thead><tbody>{logs.map(log => <tr key={log.application_id}><td><strong className="eval-id">{log.application_id}</strong></td><td><span className={`eval-status ${log.assessment_status === 'CALCULATED_DEMO_ONLY' ? 'eval-ready' : 'eval-blocked'}`}>{log.assessment_status === 'CALCULATED_DEMO_ONLY' ? 'Calculated' : 'Blocked'}</span></td><td>{log.confidence_index == null ? '—' : log.confidence_index.toFixed(3)}</td><td>{log.pd_demo == null ? '—' : percent(log.pd_demo, 3)}</td><td><RouteBadge route={log.recommended_route} /></td></tr>)}</tbody></table></div></section>
      <div className="evaluation-footer"><ShieldCheck size={15} /><span>{'Every route requires human confirmation. The export includes each application, calculations, provenance inputs and append-only review history.'}</span></div>
    </>}
  </>
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <label className="toggle-control"><span>{label}</span><button type="button" role="switch" aria-checked={checked} className={`toggle-switch ${checked ? 'toggle-on' : ''}`} onClick={() => onChange(!checked)}><span /></button></label>
}

function ScenarioStat({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="scenario-stat"><small>{label}</small><strong>{value}</strong><span>{note}</span></div>
}

function CaseContext({ active, onNavigate, current }: { active: CaseRecord; onNavigate: (page: PageName) => void; current: PageName }) {
  return <div className="case-context"><button className="context-back" onClick={() => onNavigate('Applications')}><ArrowRight size={13} /> All applications</button><span className="context-divider">/</span><strong>{active.application_id}</strong><span className="context-separator">·</span><span>{active.borrower_label}</span><span className="context-spacer" /><span className="context-tabs"><button className={current === 'Applications' ? 'context-tab-active' : ''} onClick={() => onNavigate('Applications')}>Case</button><button className={current === 'AI Assessment' ? 'context-tab-active' : ''} onClick={() => onNavigate('AI Assessment')}>Assessment</button><button className={current === 'Decision Routing' ? 'context-tab-active' : ''} onClick={() => onNavigate('Decision Routing')}>Routing</button><button className={current === 'Officer Review' ? 'context-tab-active' : ''} onClick={() => onNavigate('Officer Review')}>Review</button></span></div>
}

function RouteBadge({ route }: { route: RouteName }) {
  return <span className={`route-badge ${routeClass(route)}`}><span className="route-badge-dot" />{routeShort[route]}</span>
}

function prettyKey(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1).replaceAll('_', ' ')
}

function average(values: number[]) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0
}

function baseEvidenceQuality(item: CaseRecord) {
  const evidence = item.evidence
  return Math.min(evidence.reconciliation_fields_consistent / Math.max(evidence.reconciliation_fields_total, 1),
    evidence.verified_sources / Math.max(evidence.available_sources, 1))
}

export default App
