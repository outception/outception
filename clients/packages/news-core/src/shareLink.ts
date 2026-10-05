/**
 * Share link v1: the lead card in the query string (so the server-rendered
 * unfurl keeps working) and the rest in the hash, which never reaches the
 * server.
 *
 *   /?card=<lead>#v=1&c=<id,id>&s=<story>&e=<edition>&l=<look>&k=<topic>&at=<epochSeconds>
 *
 * Unknown tokens are dropped; an invalid card list is rejected whole, never
 * half applied; `at` is added only to the copied link. Restore order: theme,
 * then cards, then the story only if the cards applied. A user action during
 * restore wins its lane.
 */

import {
  LEAD_CARD_QUERY,
  SHARE_LINK_VERSION,
  SHARE_TOKENS,
} from './shareTokens'

export const MAX_SHARED_CARDS = 120
const CARD_ID = /^[a-z0-9][a-z0-9:_.-]{0,99}$/i
const SLUG = /^[a-z][a-z0-9-]{0,31}$/i
const STORY = /^[a-z0-9][a-z0-9_.:-]{0,127}$/i

export interface ShareLinkState {
  version: number | null
  lead: string | null
  cards: readonly string[]
  story: string | null
  edition: string | null
  look: string | null
  topic: string | null
  /** Epoch seconds the link was copied, when it carried them. */
  at: number | null
  /** Token groups that were present but invalid and therefore dropped. */
  rejected: readonly string[]
}

export const EMPTY_SHARE_STATE: ShareLinkState = Object.freeze({
  version: null,
  lead: null,
  cards: Object.freeze([]) as readonly string[],
  story: null,
  edition: null,
  look: null,
  topic: null,
  at: null,
  rejected: Object.freeze([]) as readonly string[],
})

const decode = (value: string): string | null => {
  try {
    return decodeURIComponent(value.replace(/\+/g, ' '))
  } catch {
    return null
  }
}

/** `a=1&b=2` into a map; first occurrence wins; a leading `?` or `#` is
 * ignored. Pure so it runs without the DOM's URL types. */
export const parseParams = (
  text: string | null | undefined,
): ReadonlyMap<string, string> => {
  const out = new Map<string, string>()
  if (!text) return out
  const body =
    text.startsWith('?') || text.startsWith('#') ? text.slice(1) : text
  for (const pair of body.split('&')) {
    if (!pair) continue
    const eq = pair.indexOf('=')
    const key = decode(eq === -1 ? pair : pair.slice(0, eq))
    const value = decode(eq === -1 ? '' : pair.slice(eq + 1))
    if (key === null || value === null || key === '' || out.has(key)) continue
    out.set(key, value)
  }
  return out
}

const validCard = (id: string): boolean => CARD_ID.test(id)

export const parseShareLink = (input: {
  search?: string | null
  hash?: string | null
}): ShareLinkState => {
  const query = parseParams(input.search)
  const rejected: string[] = []
  const leadRaw = query.get(LEAD_CARD_QUERY) ?? null
  let lead: string | null = null
  if (leadRaw !== null) {
    if (validCard(leadRaw)) lead = leadRaw
    else rejected.push('lead')
  }
  const hash = parseParams(input.hash)
  const versionRaw = hash.get(SHARE_TOKENS.version)
  const version =
    versionRaw !== undefined && /^\d+$/.test(versionRaw)
      ? Number(versionRaw)
      : null
  // A hash from a later version may carry meanings this parser does not
  // know; the lead card still applies, the rest is ignored whole.
  if (version === null || version > SHARE_LINK_VERSION) {
    if (hash.size > 0) rejected.push('hash')
    return { ...EMPTY_SHARE_STATE, lead, rejected }
  }
  let cards: readonly string[] = []
  const cardsRaw = hash.get(SHARE_TOKENS.cards)
  if (cardsRaw !== undefined) {
    const list = cardsRaw.split(',').filter((id) => id !== '')
    if (
      list.length > 0 &&
      list.length <= MAX_SHARED_CARDS &&
      list.every(validCard)
    )
      cards = [...new Set(list)]
    else rejected.push('cards')
  }
  const slug = (token: string, group: string): string | null => {
    const raw = hash.get(token)
    if (raw === undefined) return null
    if (SLUG.test(raw)) return raw
    rejected.push(group)
    return null
  }
  const storyRaw = hash.get(SHARE_TOKENS.story)
  let story: string | null = null
  if (storyRaw !== undefined) {
    if (STORY.test(storyRaw)) story = storyRaw
    else rejected.push('story')
  }
  const atRaw = hash.get(SHARE_TOKENS.at)
  let at: number | null = null
  if (atRaw !== undefined) {
    if (/^\d{1,12}$/.test(atRaw)) at = Number(atRaw)
    else rejected.push('at')
  }
  return {
    version,
    lead,
    cards,
    story,
    edition: slug(SHARE_TOKENS.edition, 'edition'),
    look: slug(SHARE_TOKENS.look, 'look'),
    topic: slug(SHARE_TOKENS.topic, 'topic'),
    at,
    rejected,
  }
}

export interface ShareLinkInput {
  /** The wall's path, `/` by default. */
  path?: string
  lead?: string | null
  cards?: readonly string[]
  story?: string | null
  edition?: string | null
  look?: string | null
  topic?: string | null
  /** Epoch seconds: only for the copied link, never the live address. */
  at?: number | null
}

/** The link's path, query and hash. Prefix the origin to copy it. */
export const buildShareLink = (input: ShareLinkInput): string => {
  const path = input.path ?? '/'
  const query = input.lead
    ? `?${LEAD_CARD_QUERY}=${encodeURIComponent(input.lead)}`
    : ''
  const parts: string[] = [`${SHARE_TOKENS.version}=${SHARE_LINK_VERSION}`]
  const cards = (input.cards ?? []).filter(validCard)
  if (cards.length > 0)
    parts.push(
      `${SHARE_TOKENS.cards}=${cards.map(encodeURIComponent).join(',')}`,
    )
  if (input.story)
    parts.push(`${SHARE_TOKENS.story}=${encodeURIComponent(input.story)}`)
  if (input.edition)
    parts.push(`${SHARE_TOKENS.edition}=${encodeURIComponent(input.edition)}`)
  if (input.look)
    parts.push(`${SHARE_TOKENS.look}=${encodeURIComponent(input.look)}`)
  if (input.topic)
    parts.push(`${SHARE_TOKENS.topic}=${encodeURIComponent(input.topic)}`)
  if (input.at !== null && input.at !== undefined)
    parts.push(`${SHARE_TOKENS.at}=${Math.floor(input.at)}`)
  // A bare version carries nothing worth a hash.
  const hash = parts.length > 1 ? `#${parts.join('&')}` : ''
  return `${path}${query}${hash}`
}

/** Whether the address carries anything a share would restore. */
export const isShareLink = (state: ShareLinkState): boolean =>
  state.lead !== null ||
  state.cards.length > 0 ||
  state.story !== null ||
  state.edition !== null ||
  state.look !== null

export type RestoreLane = 'theme' | 'cards' | 'story'
export const RESTORE_ORDER: readonly RestoreLane[] = ['theme', 'cards', 'story']
export type RestoreOutcome = 'applied' | 'skipped' | 'empty' | 'blocked'

export interface RestoreHandlers {
  /** Apply the edition and look. */
  theme(state: ShareLinkState): boolean | void
  /** Apply the card set and the lead; return false when nothing applied. */
  cards(state: ShareLinkState): boolean | void
  /** Open the story; runs only once the cards applied. */
  story(state: ShareLinkState): boolean | void
}

/** Run the restore in order. Lanes in `touched` (the reader acted before
 * the restore got there) are skipped; the story is blocked when the cards
 * did not apply. The caller pauses address writes around this. */
export const restoreFromLink = (
  state: ShareLinkState,
  handlers: RestoreHandlers,
  touched: ReadonlySet<RestoreLane> = new Set(),
): Record<RestoreLane, RestoreOutcome> => {
  const result: Record<RestoreLane, RestoreOutcome> = {
    theme: 'empty',
    cards: 'empty',
    story: 'empty',
  }
  const hasTheme = state.edition !== null || state.look !== null
  if (hasTheme) {
    if (touched.has('theme')) result.theme = 'skipped'
    else result.theme = handlers.theme(state) === false ? 'blocked' : 'applied'
  }
  const hasCards = state.cards.length > 0 || state.lead !== null
  if (hasCards) {
    if (touched.has('cards')) result.cards = 'skipped'
    else result.cards = handlers.cards(state) === false ? 'blocked' : 'applied'
  }
  if (state.story !== null) {
    if (touched.has('story')) result.story = 'skipped'
    else if (result.cards !== 'applied') result.story = 'blocked'
    else result.story = handlers.story(state) === false ? 'blocked' : 'applied'
  }
  return result
}
