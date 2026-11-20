import { useLayoutEffect, useRef, useState } from 'react'
import type { ReactNode, RefObject } from 'react'
import { createPortal } from 'react-dom'

export default function WorkspaceFocusSection({
  focused,
  target,
  children,
}: {
  focused: boolean
  target: RefObject<HTMLDivElement | null>
  children: ReactNode
}) {
  const slot = useRef<HTMLDivElement>(null)
  // The portal keeps a stable React tree as the section moves into the dialog and back.
  const [container] = useState(() => {
    const element = document.createElement('div')
    element.className = 'workspace-focus-section'
    return element
  })

  useLayoutEffect(() => {
    const inline = slot.current
    if (!inline) return
    inline.append(container)
    const modal = focused ? target.current : null
    if (modal) {
      inline.style.minHeight = inline.getBoundingClientRect().height + 'px'
      modal.append(container)
    }
    return () => {
      container.remove()
      inline.style.minHeight = ''
    }
  }, [container, focused, target])

  return <div ref={slot}>{createPortal(children, container)}</div>
}
