/**
 * The share link's token registry. Frozen: a token is never renamed and
 * never reused for another meaning, so a link copied today still restores
 * in a year. New meanings get new tokens and a new entry in the history.
 */

export const SHARE_LINK_VERSION = 1

/** The query parameter that carries the lead card. It predates the hash
 * tokens and keeps working forever. */
export const LEAD_CARD_QUERY = 'card'

export const SHARE_TOKENS = Object.freeze({
  version: 'v',
  cards: 'c',
  story: 's',
  edition: 'e',
  look: 'l',
  topic: 'k',
  at: 'at',
} as const)

export type ShareToken = (typeof SHARE_TOKENS)[keyof typeof SHARE_TOKENS]

export interface ShareTokenRecord {
  token: ShareToken
  meaning: keyof typeof SHARE_TOKENS
  since: number
}

/** Every token ever shipped, in the version it arrived. The test asserts the
 * live table still agrees with this history entry for entry. */
export const SHARE_TOKEN_HISTORY: readonly ShareTokenRecord[] = Object.freeze([
  { token: 'v', meaning: 'version', since: 1 },
  { token: 'c', meaning: 'cards', since: 1 },
  { token: 's', meaning: 'story', since: 1 },
  { token: 'e', meaning: 'edition', since: 1 },
  { token: 'l', meaning: 'look', since: 1 },
  { token: 'k', meaning: 'topic', since: 1 },
  { token: 'at', meaning: 'at', since: 1 },
])
