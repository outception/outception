/**
 * The slot allocator and the dwell rule: how a card list with more headlines
 * than fit shares its rows between groups (the sources inside a merged card,
 * the categories of a briefing), and how an incumbent keeps its row for a
 * while so the list does not thrash on every refresh. Deterministic, so two
 * devices show the same order for the same data.
 */

export type SlotStrategy = 'elastic' | 'weighted'

const zeros = (n: number): number[] => Array.from({ length: n }, () => 0)

// Hand one slot at a time, in order, to every group that still wants one.
const borrow = (
  out: number[],
  demand: readonly number[],
  remaining: number,
): number => {
  let left = remaining
  let progressed = true
  while (left > 0 && progressed) {
    progressed = false
    for (let i = 0; i < out.length && left > 0; i += 1) {
      const want = demand[i] ?? 0
      const have = out[i] ?? 0
      if (have < want) {
        out[i] = have + 1
        left -= 1
        progressed = true
      }
    }
  }
  return left
}

/**
 * Slots per group. `elastic` gives every group an equal share and lends the
 * unused part to groups that want more; `weighted` sizes shares by the
 * square root of the group's count times its weight, with largest-remainder
 * rounding and at least one slot for every group that has anything.
 */
export const allocate = (
  demand: readonly number[],
  capacity: number,
  strategy: SlotStrategy = 'elastic',
  weights?: readonly number[],
): number[] => {
  const n = demand.length
  if (n === 0 || capacity <= 0) return zeros(n)
  const cap = Math.floor(capacity)
  const out = zeros(n)
  if (strategy === 'elastic') {
    const share = Math.floor(cap / n)
    let used = 0
    for (let i = 0; i < n; i += 1) {
      out[i] = Math.min(Math.max(0, demand[i] ?? 0), share)
      used += out[i] ?? 0
    }
    borrow(out, demand, cap - used)
    return out
  }
  const raw = demand.map((d, i) =>
    d > 0 ? Math.sqrt(d) * Math.max(0, weights?.[i] ?? 1) : 0,
  )
  const total = raw.reduce((s, v) => s + v, 0)
  if (total <= 0) return out
  const exact = raw.map((v) => (v / total) * cap)
  let used = 0
  for (let i = 0; i < n; i += 1) {
    out[i] = Math.min(Math.floor(exact[i] ?? 0), demand[i] ?? 0)
    used += out[i] ?? 0
  }
  // At least one slot per group with anything to show, while slots last.
  for (let i = 0; i < n && used < cap; i += 1) {
    if ((demand[i] ?? 0) > 0 && (out[i] ?? 0) === 0) {
      out[i] = 1
      used += 1
    }
  }
  // Largest remainder for what is left, then plain borrowing.
  const order = exact
    .map((v, i) => ({ i, frac: v - Math.floor(v) }))
    .sort((a, b) => b.frac - a.frac || a.i - b.i)
  for (const { i } of order) {
    if (used >= cap) break
    if ((out[i] ?? 0) < (demand[i] ?? 0)) {
      out[i] = (out[i] ?? 0) + 1
      used += 1
    }
  }
  borrow(out, demand, cap - used)
  return out
}

export interface SlotCandidate {
  id: string
  /** Pinned rows always lead: the expanded story, the lead of a shared link. */
  pinned?: boolean
  /** Held its row on the previous pass and is inside its dwell. */
  incumbent?: boolean
  score?: number | null
  /** Epoch milliseconds. */
  publishedAt?: number | null
}

/** FNV-1a, 32 bit: small, stable across devices and runtimes. */
export const stableHash = (text: string): number => {
  let hash = 0x811c9dc5
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i)
    hash = Math.imul(hash, 0x01000193) >>> 0
  }
  return hash >>> 0
}

/** Pinned first, then incumbent, then score, then recency, then a stable hash. */
export const compareCandidates = (
  a: SlotCandidate,
  b: SlotCandidate,
): number => {
  if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1
  if (!!a.incumbent !== !!b.incumbent) return a.incumbent ? -1 : 1
  const sa = a.score ?? null
  const sb = b.score ?? null
  if (sa !== sb) {
    if (sa === null) return 1
    if (sb === null) return -1
    if (sa !== sb) return sb - sa
  }
  const ta = a.publishedAt ?? 0
  const tb = b.publishedAt ?? 0
  if (ta !== tb) return tb - ta
  return stableHash(a.id) - stableHash(b.id) || (a.id < b.id ? -1 : 1)
}

/** An incumbent keeps its row for this long after it was placed. */
export const DWELL_MS = 5 * 60_000

export interface DwellInput {
  candidates: readonly SlotCandidate[]
  /** Ids shown on the previous pass, in order. */
  previous: readonly string[]
  /** When each shown id was first placed, epoch milliseconds. */
  placedAt: Readonly<Record<string, number>>
  now: number
  dwellMs?: number
}

export interface DwellResult {
  order: SlotCandidate[]
  placedAt: Record<string, number>
}

/** Rank with the dwell rule: ids placed on the previous pass keep incumbent
 * status while inside their dwell; `placedAt` is carried to the next pass. */
export const rankWithDwell = (input: DwellInput): DwellResult => {
  const dwell = input.dwellMs ?? DWELL_MS
  const shown = new Set(input.previous)
  const ranked = input.candidates
    .map((c) => {
      const placed = input.placedAt[c.id]
      const incumbent =
        shown.has(c.id) && placed !== undefined && input.now - placed < dwell
      return { ...c, incumbent: c.incumbent || incumbent }
    })
    .sort(compareCandidates)
  const placedAt: Record<string, number> = {}
  for (const c of ranked) {
    placedAt[c.id] = input.placedAt[c.id] ?? input.now
  }
  return { order: ranked, placedAt }
}
