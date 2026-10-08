/**
 * The card model: the envelope every card kind shares, the payload per kind
 * and the id conventions for the strip, which is not a source. The types come
 * from the generated client so the wire shape is the single source of truth;
 * this module adds the helpers both renderers need.
 */

import type { schemas } from '@outception-com/client'

export type CardKind = schemas['CardKind']
export type Card = schemas['Card']
export type CardItem = schemas['CardItem']
export type CardPayload = Card['payload']
export type FeedPayload = schemas['FeedPayload']
export type TablePayload = schemas['TablePayload']
export type StripPayload = schemas['StripPayload']
export type HeatmapTile = schemas['HeatmapTile']
export type SourceMeta = schemas['SourceMeta']
export type NewsItem = schemas['NewsItem']
export type NewsTemplate = schemas['NewsTemplate']

export type FeedCard = Card & { kind: 'feed'; payload: FeedPayload }
export type TableCard = Card & { kind: 'table'; payload: TablePayload }
export type StripCard = Card & { kind: 'strip'; payload: StripPayload }

export const CARD_KINDS: readonly CardKind[] = ['feed', 'table', 'strip']

// The strip is not a source: its id is a fixed name that never collides
// with one.
export const WEATHER_STRIP_ID = 'weather'

/** The country card id for an ISO 3166 alpha-2 code. */
export const countryCardId = (country: string): string =>
  `gnews-${country.toLowerCase()}`

export const isCountryCardId = (cardId: string): boolean =>
  /^gnews-[a-z]{2}$/.test(cardId)

/** `SourceMeta.type` decides the kind: `heatmap` is a table; `hottest`,
 * `realtime` and unset are feeds. `game` has no rows and no kind. */
export const kindForType = (
  sourceType: string | null | undefined,
): CardKind => {
  if (sourceType === 'heatmap') return 'table'
  if (sourceType === 'game') throw new Error('game sources are not cards')
  return 'feed'
}

export const kindForId = (
  cardId: string,
  sourceType?: string | null,
): CardKind => {
  if (cardId === WEATHER_STRIP_ID) return 'strip'
  return kindForType(sourceType)
}

export const isFeedCard = (card: Card): card is FeedCard =>
  card.payload.kind === 'feed'
export const isTableCard = (card: Card): card is TableCard =>
  card.payload.kind === 'table'
export const isStripCard = (card: Card): card is StripCard =>
  card.payload.kind === 'strip'

/** The source family a card id belongs to (`bbc-world` is in `bbc`): the
 * icon and the colour are per family. */
export const sourceFamily = (id: string): string => id.split('-')[0] ?? id
