import { useEffect, useRef } from 'react'
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { Compass, Files, House, LayoutDashboard, ShieldCheck } from 'lucide-react'
import Overview from './Overview'
import Queue from './Queue'
import Workspace from './Workspace'
import BatchUpload, { BatchUploadProvider } from './BatchUpload'
import LaunchPage from './LaunchPage'
import DemoDataLibrary from './DemoDataLibrary'

export default function App() {
  const location = useLocation()
  const isLaunch = location.pathname === '/'
  const heading = useRef<HTMLElement>(null)
  const previous = useRef(location.pathname)
  useEffect(() => {
    const titles: Record<string, string> = {
      '/': 'Invoice intake',
      '/overview': 'Operations overview',
      '/runs': 'Invoice Operations',
      '/runs/upload': 'Process invoices',
    }
    document.title = (titles[location.pathname] ?? 'Invoice decision') + ' | AP Compass'
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
      <header className={isLaunch ? 'app-header launch-header' : 'app-header'}>
        <div className="header-inner">
          <div className="header-start">
            <Link className="brand" to="/" aria-label="AP Compass home">
              <Compass size={30} aria-hidden="true" />
              {!isLaunch && <span>AP Compass</span>}
            </Link>
            {isLaunch && <DemoDataLibrary />}
          </div>
          <nav aria-label="Main navigation">
            <NavLink end to="/">
              <House size={17} aria-hidden="true" />
              Home
            </NavLink>
            <NavLink end to="/overview">
              <LayoutDashboard size={17} aria-hidden="true" />
              Overview
            </NavLink>
            <NavLink to="/runs">
              <Files size={17} aria-hidden="true" />
              Invoice Operations
            </NavLink>
          </nav>
        </div>
      </header>
      <main id="main" className="main-content" tabIndex={-1} ref={heading}>
        <BatchUploadProvider>
          <Routes>
            <Route path="/" element={<LaunchPage />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/runs" element={<Queue />} />
            <Route path="/runs/upload" element={<BatchUpload />} />
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
        </BatchUploadProvider>
      </main>
      <footer className="app-footer">
        <span>
          <ShieldCheck size={16} aria-hidden="true" />
          Analyst assistance. No payment or posting authority.
        </span>
        {isLaunch ? (
          <span className="launch-credit">
            <strong>Made by Arnav Vats</strong>
            <span>
              Built for the <a href="https://www.zamp.ai/">Zamp AI</a> Solutions Associate case
              study
            </span>
          </span>
        ) : (
          <span>AP Compass</span>
        )}
      </footer>
    </div>
  )
}
