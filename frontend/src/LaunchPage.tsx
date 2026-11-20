import { useEffect, useRef, useState } from 'react'
import { ClipboardCheck, ScanLine, Waypoints } from 'lucide-react'
import BatchUpload from './BatchUpload'

const steps = [
  {
    title: 'Read the source',
    description: 'Extract invoice fields and show which values the PDF can independently support.',
    Icon: ScanLine,
  },
  {
    title: 'Check the purchase order',
    description: 'Match approved records and check prices, remaining quantities and prior billing.',
    Icon: ClipboardCheck,
  },
  {
    title: 'Work the exceptions',
    description:
      'See why an invoice is Ready, needs Review or is Blocked, and who should act next.',
    Icon: Waypoints,
  },
] as const

export default function LaunchPage() {
  const story = useRef<HTMLOListElement>(null)
  const [entered, setEntered] = useState(false)
  useEffect(() => {
    if (!story.current || typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return
        setEntered(true)
        observer.disconnect()
      },
      { threshold: 0.2 },
    )
    observer.observe(story.current)
    return () => observer.disconnect()
  }, [])
  return (
    <div className="launch-page">
      <BatchUpload launch />
      <section className="launch-story" aria-labelledby="launch-story-title">
        <h2 id="launch-story-title">From PDF to decision</h2>
        <ol ref={story} data-entered={entered} className="launch-steps">
          {steps.map(({ title, description, Icon }) => (
            <li key={title}>
              <div className="launch-step-icon">
                <Icon size={25} aria-hidden="true" />
              </div>
              <h3>{title}</h3>
              <p>{description}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}
