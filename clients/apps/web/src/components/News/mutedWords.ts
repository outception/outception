'use client'

/** Muted words on the web: the news-core store bound to localStorage. */

import { createMutedWordsStore, EMPTY_LIST } from '@outception-com/news-core'
import { browserStorage } from './newsPrefsStore'

export { isMuted } from '@outception-com/news-core'

const store = createMutedWordsStore(browserStorage)

export const getMutedWords = store.getWords

/** Stable reference for the server snapshot: a fresh `[]` per render would
 * make React see a changed store on every pass. */
export const getMutedWordsServerSnapshot = (): readonly string[] => EMPTY_LIST

export const subscribeMutedWords = store.subscribe
export const addMutedWord = store.add
export const removeMutedWord = store.remove
