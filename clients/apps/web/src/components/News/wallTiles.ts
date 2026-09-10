/** The tiles behind the mosaic view: a pure transform from the wall's source
 * payloads to the grid of headlines WallZoom paints.
 *
 * Its own module so it can be tested without mounting the view - importing
 * the component pulls in the whole design system, which needs a compile step
 * a unit test has no reason to run. */
import type { NewsSourceMeta } from '@/utils/news'

export type Tile = {
  key: string
  id: string
  /** The headline's own id, distinct from the source id above. */
  itemId: string
  title: string
  href: string
  source: string
  color: string
  logo: string | null
  /** When the headline was published, as the card's row kicker shows it. */
  pubDate: number | null
  /** When the source was last refreshed, as the card's header shows it. */
  updated: number | null
}

/** Source payloads, narrowed to what a tile needs. */
type BatchSource = {
  id: string
  updatedTime?: number
  items?: { id: string; title: string; url: string; pubDate?: number | null }[]
}

/**
 * Lay the wall out as a grid of rows, in the reader's own card order.
 *
 * The MIDDLE column is the wall. It is the column the zoom drives at the
 * reader, the one they actually read, so it follows the stack exactly: the
 * first row's middle tile is the top card - their country's news - the second
 * row's is the next card, and so on down. Each takes that source's latest
 * headline first.
 *
 * Everything either side of the middle takes turns across every source, so a
 * row still reads as a slice of the whole wall rather than nine headlines from
 * one outlet.
 */
export const buildTiles = (
  data: readonly BatchSource[],
  metas: readonly Pick<NewsSourceMeta, 'id' | 'name' | 'color' | 'logo'>[],
  perRow: number,
  rows: number,
  /** Which pass through the wall this is. Each pass starts every source at a
   * different headline, so a page that arrives is not the page just read. The
   * card ORDER down the middle is untouched by it - that is the reader's
   * stack, and it reads the same way every time. Wraps, so a source with few
   * headlines keeps contributing instead of dropping out after a pass or two. */
  cycle = 0,
): Tile[] => {
  const metaById = new Map(metas.map((m) => [m.id, m]))
  // Card order, which is the order the ids arrived in.
  const queues = data
    .map((s) => {
      const items = s.items ?? []
      const updated = s.updatedTime ?? null
      if (items.length === 0) return { id: s.id, updated, items: [] }
      // Rotate by a per-source amount as well as by the cycle, or every source
      // would advance in lockstep and the rows would look merely shifted.
      const step = (cycle * (1 + (s.id.length % 5))) % items.length
      return {
        id: s.id,
        updated,
        items: [...items.slice(step), ...items.slice(0, step)],
      }
    })
    .filter((q) => q.items.length > 0)
  if (queues.length === 0 || perRow < 1 || rows < 1) return []

  /** The first queue at or after `from` that still has a headline, wrapping
   * once. -1 when every source is dry. */
  const ready = (from: number) => {
    for (let i = 0; i < queues.length; i += 1) {
      const at = (from + i) % queues.length
      if (queues[at]!.items.length > 0) return at
    }
    return -1
  }

  const middle = Math.floor(perRow / 2)
  const out: Tile[] = []
  let turn = 0

  const take = (at: number): Tile => {
    const queue = queues[at]!
    const item = queue.items.shift()!
    const meta = metaById.get(queue.id)
    return {
      key: `${queue.id}-${item.id}`,
      id: queue.id,
      itemId: item.id,
      title: item.title,
      href: item.url,
      source: meta?.name ?? queue.id,
      color: meta?.color ?? '#888888',
      logo: meta?.logo ?? null,
      pubDate: item.pubDate ?? null,
      updated: queue.updated,
    }
  }

  for (let row = 0; row < rows; row += 1) {
    const slots: (Tile | null)[] = new Array(perRow).fill(null)

    // The middle of row N wants card N, and it is claimed FIRST: the columns
    // either side then know to hand the slot next to it to somebody else, so
    // the card the reader is being shown never sits beside itself.
    const centre = ready(row % queues.length)
    if (centre === -1) return out
    const centreId = queues[centre]!.id
    slots[middle] = take(centre)

    for (let column = 0; column < perRow; column += 1) {
      if (column === middle) continue
      let at = ready(turn)
      if (at === -1) {
        // Everything is dry mid-row. Keep what the row already has rather than
        // dropping a part-built row on the floor.
        for (const slot of slots) if (slot) out.push(slot)
        return out
      }
      if (queues[at]!.id === centreId) {
        const other = ready((at + 1) % queues.length)
        if (other !== -1 && queues[other]!.id !== centreId) at = other
      }
      turn = (at + 1) % queues.length
      slots[column] = take(at)
    }

    for (const slot of slots) if (slot) out.push(slot)
  }
  return out
}
