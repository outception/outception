'use client'

import { useEffect, useRef } from 'react'

// Uniform square grid (px). Spacing never changes — the "concentration" is done
// purely with a radial alpha mask, so the lines read as strong near the anchor
// and fade out toward the edges (no hard edges, no moiré).
const CELL = 60
const LINE_WIDTH = 1

// The anchor: horizontal centre of the viewport, a fixed distance down from the
// top that matches the logo (the red totem). The grid is PHASED so a cell is
// centred exactly on this point — i.e. the logo sits in the middle of a square —
// and the radial fade glows out from the same point.
const ANCHOR_X = 0.5
const ANCHOR_TOP_PX = 80
const FADE_RADIUS = 0.9

/** A static line grid (dub-style squares) phased so a cell is centred on the
 * logo, then masked with a radial gradient (destination-in) so it reads as a
 * glow radiating from the logo and fading toward the edges. Drawn on a 2D
 * canvas, repainted on resize. */
export default function SpectraGrid({
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

      // Anchor = logo position. Phase the lines so the anchor is a cell CENTRE:
      // lines fall at anchor ± CELL/2 ± k·CELL, so the logo lands dead-centre of
      // a square.
      const ax = w * ANCHOR_X
      const ay = ANCHOR_TOP_PX
      const startX = (((ax - CELL / 2) % CELL) + CELL) % CELL
      const startY = (((ay - CELL / 2) % CELL) + CELL) % CELL

      // 1) Paint the full grid at peak strength.
      ctx.globalCompositeOperation = 'source-over'
      ctx.globalAlpha = maxOpacity
      ctx.strokeStyle = color
      ctx.lineWidth = LINE_WIDTH
      ctx.beginPath()
      // +0.5 keeps 1px lines crisp instead of blurring across two device pixels.
      for (let x = startX; x < w; x += CELL) {
        ctx.moveTo(Math.round(x) + 0.5, 0)
        ctx.lineTo(Math.round(x) + 0.5, h)
      }
      for (let y = startY; y < h; y += CELL) {
        ctx.moveTo(0, Math.round(y) + 0.5)
        ctx.lineTo(w, Math.round(y) + 0.5)
      }
      ctx.stroke()

      // 2) Mask it with a radial fade centred on the anchor so the grid glows
      //    from the logo and clears toward the edges.
      const fade = FADE_RADIUS * Math.min(w, h)
      const mask = ctx.createRadialGradient(ax, ay, 0, ax, ay, fade)
      mask.addColorStop(0, 'rgba(0,0,0,1)')
      mask.addColorStop(0.5, 'rgba(0,0,0,0.6)')
      mask.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.globalAlpha = 1
      ctx.globalCompositeOperation = 'destination-in'
      ctx.fillStyle = mask
      ctx.fillRect(0, 0, w, h)

      ctx.globalCompositeOperation = 'source-over'
    }

    draw()
    window.addEventListener('resize', draw)
    return () => window.removeEventListener('resize', draw)
  }, [color, maxOpacity])

  return (
    <canvas ref={canvasRef} className="absolute inset-0 block h-full w-full" />
  )
}
