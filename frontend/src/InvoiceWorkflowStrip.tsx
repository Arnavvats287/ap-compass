import { useEffect, useRef, useState } from 'react'
import { Check, CircleAlert, ClipboardList, Pause, Play, X } from 'lucide-react'

const outcomes = [
  { name: 'ready', Icon: Check },
  { name: 'review', Icon: CircleAlert },
  { name: 'blocked', Icon: X },
] as const

export default function InvoiceWorkflowStrip() {
  const strip = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(() => typeof IntersectionObserver === 'undefined')
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    const element = strip.current
    if (!element || typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting),
      { threshold: 0.35 },
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return (
    <div className="ops-workflow-strip" ref={strip} data-running={visible && !paused}>
      <div className="ops-workflow-art" aria-hidden="true">
        <span className="ops-workflow-track" />
        <span className="ops-workflow-paper ops-workflow-po">
          <ClipboardList size={23} strokeWidth={1.5} />
        </span>
        <div className="ops-workflow-lane">
          {outcomes.map(({ name, Icon }) => (
            <div key={name} className={'ops-workflow-courier ' + name}>
              <span className="ops-workflow-paper ops-workflow-invoice" />
              <span className="ops-workflow-result">
                <Icon size={14} strokeWidth={2.4} />
              </span>
            </div>
          ))}
        </div>
      </div>
      <button
        className="ops-workflow-toggle"
        type="button"
        aria-label={paused ? 'Play workflow illustration' : 'Pause workflow illustration'}
        title={paused ? 'Play illustration' : 'Pause illustration'}
        onClick={() => setPaused((current) => !current)}
      >
        {paused ? <Play size={14} aria-hidden="true" /> : <Pause size={14} aria-hidden="true" />}
      </button>
    </div>
  )
}
