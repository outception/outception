/**
 * Same-story handling on a card: items that the server clustered share a
 * `clusterId`; the wall shows one row per story by default, keeping the
 * first (highest-ranked) and carrying the outlet count.
 */

export interface Clustered {
  id: string
  clusterId?: string | null
  publisherCount?: number | null
}

/** One row per story, in the original order; unclustered items stay. */
export const collapseStories = <T extends Clustered>(
  items: readonly T[],
): T[] => {
  const seen = new Set<string>()
  const out: T[] = []
  for (const item of items) {
    const cluster = item.clusterId ?? null
    if (cluster !== null) {
      if (seen.has(cluster)) continue
      seen.add(cluster)
    }
    out.push(item)
  }
  return out
}

/** Whether a row deserves the coverage mark: more than one outlet has it. */
export const hasCoverage = (item: Pick<Clustered, 'publisherCount'>): boolean =>
  (item.publisherCount ?? 0) > 1

/** Drop the headlines the reader already opened, when asked to. */
export const hideRead = <T extends { id: string }>(
  items: readonly T[],
  read: ReadonlySet<string> | ((id: string) => boolean),
): T[] => {
  const isRead =
    typeof read === 'function' ? read : (id: string) => read.has(id)
  return items.filter((item) => !isRead(item.id))
}

/** Cards within a column, the ones carrying the widest-reported stories
 * first. `coverageOf` is the best publisher count a card holds right now;
 * cards with nothing known keep their place among themselves. Stable. */
export const rankByCoverage = (
  ids: readonly string[],
  coverageOf: (id: string) => number | null | undefined,
): string[] =>
  ids
    .map((id, index) => ({ id, index, coverage: coverageOf(id) ?? 0 }))
    .sort((a, b) => b.coverage - a.coverage || a.index - b.index)
    .map((entry) => entry.id)

/** The rows a card shows, the stories more outlets carry first: a story
 * carried by many sits above one carried by few, the rest keep the
 * publisher's order. Stable, so a feed with no coverage is untouched. */
export const liftCoverage = <T extends Clustered>(items: readonly T[]): T[] =>
  items
    .map((item, index) => ({ item, index, count: item.publisherCount ?? 0 }))
    .sort((a, b) => {
      const ca = a.count > 1 ? a.count : 0
      const cb = b.count > 1 ? b.count : 0
      return cb - ca || a.index - b.index
    })
    .map((entry) => entry.item)
