import { useEffect, useState } from 'react'
import {
  ClipboardList,
  FileSearch,
  PanelLeftClose,
  PanelLeftOpen,
  ScanLine,
  Workflow,
} from 'lucide-react'
import { useLocation } from 'react-router-dom'

const sections = [
  { id: 'case-decision', label: 'Decision summary', Icon: ClipboardList },
  { id: 'evidence', label: 'Source evidence', Icon: FileSearch },
  { id: 'case-trace', label: 'Decision journey', Icon: Workflow },
  { id: 'case-details', label: 'Run details', Icon: ScanLine },
] as const

export default function WorkspaceNavigation({
  hasDecision,
  hasEvidence,
  onFocusSection,
}: {
  hasDecision: boolean
  hasEvidence: boolean
  onFocusSection: (section: { id: string; label: string }, trigger: HTMLElement) => void
}) {
  const { hash } = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [active, setActive] = useState<string>('case-decision')
  const available = sections.filter(({ id }) => id !== 'evidence' || hasEvidence)

  useEffect(() => {
    const target = hash === '#case-policy' ? 'case-decision' : hash.slice(1)
    const destination = target && document.getElementById(target)
    if (destination) destination.scrollIntoView?.()
  }, [hash, hasEvidence, hasDecision])

  useEffect(() => {
    const anchors = sections.flatMap(({ id }) => {
      const element = document.getElementById(id)
      return element ? [element] : []
    })
    let frame = 0
    const update = () => {
      const visible = anchors.map((element) => ({
        element,
        top: element.getBoundingClientRect().top,
      }))
      const atBottom =
        window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2
      const anchor =
        (atBottom
          ? anchors.at(-1)
          : visible.filter(({ top }) => top <= 110).sort((a, b) => b.top - a.top)[0]?.element) ??
        anchors[0]
      if (anchor) setActive(anchor.id)
    }
    const schedule = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(update)
    }
    schedule()
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
    }
  }, [hasEvidence, hasDecision])

  const highlighted = available.some(({ id }) => id === active) ? active : 'case-decision'
  return (
    <nav
      className="invoice-sidebar"
      data-collapsed={collapsed}
      aria-label="Invoice workspace sections"
    >
      <div className="invoice-sidebar-heading">
        <span className="invoice-nav-label">Workspace</span>
        <button
          className="invoice-sidebar-toggle"
          type="button"
          aria-controls="invoice-section-links"
          aria-expanded={!collapsed}
          aria-label={collapsed ? 'Expand workspace sidebar' : 'Collapse workspace sidebar'}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <PanelLeftOpen size={18} aria-hidden />
          ) : (
            <PanelLeftClose size={18} aria-hidden />
          )}
        </button>
      </div>
      <ul id="invoice-section-links">
        {available.map(({ id, label, Icon }) => (
          <li key={id}>
            <a
              href={'#' + id}
              aria-current={highlighted === id ? 'location' : undefined}
              aria-label={label}
              title={collapsed ? label : undefined}
              aria-haspopup="dialog"
              onClick={(event) => {
                if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
                event.preventDefault()
                setActive(id)
                onFocusSection({ id, label }, event.currentTarget)
              }}
            >
              <Icon size={18} aria-hidden />
              <span className="invoice-nav-label">{label}</span>
            </a>
          </li>
        ))}
      </ul>
      <label className="invoice-mobile-jump">
        <span>Jump to</span>
        <select
          value=""
          onChange={(event) => {
            const target = available.find(({ id }) => id === event.currentTarget.value)
            if (!target) return
            setActive(target.id)
            onFocusSection(target, event.currentTarget)
          }}
        >
          <option value="" disabled>
            Choose section
          </option>
          {available.map(({ id, label }) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
      </label>
    </nav>
  )
}
