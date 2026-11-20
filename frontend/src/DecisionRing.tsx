import { useEffect, useState } from 'react'

type Segment = readonly [key: 'ready' | 'review' | 'blocked', label: string, count: number]

const duration = 780
// Increase the sweep of a single arc while keeping the segment proportions.
function point(position: number, curl: number) {
  if (curl === 0) return 18 + 172 * position + ' 104'
  const sweep = Math.PI * curl
  const length = 172 * (1 - curl) + 150 * Math.PI * curl
  const radius = length / (2 * sweep)
  const angle = (2 * position - 1) * sweep
  return [104 + radius * Math.sin(angle), 104 - 75 * curl + radius * (1 - Math.cos(angle))].join(
    ' ',
  )
}

export default function DecisionRing({ segments }: { segments: readonly Segment[] }) {
  const [curl, setCurl] = useState(0)
  useEffect(() => {
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (motion.matches) return
    let frame = 0
    let start: number | undefined
    function draw(now: number) {
      start ??= now
      const progress = Math.min((now - start) / duration, 1)
      setCurl(progress * progress * (3 - 2 * progress))
      if (progress < 1) frame = requestAnimationFrame(draw)
    }
    frame = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(frame)
  }, [])

  const total = segments.reduce((sum, segment) => sum + segment[2], 0)
  const positions = segments.reduce<{ end: number; paths: React.ReactNode[] }>(
    ({ end, paths }, [key, , count]) => {
      if (!count) return { end, paths }
      const fraction = count / total
      const steps = Math.max(1, Math.ceil(fraction * 96))
      const points = Array.from(
        { length: steps + 1 },
        (_, index) => end + (fraction * index) / steps,
      )
      const path = (progress: number) =>
        points
          .map((position, index) => (index === 0 ? 'M' : 'L') + point(position, progress))
          .join(' ')
      return {
        end: end + fraction,
        paths: [
          ...paths,
          <g key={key} className={key}>
            <path className="decision-ring-motion" d={path(curl)} />
            <path className="decision-ring-static" d={path(1)} />
          </g>,
        ],
      }
    },
    { end: 0, paths: [] },
  )

  return (
    <svg className="decision-ring" viewBox="0 0 208 208" aria-hidden="true">
      {positions.paths}
    </svg>
  )
}
