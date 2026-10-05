/**
 * Device-local reader preferences on the app: the news-core store bound to
 * the AsyncStorage mirror, exposed as external stores for
 * `useSyncExternalStore`. Following is anonymous and lives on the device.
 */

import {
  EMPTY_LIST,
  NO_FOCUS_REQUEST,
  PREF_KEYS,
  createFlagStore,
  createMutedWordsStore,
  createPrefsStore,
  createPushStore,
  createReadStore,
  type FocusRequest,
} from '@outception-com/news-core'
import { createStorageMirror } from './storageMirror'

export const storage = createStorageMirror()

const store = createPrefsStore(storage)
export const mutedWords = createMutedWordsStore(storage)
export const flags = createFlagStore(storage)
export const readItems = createReadStore(storage)
export const pushProfiles = createPushStore(storage)

const HYDRATED_KEYS = [
  PREF_KEYS.focused,
  PREF_KEYS.hidden,
  PREF_KEYS.templates,
  PREF_KEYS.profiles,
  PREF_KEYS.collapsed,
  PREF_KEYS.mutedWords,
  PREF_KEYS.flags,
  PREF_KEYS.readItems,
  PREF_KEYS.pushProfiles,
  PREF_KEYS.firstVisit,
  PREF_KEYS.cardPositions,
  PREF_KEYS.edition,
  PREF_KEYS.look,
]

/** Warm every store from disk once at start, then tell the subscribers. */
export const hydratePrefs = (): Promise<void> =>
  storage.hydrate(HYDRATED_KEYS).then(() => {
    store.refresh()
    mutedWords.refresh()
    flags.refresh()
    readItems.refresh()
    pushProfiles.refresh()
  })

export const subscribeFocused = store.subscribe
export const subscribeHidden = store.subscribe
export const getFocusedSnapshot = (): readonly string[] =>
  store.getState().focused
export const getHiddenSnapshot = (): readonly string[] =>
  store.getState().hidden
export const getActiveTemplatesSnapshot = (): readonly string[] =>
  store.getState().templates
export const getBriefingProfilesSnapshot = (): readonly string[] =>
  store.getState().profiles
export const getCollapsedSnapshot = (): readonly string[] =>
  store.getState().collapsed

/** True when the reader explicitly emptied the card set: the wall shows the
 * empty state instead of re-seeding. */
export const getCardsClearedSnapshot = (): boolean => {
  const state = store.getState()
  return state.touched && state.focused.length === 0
}

export const getFocusRequestSnapshot = (): FocusRequest =>
  store.getFocusRequest()
export const NO_FOCUS = NO_FOCUS_REQUEST
export const EMPTY = EMPTY_LIST

export const setSeedCards = store.setSeed
export const toggleFocus = store.toggleFocus
export const followAll = store.followAll
export const replaceAll = store.replaceAll
export const unfollowAll = store.unfollowAll
export const hideSource = store.hideSource
export const unhideSource = store.unhideSource
export const setActiveTemplates = store.setActiveTemplates
export const setBriefingProfiles = store.setBriefingProfiles
export const toggleCollapsed = store.toggleCollapsed

/** Unfollow from a card. Hiding means unfollowing too, on both clients. */
export const removeFocus = store.hideSource

export { MAX_BULK_FOLLOW, MAX_CARDS } from '@outception-com/news-core'

export const subscribeMutedWords = mutedWords.subscribe
export const getMutedWords = mutedWords.getWords
export const addMutedWord = mutedWords.add
export const removeMutedWord = mutedWords.remove
export { isMuted } from '@outception-com/news-core'
