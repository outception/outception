/**
 * Share links on the app: the root listener hands every incoming address to
 * the shared parser, the theme lane applies the edition (looks are ignored
 * here), the cards lane holds the sender's deck for the wall to view without
 * touching the reader's own card set, and the story lane remembers the story
 * to open. `?card=` keeps working as the lead card.
 */

import {
  isShareLink,
  parseShareLink,
  restoreFromLink,
  type ShareLinkState,
} from '@outception-com/news-core'
import { setEdition } from '@/design-system/themeStore'

export interface SharedView {
  cards: readonly string[]
  story: string | null
}

const EMPTY_VIEW: SharedView = Object.freeze({
  cards: Object.freeze([]) as readonly string[],
  story: null,
})

let view: SharedView = EMPTY_VIEW
const listeners = new Set<() => void>()
const emit = () => {
  for (const listener of listeners) listener()
}

export const subscribeSharedView = (listener: () => void): (() => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getSharedViewSnapshot = (): SharedView => view

/** Back to the reader's own card set. */
export const clearSharedView = (): void => {
  if (view === EMPTY_VIEW) return
  view = EMPTY_VIEW
  emit()
}

/** The search and hash of an address, without the DOM's URL class. */
export const splitAddress = (url: string): { search: string; hash: string } => {
  const hashAt = url.indexOf('#')
  const beforeHash = hashAt === -1 ? url : url.slice(0, hashAt)
  const hash = hashAt === -1 ? '' : url.slice(hashAt)
  const queryAt = beforeHash.indexOf('?')
  const search = queryAt === -1 ? '' : beforeHash.slice(queryAt)
  return { search, hash }
}

/** Parse and apply an incoming address. Returns the lead card to open, or
 * null when the address carried no share. */
export const applyShareAddress = (url: string): string | null => {
  const state: ShareLinkState = parseShareLink(splitAddress(url))
  if (!isShareLink(state)) return null
  restoreFromLink(state, {
    theme: (s) => {
      if (s.edition) setEdition(s.edition)
      return true
    },
    cards: (s) => {
      view = { cards: s.cards, story: s.story }
      emit()
      return s.cards.length > 0 || s.lead !== null
    },
    story: () => true,
  })
  return state.lead
}
