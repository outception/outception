'use client'

/**
 * The reader's device-local preferences on the web: the news-core store bound
 * to localStorage and exposed as an external store for `useSyncExternalStore`.
 * The server snapshots are stable defaults, so the first client render matches
 * the server and every subscriber re-renders when a value changes.
 */

import {
  EMPTY_LIST,
  NO_FOCUS_REQUEST,
  createPrefsStore,
  type FocusRequest,
  type PrefsStorage,
} from '@outception-com/news-core'

/** localStorage behind the news-core storage contract: absent on the server,
 * tolerant of private mode and full quotas. */
export const browserStorage: PrefsStorage = {
  getItem: (key) => {
    if (typeof window === 'undefined') return null
    try {
      return localStorage.getItem(key)
    } catch {
      return null
    }
  },
  setItem: (key, value) => {
    if (typeof window === 'undefined') return
    localStorage.setItem(key, value)
  },
  removeItem: (key) => {
    if (typeof window === 'undefined') return
    localStorage.removeItem(key)
  },
}

const store = createPrefsStore(browserStorage)

export const subscribe = store.subscribe

export const getFocusedSnapshot = (): readonly string[] =>
  store.getState().focused
export const getFocusedServerSnapshot = (): readonly string[] => EMPTY_LIST

export const getHiddenSnapshot = (): readonly string[] =>
  store.getState().hidden
export const getHiddenServerSnapshot = (): readonly string[] => EMPTY_LIST

/** True when the reader explicitly emptied the card set: the wall shows the
 * empty state instead of re-seeding. */
export const getCardsClearedSnapshot = (): boolean => {
  const state = store.getState()
  return state.touched && state.focused.length === 0
}
export const getCardsClearedServerSnapshot = (): boolean => false

export const getActiveTemplatesSnapshot = (): readonly string[] =>
  store.getState().templates
export const getActiveTemplatesServerSnapshot = (): readonly string[] =>
  EMPTY_LIST

export const getBriefingProfilesSnapshot = (): readonly string[] =>
  store.getState().profiles
export const getBriefingProfilesServerSnapshot = (): readonly string[] =>
  EMPTY_LIST

export const getCollapsedSnapshot = (): readonly string[] =>
  store.getState().collapsed
export const getCollapsedServerSnapshot = (): readonly string[] => EMPTY_LIST

export const getFocusRequestSnapshot = (): FocusRequest =>
  store.getFocusRequest()
export const getFocusRequestServerSnapshot = (): FocusRequest =>
  NO_FOCUS_REQUEST

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
export const refreshPrefs = store.refresh
