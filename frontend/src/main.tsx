import React from 'react'
import ReactDOM from 'react-dom/client'
import { useEffect, useState } from 'react'
import { ArrowUpRight, Check, Compass, FilePlus2, Files, LayoutDashboard, ShieldCheck } from 'lucide-react'
import './styles.css'

type Health = {status: string; database: string}
function App() {
  const [view, setView] = useState<'operations' | 'foundation'>('operations')
  const [health, setHealth] = useState<'checking' | 'online' | 'unavailable'>('checking')
  useEffect(() => {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 5000)
    fetch('/api/health', {signal:controller.signal})
      .then(async r => { if (!r.ok) throw new Error('Health unavailable'); return r.json() as Promise<Health> })
      .then(h => setHealth(h.status === 'ok' && h.database === 'ok' ? 'online' : 'unavailable'))
      .catch(() => { setHealth('unavailable') })
      .finally(() => clearTimeout(timeout))
    return () => {clearTimeout(timeout); controller.abort()}
  }, [])
  return <div className="app">
    <aside className="sidebar">
      <a className="brand" href="#operations" onClick={() => setView('operations')}><span className="brand-mark"><Compass size={25}/></span><span>AP Compass<small>INVOICE OPERATIONS</small></span></a>
      <div className="workspace-label">WORKSPACE</div>
      <nav aria-label="Main navigation">
        <button className={view === 'operations' ? 'nav active' : 'nav'} onClick={() => setView('operations')}><Files size={18}/>Invoice Operations</button>
        <button className={view === 'foundation' ? 'nav active' : 'nav'} onClick={() => setView('foundation')}><LayoutDashboard size={18}/>Foundation status</button>
      </nav>
      <div className="sidebar-foot"><ShieldCheck size={19}/><p>Analyst assistance<small>No payment or posting authority</small></p></div>
    </aside>
    <div className="main-wrap">
      <header className="topbar"><span>Workspace <span className="slash">/</span> {view === 'operations' ? 'Invoice Operations' : 'Foundation status'}</span><span className="phase-badge">Phase 01 · Foundation</span></header>
      <main>
        <div className="heading"><div><div className="eyebrow">ACCOUNTS PAYABLE WORKSTATION</div><h1>{view === 'operations' ? 'Invoice Operations' : 'Foundation status'}</h1><p className="subtitle">{view === 'operations' ? 'A clear path from invoice to the next right action.' : 'The starting point for a verifiable invoice workflow.'}</p></div><span className="environment">Synthetic demo environment</span></div>
        {view === 'operations' ? <>
          <section className="notice"><ShieldCheck size={20}/><p><strong>The foundation is in place.</strong> Processing will become available in a later phase. No invoices have been analyzed.</p></section>
          <section className="empty-card" aria-labelledby="empty-title">
            <div className="document-icon"><FilePlus2 size={32} strokeWidth={1.5}/></div>
            <div className="eyebrow">YOUR INVOICE WORKSPACE</div><h2 id="empty-title">Start with an invoice. End with clarity.</h2>
            <p>Bring invoice facts, purchase orders, and exceptions together<br className="desktop-break"/> in one place, with evidence behind every decision.</p>
            <button className="process-button" disabled aria-describedby="processing-note"><FilePlus2 size={18}/>Process invoice <ArrowUpRight size={17}/></button>
            <span id="processing-note" className="muted">Not available in Phase 1</span>
            <div className="empty-divider"/><div className="workflow-preview"><span>Planned workflow</span><p>Read invoice <span>→</span> Check purchase order <span>→</span> Resolve exceptions</p></div>
          </section>
          <div className="bottom-note"><ShieldCheck size={16}/><span>Decisions will support AP review. Final approval stays with your team.</span></div>
        </> : <section className="status-card"><h2>Foundation connections</h2><div className="status-row"><span>Backend & database</span><strong className={health === 'online' ? 'online' : ''}>{health === 'online' ? <><Check size={16}/> Connected</> : health === 'checking' ? 'Checking…' : 'Unavailable'}</strong></div><p>The connection status comes from the health API. Invoice extraction, financial checks, and analysis history are not implemented in this phase.</p><div className="synthetic-label">All supplied vendors, purchase orders, and invoice fixtures are synthetic.</div></section>}
      </main><footer>AP Compass <span>Invoice Operations & Exception Resolution</span></footer>
    </div>
  </div>
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
