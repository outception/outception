/**
 * Briefing helpers: score tiers, grouping by category with the slot
 * allocator, freshness and the muted-words filter, shared by the briefing
 * card and the briefing page on both clients.
 */

import type { BriefingItem, BriefingPayload } from './card'
import { filterMuted } from './mutedWords'
import { allocate } from './slots'
import type { SignalState } from './state'

/** Scores are whole numbers from 0 to 10; a profile hides items under its
 * minimum, so what reaches a client is usually 6 and up. */
export type ScoreTier = 'top' | 'high' | 'mid' | 'low'

export const scoreTier = (score: number | null | undefined): ScoreTier => {
  if (score === null || score === undefined) return 'low'
  if (score >= 9) return 'top'
  if (score >= 7) return 'high'
  if (score >= 5) return 'mid'
  return 'low'
}

export interface BriefingGroup {
  category: string
  items: readonly BriefingItem[]
}

/** Items grouped by category in first-seen order, rank order kept inside. */
export const groupByCategory = (
  items: readonly BriefingItem[],
): BriefingGroup[] => {
  const groups = new Map<string, BriefingItem[]>()
  for (const item of items) {
    const list = groups.get(item.category)
    if (list) list.push(item)
    else groups.set(item.category, [item])
  }
  return [...groups.entries()].map(([category, list]) => ({
    category,
    items: list,
  }))
}

/** Each category's quota when only `capacity` rows fit, weighted by the
 * square root of its size so a big category cannot crowd out the rest. */
export const categoryQuotas = (
  groups: readonly BriefingGroup[],
  capacity: number,
): BriefingGroup[] => {
  const slots = allocate(
    groups.map((g) => g.items.length),
    capacity,
    'weighted',
  )
  return groups.map((group, i) => ({
    category: group.category,
    items: group.items.slice(0, slots[i] ?? 0),
  }))
}

export const isBriefingStale = (
  payload: Pick<BriefingPayload, 'builtAt' | 'staleAfterMs'>,
  now: number,
): boolean => now - payload.builtAt > payload.staleAfterMs

/** The state a client derives for a briefing it holds: stale past its
 * window, else what the envelope said. */
export const briefingState = (
  payload: Pick<BriefingPayload, 'builtAt' | 'staleAfterMs'>,
  envelopeState: SignalState,
  now: number,
): SignalState =>
  envelopeState === 'nominal' && isBriefingStale(payload, now)
    ? 'stale'
    : envelopeState

export const filterBriefing = (
  items: readonly BriefingItem[],
  mutedWords: readonly string[],
): readonly BriefingItem[] =>
  filterMuted(items, mutedWords, (item) => item.title)

/** The coverage line's inputs: how many publishers carry the story. */
export const coverage = (
  item: Pick<BriefingItem, 'publisherCount' | 'leadSourceName'>,
): { lead: string; others: number } => ({
  lead: item.leadSourceName,
  others: Math.max(0, item.publisherCount - 1),
})

/** The day a briefing was built for, as the history route keys it. */
export const briefingDayOf = (builtAt: number): string =>
  new Date(builtAt).toISOString().slice(0, 10)

export interface BriefingDayLike<T> {
  builtFor: string
  items: readonly T[]
}

/** The most recent history day strictly before `today`; null on the first
 * day. History arrives newest first but is not trusted to. */
export const dayBefore = <T>(
  days: readonly BriefingDayLike<T>[],
  today: string,
): BriefingDayLike<T> | null => {
  let best: BriefingDayLike<T> | null = null
  for (const day of days) {
    if (day.builtFor >= today) continue
    if (best === null || day.builtFor > best.builtFor) best = day
  }
  return best
}

export interface BriefingDiff<T> {
  /** Stories that were not in yesterday's briefing, in today's order. */
  fresh: T[]
  /** Stories carried over from yesterday, in today's order. */
  carried: T[]
  /** How many of yesterday's stories dropped out. */
  gone: number
}

/** "What changed since yesterday": today's items against the previous
 * day's, by story. Without a previous day every story is fresh. */
export const diffBriefings = <T extends { clusterId: string }>(
  today: readonly T[],
  yesterday: readonly { clusterId: string }[] | null,
): BriefingDiff<T> => {
  const before = new Set((yesterday ?? []).map((item) => item.clusterId))
  const fresh: T[] = []
  const carried: T[] = []
  for (const item of today) {
    if (before.has(item.clusterId)) carried.push(item)
    else fresh.push(item)
  }
  const now = new Set(today.map((item) => item.clusterId))
  let gone = 0
  for (const id of before) if (!now.has(id)) gone += 1
  return { fresh, carried, gone }
}
