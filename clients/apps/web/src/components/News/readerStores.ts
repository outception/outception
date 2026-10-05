'use client'

/** The reader's switches and the headlines they opened, on the web. */

import {
  EMPTY_LIST,
  FLAGS,
  createFlagStore,
  createPushStore,
  createReadStore,
  flagOn,
  toggleFlagOn,
  type Flag,
} from '@outception-com/news-core'
import { useSyncExternalStore } from 'react'
import { browserStorage } from './newsPrefsStore'

export const flagStore = createFlagStore(browserStorage)
export const readStore = createReadStore(browserStorage)
export const pushStore = createPushStore(browserStorage)

const serverSnapshot = (): readonly string[] => EMPTY_LIST

export const useFlags = (): readonly string[] =>
  useSyncExternalStore(flagStore.subscribe, flagStore.get, serverSnapshot)

/** A switch's position: the reader's choice, else its default. Before
 * hydration every switch reads as its default. */
export const useFlag = (flag: Flag): boolean => flagOn(useFlags(), flag)

export const toggleFlag = (flag: Flag): void => toggleFlagOn(flagStore, flag)

/** The profiles this browser asked a morning push for. */
export const usePushProfiles = (): readonly string[] =>
  useSyncExternalStore(pushStore.subscribe, pushStore.get, serverSnapshot)

export const useReadItems = (): readonly string[] =>
  useSyncExternalStore(readStore.subscribe, readStore.get, serverSnapshot)

export const markRead = (id: string): void => readStore.add(id)

export { FLAGS }
