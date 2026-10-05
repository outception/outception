/**
 * The wall's theme wheel on the web. The editions table is news-core's; this
 * module applies an edition through a `data-theme` attribute on <html> (see
 * globals.css) and remembers it in localStorage. Every edition ships both
 * tones: the light/dark class (the sun and moon toggle) picks which of the
 * edition's token sets is read, independent of which palette is selected.
 *
 * No 'use client' directive: this is a utility, not a component, and its
 * browser calls live inside functions invoked only from client code, so the
 * module is safely importable server-side (the manifest reads
 * DEFAULT_WALL_THEME through utils/brand.ts).
 */

import {
  DEFAULT_EDITION,
  DEFAULT_EDITION_ID,
  EDITION_STORAGE_KEY,
  WALL_EDITIONS,
  normalizeEdition,
  type WallEdition,
  type WallTone,
} from '@outception-com/news-core'

export type WallThemeTone = WallTone
export type WallTheme = WallEdition

export const WALL_THEMES: readonly WallTheme[] = WALL_EDITIONS
export const WALL_THEME_STORAGE_KEY = EDITION_STORAGE_KEY
export const DEFAULT_WALL_THEME_ID = DEFAULT_EDITION_ID
export const DEFAULT_WALL_THEME: WallTheme = DEFAULT_EDITION

const listeners = new Set<() => void>()
const emit = () => {
  for (const listener of listeners) listener()
}

export const subscribeWallTheme = (listener: () => void): (() => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getWallThemeSnapshot = (): WallTheme => {
  try {
    return normalizeEdition(localStorage.getItem(WALL_THEME_STORAGE_KEY))
  } catch {
    return normalizeEdition(null)
  }
}

export const getWallThemeServerSnapshot = (): WallTheme =>
  normalizeEdition(null)

const apply = (theme: WallTheme) => {
  document.documentElement.dataset.theme = theme.id
  try {
    localStorage.setItem(WALL_THEME_STORAGE_KEY, theme.id)
  } catch {
    // storage disabled: the theme just won't persist
  }
  emit()
}

/** Jump straight to one edition, for the swatch fan the logo opens. Tone is
 * the caller's to set through the tone toggle. */
export const setWallTheme = (id: string): WallTheme => {
  const theme = normalizeEdition(id)
  apply(theme)
  return theme
}
