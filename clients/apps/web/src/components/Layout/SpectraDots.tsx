'use client'

import { useEffect, useRef } from 'react'

// Uniform dot lattice (px). Spacing never changes — the "concentration" is done
// purely with per-dot opacity. This keeps the field clean: no rings, no spokes,
// no moiré.
const GRID = 22
const DOT_RADIUS = 1.1

// The focal "sun" (fraction of the viewport) where dots are at full strength,
// and the radius (fraction of the viewport's larger side) over which they fade
// out to nothing. Smaller radius = tighter pool of dots; larger = broader.
const FOCAL_X = 0.5
const FOCAL_Y = 0.45
const FADE_RADIUS = 0.62

function smoothstep(t: number): number {
  const x = Math.max(0, Math.min(1, t))
  return x * x * (3 - 2 * x)
}

/** A static dot field: a uniform grid whose dots fade out with distance from a
 * focal point, so the texture reads as concentrated near the "sun" and thinning
 * toward the edges — without ever changing the spacing (which is what produces
 * ugly ring/spoke artifacts). Drawn on a 2D canvas, repainted on resize. */
export default function SpectraDots({
  color,
  maxOpacity,
}: {
  color: string
  maxOpacity: number
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const draw = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const w = canvas.clientWidth
      const h = canvas.clientHeight
      canvas.width = Math.max(1, Math.floor(w * dpr))
      canvas.height = Math.max(1, Math.floor(h * dpr))
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, w, h)
      ctx.fillStyle = color

      const fx = w * FOCAL_X
      const fy = h * FOCAL_Y
      const fade = FADE_RADIUS * Math.max(w, h)

      for (let y = GRID / 2; y < h; y += GRID) {
        for (let x = GRID / 2; x < w; x += GRID) {
          const d = Math.hypot(x - fx, y - fy) / fade
          const a = smoothstep(1 - d)
          if (a <= 0.01) continue
          ctx.globalAlpha = maxOpacity * a
          ctx.beginPath()
          ctx.arc(x, y, DOT_RADIUS, 0, Math.PI * 2)
          ctx.fill()
        }
      }
      ctx.globalAlpha = 1
    }

    draw()
    window.addEventListener('resize', draw)
    return () => window.removeEventListener('resize', draw)
  }, [color, maxOpacity])

  return (
    <canvas ref={canvasRef} className="absolute inset-0 block h-full w-full" />
  )
}
