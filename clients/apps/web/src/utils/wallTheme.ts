/**
 * The wall's theme wheel — Outception's six editions, cycled by clicking
 * the logo. Each edition repaints the whole newsprint token system (page,
 * card stock, ink) via a `data-theme` attribute on <html> (see
 * globals.css). Every edition ships both tones: next-themes' light/dark
 * class (the sun/moon toggle) picks which of the edition's token sets is
 * read, independent of which palette is selected.
 *
 * No 'use client' directive: this is a utility, not a component, and its
 * browser-API calls (localStorage/document) live inside functions invoked
 * only from client code — so the module is safely importable server-side
 * (the PWA manifest reads DEFAULT_WALL_THEME through utils/brand.ts).
 */

export type WallThemeTone = 'light' | 'dark'

export interface WallTheme {
  id: string
  label: string
  /** Browser-chrome color (theme-color meta) per tone. */
  chrome: Record<WallThemeTone, string>
}

export const WALL_THEMES: readonly WallTheme[] = [
  {
    id: 'midnight',
    label: 'Midnight',
    chrome: { light: '#e9eef4', dark: '#101413' },
  },
  { id: 'tide', label: 'Tide', chrome: { light: '#dceefa', dark: '#063d61' } },
  { id: 'neon', label: 'Neon', chrome: { light: '#fae4f0', dark: '#25101f' } },
  { id: 'dune', label: 'Dune', chrome: { light: '#f2ddc0', dark: '#1d1410' } },
  {
    id: 'phosphor',
    label: 'Phosphor',
    chrome: { light: '#dff4e7', dark: '#020403' },
  },
]

// Earlier ids these editions shipped under — stored choices migrate. The
// retired Daybreak edition (and its old aliases) migrate to Dune.
const LEGACY_THEME_IDS: Record<string, string> = {
  daybreak: 'dune',
  light: 'dune',
  technical: 'dune',
  'studio-showroom': 'dune',
  beach: 'dune',
  dark: 'midnight',
  blue: 'tide',
  pink: 'neon',
  'clay-sunrise': 'dune',
  terminal: 'phosphor',
}

export const WALL_THEME_STORAGE_KEY = 'news.wallTheme'

/** First-visit default edition: Phosphor — mint paper on light systems,
 * green-on-black on dark (the tone follows the OS; a stored choice always
 * wins). */
export const DEFAULT_WALL_THEME_ID = 'phosphor'

/** The default edition's descriptor — the source of truth for the few
 * literal colors emitted outside CSS (see utils/brand.ts). */
export const DEFAULT_WALL_THEME: WallTheme = WALL_THEMES.find(
  (t) => t.id === DEFAULT_WALL_THEME_ID,
)!

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

const normalize = (id: string | null): WallTheme => {
  const canonical = id ? (LEGACY_THEME_IDS[id] ?? id) : id
  return (
    WALL_THEMES.find((t) => t.id === canonical) ??
    WALL_THEMES.find((t) => t.id === DEFAULT_WALL_THEME_ID)!
  )
}

export const getWallThemeSnapshot = (): WallTheme => {
  try {
    return normalize(localStorage.getItem(WALL_THEME_STORAGE_KEY))
  } catch {
    return normalize(null)
  }
}

export const getWallThemeServerSnapshot = (): WallTheme => normalize(null)

const apply = (theme: WallTheme) => {
  document.documentElement.dataset.theme = theme.id
  try {
    localStorage.setItem(WALL_THEME_STORAGE_KEY, theme.id)
  } catch {
    // storage disabled — the theme just won't persist
  }
  emit()
}

/** Advance one stop on the 12-stop wheel: each edition shows its light
 * face, then its dark face, then the wheel moves to the next edition —
 * every look is reachable with the logo alone. Takes the currently
 * resolved tone and returns the tone the caller must set alongside the
 * applied palette. */
export const cycleWallTheme = (
  currentTone: WallThemeTone,
): { theme: WallTheme; tone: WallThemeTone } => {
  const current = getWallThemeSnapshot()
  if (currentTone === 'light') {
    // Same edition, just flip to its dark face — the caller drives that
    // through next-themes, so there's no edition to re-apply here.
    return { theme: current, tone: 'dark' }
  }
  const index = WALL_THEMES.findIndex((t) => t.id === current.id)
  const next = WALL_THEMES[(index + 1) % WALL_THEMES.length]
  apply(next)
  return { theme: next, tone: 'light' }
}
