import { useEffect, useRef } from 'react'

// The Home-only horizon uses the ordered-dither effect shown in Magic UI’s Dither Field.
const bayer = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]
const dotSize = 4

export default function LaunchDitherField() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const host = canvas?.closest('main')
    if (!canvas || !host || typeof ResizeObserver === 'undefined') return
    const context = canvas.getContext('2d')
    if (!context) return

    const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
    let frame: ImageData | undefined
    let ink = getComputedStyle(canvas).color
    let pointer: { x: number; y: number } | null = null
    let time = 0
    let visible = true
    let timer: number | undefined

    const paint = () => {
      if (!frame) return
      const { width, height, data } = frame
      for (let y = 0; y < height; y++) {
        const depth = 1 - y / height
        const fade = 1 - depth
        for (let x = 0; x < width; x++) {
          const across = x / width
          const distance = Math.hypot((across - 0.63) * 1.6, depth + 0.12)
          const horizon = Math.exp(-5 * Math.max(distance - 0.2, 0))
          const band = 0.76 + 0.24 * Math.sin(depth * 25 + across * 5 - time)
          const glow = pointer
            ? 0.2 * Math.exp(-65 * ((across - pointer.x) ** 2 + (y / height - pointer.y) ** 2))
            : 0
          const light = Math.min(1, (horizon * band + glow) * fade)
          const threshold = (bayer[(y % 4) * 4 + (x % 4)] + 0.5) / 16
          data[(y * width + x) * 4 + 3] = light > threshold ? 30 + light * 105 : 0
        }
      }
      context.putImageData(frame, 0, 0)
      context.globalCompositeOperation = 'source-in'
      context.fillStyle = ink
      context.fillRect(0, 0, width, height)
    }

    const resize = () => {
      const { width, height } = canvas.getBoundingClientRect()
      if (!width || !height) return
      canvas.width = Math.ceil(width / dotSize)
      canvas.height = Math.ceil(height / dotSize)
      ink = getComputedStyle(canvas).color
      frame = context.createImageData(canvas.width, canvas.height)
      paint()
    }

    function sync() {
      window.clearInterval(timer)
      if (!visible || document.hidden || motion.matches) {
        pointer = null
        paint()
        return
      }
      timer = window.setInterval(() => {
        time += 0.027
        paint()
      }, 50)
    }

    const move = (event: PointerEvent) => {
      if (motion.matches || event.pointerType === 'touch') return
      const bounds = canvas.getBoundingClientRect()
      pointer =
        event.clientY >= bounds.top && event.clientY <= bounds.bottom
          ? {
              x: (event.clientX - bounds.left) / bounds.width,
              y: (event.clientY - bounds.top) / bounds.height,
            }
          : null
    }

    function stopPointer() {
      pointer = null
    }

    const sizeObserver = new ResizeObserver(resize)
    const viewObserver =
      typeof IntersectionObserver === 'undefined'
        ? null
        : new IntersectionObserver(([entry]) => {
            visible = entry.isIntersecting
            sync()
          })
    sizeObserver.observe(canvas)
    viewObserver?.observe(canvas)
    host.addEventListener('pointermove', move)
    host.addEventListener('pointerleave', stopPointer)
    document.addEventListener('visibilitychange', sync)
    motion.addEventListener('change', sync)
    resize()
    sync()

    return () => {
      window.clearInterval(timer)
      sizeObserver.disconnect()
      viewObserver?.disconnect()
      host.removeEventListener('pointermove', move)
      host.removeEventListener('pointerleave', stopPointer)
      document.removeEventListener('visibilitychange', sync)
      motion.removeEventListener('change', sync)
    }
  }, [])

  return <canvas ref={canvasRef} className="launch-dither-field" aria-hidden="true" />
}
