import { useLayoutEffect, useRef } from 'react'
import type { ReactNode, RefObject } from 'react'
import { X } from 'lucide-react'

export default function FocusDialog({
  open,
  label,
  section,
  onClose,
  children,
  contentRef,
}: {
  open: boolean
  label?: string
  section?: string | null
  onClose: () => void
  children?: ReactNode
  contentRef?: RefObject<HTMLDivElement | null>
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const closeButton = useRef<HTMLButtonElement>(null)

  useLayoutEffect(() => {
    const modal = dialog.current
    if (open && modal) {
      if (!modal.open) modal.showModal()
      closeButton.current?.focus({ preventScroll: true })
    } else if (!open && modal?.open) {
      modal.close()
    }
  }, [open, section])

  return (
    <dialog
      ref={dialog}
      className="overview-focus"
      data-section={section}
      aria-label={label}
      onClose={onClose}
    >
      <div className="overview-focus-toolbar">
        <button
          ref={closeButton}
          className="invoice-sidebar-toggle"
          type="button"
          aria-label="Close focused view"
          onClick={() => dialog.current?.close()}
        >
          <X size={21} aria-hidden="true" />
        </button>
      </div>
      {children}
      {contentRef && <div className="invoice-focused-content" ref={contentRef} />}
    </dialog>
  )
}
