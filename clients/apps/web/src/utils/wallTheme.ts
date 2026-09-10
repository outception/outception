/**
 * The wall's theme wheel - Outception's five editions, cycled by clicking
 * the logo. Each edition repaints the whole newsprint token system (page,
 * card stock, ink) via a `data-theme` attribute on <html> (see
 * globals.css). Every edition ships both tones: next-themes' light/dark
 * class (the sun/moon toggle) picks which of the edition's token sets is
 * read, independent of which palette is selected.
 *
 * No 'use client' directive: this is a utility, not a component, and its
 * browser-API calls (localStorage/document) live inside functions invoked
 * only from client code - so the module is safely importable server-side
 * (the PWA manifest reads DEFAULT_WALL_THEME through utils/brand.ts).
 */

export type WallThemeTone = 'light' | 'dark'

export interface WallTheme {
  id: string
  label: string
  /** Browser-chrome color (theme-color meta) per tone. */
  chrome: Record<WallThemeTone, string>
  /** The edition's brand colour (mirrors --color-brand-500 in globals.css).
   * The swatch shows it as an inner dot, so one circle carries both the page
   * it applies AND the accent that comes with it. */
  accent: string
}

// Wheel order, and it is the order the reader sees: the neutral grey first
// (it is the default and the quietest reading surface), then the colours -
// blue, green, pink - with the warm brown last.
export const WALL_THEMES: readonly WallTheme[] = [
  // Display order, and the order the swatch fan shows on BOTH sides: grey,
  // blue, purple, green, cream. Nothing keys off the index - `brand.test.ts`
  // iterates the list and `layout.tsx` duplicates by id - so this is free to
  // be whatever reads best.
  {
    id: 'midnight',
    label: 'Midnight',
    chrome: { light: '#eeeeee', dark: '#191617' },
    accent: '#e81c2e',
  },
  {
    id: 'tide',
    label: 'Tide',
    chrome: { light: '#dceefa', dark: '#08324f' },
    accent: '#21a1d6',
  },
  {
    id: 'neon',
    label: 'Neon',
    chrome: { light: '#fae4f0', dark: '#2b1322' },
    accent: '#ff2f98',
  },
  {
    id: 'phosphor',
    label: 'Phosphor',
    chrome: { light: '#dff4e7', dark: '#04140b' },
    accent: '#1fe266',
  },
  {
    id: 'dune',
    label: 'Dune',
    chrome: { light: '#f2ddc0', dark: '#211610' },
    accent: '#dfa053',
  },
]

// Earlier ids these editions shipped under - stored choices migrate. The
// retired Daybreak edition (and its old aliases) migrate to Dune.
const LEGACY_THEME_IDS: Record<string, string> = {
  // Ruby's look moved onto midnight when it became the default, so anyone
  // holding a stored 'ruby' lands on the same page they had.
  ruby: 'midnight',
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

/** First-visit default edition: Midnight - a flat neutral grey page with white
 * cards by day, the same page inverted with a hint of the mark's red by night
 * (the tone follows the OS; a stored choice always wins). It carries the
 * brand's favicon red on the gem. */
export const DEFAULT_WALL_THEME_ID = 'midnight'

/** The default edition's descriptor - the source of truth for the few
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
    // storage disabled - the theme just won't persist
  }
  emit()
}

/** Jump straight to one edition, for the swatch fan the logo opens.
 *
 * The wheel below still exists, but stepping it was the only way to reach a
 * look: ten clicks to get back to where you started. The fan shows every
 * edition at once, so this sets one directly. Tone is the caller's to set
 * through next-themes, exactly as the wheel does. */
export const setWallTheme = (id: string): WallTheme => {
  const theme = normalize(id)
  apply(theme)
  return theme
}
