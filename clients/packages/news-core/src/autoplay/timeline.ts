/**
 * The auto-play timeline: a shot is a card and one of its stories; the hold
 * is a dwell scaled to reading time. Travel between shots is the renderer's
 * existing scroll or flip. No camera anywhere.
 */

export interface Shot {
  cardId: string
  itemId: string | null
  title: string
  dwellMs: number
  /** Offset from the start of the timeline. */
  startMs: number
}

export interface Timeline {
  shots: readonly Shot[]
  totalMs: number
}

export interface DwellOptions {
  wordsPerMinute?: number
  minMs?: number
  maxMs?: number
  /** Time to take the card in before reading starts. */
  baseMs?: number
}

export const dwellFor = (title: string, options: DwellOptions = {}): number => {
  const wpm = options.wordsPerMinute ?? 180
  const min = options.minMs ?? 4000
  const max = options.maxMs ?? 12000
  const base = options.baseMs ?? 2500
  const words = title.trim().split(/\s+/).filter(Boolean).length
  const reading = (words / wpm) * 60_000
  return Math.round(Math.min(max, Math.max(min, base + reading)))
}

export interface TimelineCard {
  id: string
  items: readonly { id: string; title: string }[]
}

export interface TimelineOptions extends DwellOptions {
  /** Stories per card; a card with none still gets one shot. */
  storiesPerCard?: number
}

export const buildTimeline = (
  cards: readonly TimelineCard[],
  options: TimelineOptions = {},
): Timeline => {
  const perCard = Math.max(1, options.storiesPerCard ?? 1)
  const shots: Shot[] = []
  let cursor = 0
  for (const card of cards) {
    const items = card.items.slice(0, perCard)
    const entries = items.length > 0 ? items : [{ id: null, title: '' }]
    for (const item of entries) {
      const dwellMs = dwellFor(item.title, options)
      shots.push({
        cardId: card.id,
        itemId: item.id,
        title: item.title,
        dwellMs,
        startMs: cursor,
      })
      cursor += dwellMs
    }
  }
  return { shots, totalMs: cursor }
}

/** The shot playing at `ms`, and how far into it. Past the end lands on the
 * last shot's end. */
export const seekTimeline = (
  timeline: Timeline,
  ms: number,
): { index: number; offsetMs: number } => {
  const last = timeline.shots.length - 1
  if (last < 0) return { index: -1, offsetMs: 0 }
  const t = Math.max(0, ms)
  for (let i = last; i >= 0; i -= 1) {
    const shot = timeline.shots[i]!
    if (t >= shot.startMs) {
      return { index: i, offsetMs: Math.min(t - shot.startMs, shot.dwellMs) }
    }
  }
  return { index: 0, offsetMs: 0 }
}
