import { useId, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import {
  Activity,
  ChartPie,
  CircleAlert,
  Files,
  Landmark,
  ListChecks,
  PanelLeftClose,
  PanelLeftOpen,
  Table2,
  Wallet,
} from 'lucide-react'

import FocusDialog from './FocusDialog'

const sections = [
  { id: 'counts', label: 'Invoice counts', Icon: Files },
  { id: 'attention', label: 'Needs attention', Icon: CircleAlert },
  { id: 'distribution', label: 'Decision distribution', Icon: ChartPie },
  { id: 'financial', label: 'Financial overview', Icon: Wallet },
  { id: 'vendors', label: 'Vendors needing attention', Icon: Table2 },
  { id: 'capacity', label: 'Purchase order capacity', Icon: Landmark },
  { id: 'exceptions', label: 'Common exceptions', Icon: ListChecks },
  { id: 'flagged', label: 'Flagged invoice net', Icon: Wallet },
  { id: 'activity', label: 'Recent invoice activity', Icon: Activity },
] as const

type SectionId = (typeof sections)[number]['id']

export default function OverviewFocus({
  children,
  panels,
}: {
  children: ReactNode
  panels: Partial<Record<SectionId, ReactNode>>
}) {
  const [collapsed, setCollapsed] = useState(false)
  const [selected, setSelected] = useState<SectionId | null>(null)
  const content = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const id = useId()
  const active = sections.find((section) => section.id === selected)

  return (
    <div className="overview-layout" data-collapsed={collapsed}>
      <nav className="overview-sidebar" aria-label="Overview sections" data-collapsed={collapsed}>
        <div className="invoice-sidebar-heading">
          <span className="overview-sidebar-label">Overview</span>
          <button
            className="invoice-sidebar-toggle overview-sidebar-toggle"
            type="button"
            aria-expanded={!collapsed}
            aria-controls={id + '-sections'}
            aria-label={collapsed ? 'Expand Overview sidebar' : 'Collapse Overview sidebar'}
            onClick={() => setCollapsed((previous) => !previous)}
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>
        <ul id={id + '-sections'}>
          {sections
            .filter(({ id }) => panels[id] != null)
            .map(({ id, label, Icon }) => (
              <li key={id}>
                <button
                  className="overview-section-link"
                  type="button"
                  aria-label={label}
                  aria-haspopup="dialog"
                  aria-current={selected === id ? 'true' : undefined}
                  title={collapsed ? label : undefined}
                  onClick={(event) => {
                    trigger.current = event.currentTarget
                    content.current
                      ?.querySelector(`[data-overview-section="${id}"]`)
                      ?.scrollIntoView?.({
                        block: 'nearest',
                      })
                    setSelected(id)
                  }}
                >
                  <Icon size={18} aria-hidden="true" />
                  <span className="overview-sidebar-label">{label}</span>
                </button>
              </li>
            ))}
        </ul>
      </nav>
      <div className="overview-content" ref={content}>
        {children}
      </div>
      <FocusDialog
        open={selected !== null}
        section={selected}
        label={active?.label}
        onClose={() => {
          setSelected(null)
          trigger.current?.focus({ preventScroll: true })
        }}
      >
        {active && panels[active.id]}
      </FocusDialog>
    </div>
  )
}
