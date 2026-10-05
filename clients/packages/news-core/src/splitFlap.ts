/**
 * The split-flap planner: how a short label (a kicker, a counter, the
 * updated-ago line) flips from one text to the next, column by column, so a
 * web component and a native one animate the same plan. Never used on
 * headlines. The renderer honours reduced motion by showing `to` at once.
 */

export const FLAP_RING = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:-/'

export interface FlapColumn {
  from: string
  to: string
  /** Glyphs stepped through, `from` excluded, `to` included. */
  steps: number
  /** Milliseconds from the plan start. */
  start: number
  end: number
}

export interface FlapPlan {
  from: string
  to: string
  columns: readonly FlapColumn[]
  /** Milliseconds until every column rests. */
  duration: number
}

export interface FlapOptions {
  /** Time per glyph. */
  stepMs?: number
  /** Delay between one column starting and the next. */
  staggerMs?: number
  /** Longest run of glyphs a column flips through. */
  maxSteps?: number
}

const ringIndex = (glyph: string): number =>
  FLAP_RING.indexOf(glyph.toUpperCase())

const ringDistance = (from: string, to: string): number => {
  const a = ringIndex(from)
  const b = ringIndex(to)
  if (a === -1 || b === -1) return 1
  return (b - a + FLAP_RING.length) % FLAP_RING.length
}

/** Pad the shorter text with spaces so every column has a from and a to. */
export const planFlap = (
  from: string,
  to: string,
  options: FlapOptions = {},
): FlapPlan => {
  const stepMs = options.stepMs ?? 45
  const staggerMs = options.staggerMs ?? 30
  const maxSteps = options.maxSteps ?? 12
  const width = Math.max(from.length, to.length)
  const columns: FlapColumn[] = []
  let duration = 0
  for (let i = 0; i < width; i += 1) {
    const a = from[i] ?? ' '
    const b = to[i] ?? ' '
    const distance = a === b ? 0 : ringDistance(a, b)
    const steps = Math.min(distance, maxSteps)
    const start = i * staggerMs
    const end = start + steps * stepMs
    columns.push({ from: a, to: b, steps, start, end })
    if (steps > 0 && end > duration) duration = end
  }
  return { from, to, columns, duration }
}

const glyphAt = (column: FlapColumn, elapsed: number): string => {
  if (column.steps === 0 || elapsed >= column.end) return column.to
  if (elapsed < column.start) return column.from
  const stepMs = (column.end - column.start) / column.steps
  const done = Math.floor((elapsed - column.start) / stepMs)
  if (done >= column.steps) return column.to
  const a = ringIndex(column.from)
  const b = ringIndex(column.to)
  if (a === -1 || b === -1) return column.from
  // A run capped by maxSteps skips evenly through the ring so it still
  // lands on `to` at the last step.
  const distance = (b - a + FLAP_RING.length) % FLAP_RING.length
  const offset = Math.floor((done * distance) / column.steps)
  const glyph = FLAP_RING[(a + offset) % FLAP_RING.length] ?? column.to
  return column.to === column.to.toLowerCase() ? glyph.toLowerCase() : glyph
}

/** The text shown `elapsed` milliseconds into the plan. */
export const glyphsAt = (plan: FlapPlan, elapsed: number): string =>
  plan.columns.map((column) => glyphAt(column, elapsed)).join('')

export const isSettled = (plan: FlapPlan, elapsed: number): boolean =>
  elapsed >= plan.duration
