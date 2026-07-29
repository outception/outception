import AsyncStorage from '@react-native-async-storage/async-storage'
import { useSyncExternalStore } from 'react'
import { useColorScheme } from 'react-native'

/**
 * In-app light/dark tone override — device-local, AsyncStorage-backed. Defaults
 * to `system` (follows the OS setting, like before); the header sun/moon button
 * sets an explicit `light`/`dark`, mirroring the web wall's in-app tone toggle.
 * Consumed via `useTone()`, which resolves the override against the OS setting.
 */

type ToneOverride = 'system' | 'light' | 'dark'

const KEY = 'news.tone'

let tone: ToneOverride = 'system'
let hydrated = false
let inFlight = false

const listeners = new Set<() => void>()
const emit = () => {
  for (const listener of listeners) listener()
}

const normalize = (value: string | null): ToneOverride =>
  value === 'light' || value === 'dark' ? value : 'system'

const hydrate = () => {
  if (hydrated || inFlight) return
  inFlight = true
  void AsyncStorage.getItem(KEY)
    .then((stored) => {
      inFlight = false
      if (hydrated) return
      hydrated = true
      const next = normalize(stored)
      if (next !== tone) {
        tone = next
        emit()
      }
    })
    .catch(() => {
      inFlight = false
    })
}

export const subscribeTone = (listener: () => void): (() => void) => {
  hydrate()
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getToneSnapshot = (): ToneOverride => tone

/** Set an explicit tone (or back to `system`), persist, and notify. */
export const setTone = (next: ToneOverride): void => {
  hydrated = true
  tone = next
  void AsyncStorage.setItem(KEY, next).catch(() => {})
  emit()
}

/** The effective tone: the explicit override if set, else the OS setting. */
export const useTone = (): 'light' | 'dark' => {
  const override = useSyncExternalStore(
    subscribeTone,
    getToneSnapshot,
    getToneSnapshot,
  )
  const scheme = useColorScheme()
  if (override === 'light' || override === 'dark') return override
  return scheme === 'dark' ? 'dark' : 'light'
}
