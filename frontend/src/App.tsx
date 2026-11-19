import { useEffect, useRef } from 'react'
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { Compass, Files, LayoutDashboard, ShieldCheck } from 'lucide-react'
import Overview from './Overview'
import Queue from './Queue'
import Workspace from './Workspace'

export default function App() {
  const location = useLocation()
  const heading = useRef<HTMLElement>(null)
  const previous = useRef(location.pathname)
  useEffect(() => {
    document.title = `${location.pathname === '/' ? 'Operations overview' : location.pathname === '/runs' ? 'Invoice Operations' : 'Invoice decision'} | AP Compass`
    if (previous.current !== location.pathname) {
      heading.current?.focus()
      window.scrollTo(0, 0)
      previous.current = location.pathname
    }
    if (location.hash === '#upload') {
      requestAnimationFrame(() => {
        const panel = document.getElementById('upload')
        panel?.scrollIntoView({ block: 'start' })
        panel?.querySelector<HTMLButtonElement>('button')?.focus()
      })
    }
  }, [location.pathname, location.hash])
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <header className="app-header">
        <div className="header-inner">
          <Link className="brand" to="/" aria-label="AP Compass overview">
            <Compass size={30} aria-hidden="true" />
            <span>
              AP Compass<small>Invoice Operations & Exception Resolution</small>
            </span>
          </Link>
          <nav aria-label="Main navigation">
            <NavLink end to="/">
              <LayoutDashboard size={17} aria-hidden="true" />
              Overview
            </NavLink>
            <NavLink to="/runs">
              <Files size={17} aria-hidden="true" />
              Invoice Operations
            </NavLink>
          </nav>
          <span className="environment-label">Synthetic demo data</span>
        </div>
      </header>
      <main id="main" className="main-content" tabIndex={-1} ref={heading}>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/runs" element={<Queue />} />
          <Route path="/runs/:runId" element={<Workspace />} />
          <Route
            path="*"
            element={
              <section className="empty-state">
                <h1>Page not found</h1>
                <p>Return to Invoice Operations to find your invoice.</p>
                <Link className="button secondary" to="/runs">
                  Open invoice queue
                </Link>
              </section>
            }
          />
        </Routes>
      </main>
      <footer className="app-footer">
        <span>
          <ShieldCheck size={16} aria-hidden="true" />
          Analyst assistance. No payment or posting authority.
        </span>
        <span>AP Compass</span>
      </footer>
    </div>
  )
}
