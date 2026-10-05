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
