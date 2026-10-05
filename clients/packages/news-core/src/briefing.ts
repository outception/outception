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
