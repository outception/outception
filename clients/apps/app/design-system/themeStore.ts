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

// Editions that have been retired, and what a stored choice migrates to.
// Unknown ids already fall back to the default, but naming the mapping keeps
// the migration correct if the default ever moves again - and mirrors the
// web's LEGACY_THEME_IDS.
const RETIRED: Record<string, string> = { ruby: 'midnight' }

const normalize = (id: string | null): string => {
  const canonical = id ? (RETIRED[id] ?? id) : id
  return canonical && editionIds.includes(canonical)
    ? canonical
    : DEFAULT_EDITION_ID
}

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
 * Advance the wall look: light → the same edition's dark → the next edition's
 * light → … so one control reaches every look and the app needs no separate
 * tone button.
 *
 * The web NO LONGER works this way. Its logo used to step the identical wheel,
 * but reaching the last look took ten taps through nine nobody wanted, so it
 * now fans out every edition in both tones at once
 * (`apps/web/src/components/Layout/Public/WallThemeSwatches.tsx`). The two
 * platforms are deliberately out of step until that fan is ported here; this
 * wheel is what the app still does.
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
