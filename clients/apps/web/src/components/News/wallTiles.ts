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
}

/** Source payloads, narrowed to what a tile needs. */
type BatchSource = {
  id: string
  items?: { id: string; title: string; url: string }[]
}

/**
 * Flatten many sources into tiles, taking ONE headline from each source in
 * turn rather than draining a source before moving on.
 *
 * Round-robin matters here: a row is nine tiles, so draining would make every
 * row nine headlines from one outlet. Taking turns makes each row a slice of
 * the whole wall, which is the thing the view is meant to show.
 */
export const buildTiles = (
  data: readonly BatchSource[],
  metas: readonly Pick<NewsSourceMeta, 'id' | 'name' | 'color' | 'logo'>[],
  limit: number,
  /** Which pass through the wall this is. Each pass starts every source at a
   * different headline, so reaching the end hands back a mosaic that is not
   * the one just seen - the centre, which the zoom puts in your face, is never
   * twice the same. Wraps, so a source with few headlines keeps contributing
   * instead of dropping out after a pass or two. */
  cycle = 0,
): Tile[] => {
  const metaById = new Map(metas.map((m) => [m.id, m]))
  const queues = data
    .map((s) => {
      const items = s.items ?? []
      if (items.length === 0) return { id: s.id, items: [] }
      // Rotate by a per-source amount as well as by the cycle, or every source
      // would advance in lockstep and the rows would look merely shifted.
      const step = (cycle * (1 + (s.id.length % 5))) % items.length
      return {
        id: s.id,
        items: [...items.slice(step), ...items.slice(0, step)],
      }
    })
    .filter((q) => q.items.length > 0)
  const out: Tile[] = []
  while (out.length < limit && queues.length > 0) {
    for (let q = queues.length - 1; q >= 0; q -= 1) {
      const queue = queues[q]!
      const item = queue.items.shift()
      if (!item) {
        queues.splice(q, 1)
        continue
      }
      const meta = metaById.get(queue.id)
      out.push({
        key: `${queue.id}-${item.id}`,
        id: queue.id,
        itemId: item.id,
        title: item.title,
        href: item.url,
        source: meta?.name ?? queue.id,
        color: meta?.color ?? '#888888',
        logo: meta?.logo ?? null,
      })
      if (out.length >= limit) break
    }
  }
  return out
}
