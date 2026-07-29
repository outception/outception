import AsyncStorage from '@react-native-async-storage/async-storage'
import { DEFAULT_EDITION_ID, editionIds } from './editions'
import { setTone } from './toneStore'

/**
 * The active theme edition - device-local, AsyncStorage-backed, exposed as an
 * external store for `useSyncExternalStore`. The logo cycles editions (mobile
 * mirror of the web logo-click theme wheel); the OS setting still picks the
 * light/dark tone.
 */

const KEY = 'news.wallTheme'

let edition = DEFAULT_EDITION_ID
let hydrated = false
let inFlight = false

const listeners = new Set<() => void>()
const emit = () => {
  for (const listener of listeners) listener()
}

const normalize = (id: string | null): string =>
  id && editionIds.includes(id) ? id : DEFAULT_EDITION_ID

const hydrate = () => {
  if (hydrated || inFlight) return
  inFlight = true
  void AsyncStorage.getItem(KEY)
    .then((stored) => {
      inFlight = false
      // A cycle during the read already set `hydrated` and wrote the user's
      // choice - don't clobber it with the stored value.
      if (hydrated) return
      hydrated = true
      const next = normalize(stored)
      if (next !== edition) {
        edition = next
        emit()
      }
    })
    .catch(() => {
      inFlight = false
    })
}

export const subscribeEdition = (listener: () => void): (() => void) => {
  hydrate()
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getEditionSnapshot = (): string => edition

/**
 * Advance the wall look, exactly like the web logo-wheel
 * (`apps/web/src/utils/wallTheme.ts` cycleWallTheme): light → the same
 * edition's dark → the next edition's light → … so one control reaches every
 * look and the app needs no separate tone button.
 *
 * @param currentTone the tone showing right now, resolved against the OS.
 */
export const cycleEdition = (currentTone: 'light' | 'dark' = 'dark'): void => {
  if (currentTone === 'light') {
    // Same edition, flip to its dark half. Deliberately does NOT mark hydrated:
    // this branch never writes an edition, so claiming it did would make an
    // in-flight hydrate() discard the reader's saved edition and strand the
    // session on the default.
    setTone('dark')
    emit()
    return
  }
  // An explicit edition choice wins over any in-flight hydration (see hydrate).
  hydrated = true
  const index = editionIds.indexOf(edition)
  edition = editionIds[(index + 1) % editionIds.length]
  setTone('light')
  void AsyncStorage.setItem(KEY, edition).catch(() => {})
  emit()
}
