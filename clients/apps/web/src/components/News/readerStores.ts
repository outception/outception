'use client'

/** The reader's switches and the headlines they opened, on the web. */

import {
  EMPTY_LIST,
  FLAGS,
  createFlagStore,
  createReadStore,
  type Flag,
} from '@outception-com/news-core'
import { useSyncExternalStore } from 'react'
import { browserStorage } from './newsPrefsStore'

export const flagStore = createFlagStore(browserStorage)
export const readStore = createReadStore(browserStorage)

const serverSnapshot = (): readonly string[] => EMPTY_LIST

export const useFlags = (): readonly string[] =>
  useSyncExternalStore(flagStore.subscribe, flagStore.get, serverSnapshot)

export const useFlag = (flag: Flag): boolean => useFlags().includes(flag)

export const toggleFlag = (flag: Flag): void => flagStore.toggle(flag)

export const useReadItems = (): readonly string[] =>
  useSyncExternalStore(readStore.subscribe, readStore.get, serverSnapshot)

export const markRead = (id: string): void => readStore.add(id)

export { FLAGS }
