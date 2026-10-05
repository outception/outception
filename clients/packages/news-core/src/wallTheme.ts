/**
 * The theme wheel: the five editions, each repainting the whole newsprint
 * token system, and the two CSS-only looks layered over images and chrome.
 * This is the table both clients read; applying it (a data attribute on the
 * web, a Restyle theme in the app) stays with each renderer. The app applies
 * editions and ignores looks, which is why the share link carries them as
 * separate tokens.
 */

export type WallTone = 'light' | 'dark'

export interface WallEdition {
  id: string
  label: string
  /** Browser-chrome and status-bar colour per tone. */
  chrome: Readonly<Record<WallTone, string>>
  /** The edition's brand colour; the swatch shows it as an inner dot. */
  accent: string
}

// Display order, the order the swatch fan shows: the neutral grey first (the
// default and the quietest reading surface), then the colours, the warm
// brown last. Nothing keys off the index.
export const WALL_EDITIONS: readonly WallEdition[] = Object.freeze([
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
])

export const DEFAULT_EDITION_ID = 'midnight'

// Earlier ids these editions shipped under: stored choices migrate.
export const LEGACY_EDITION_IDS: Readonly<Record<string, string>> =
  Object.freeze({
    ruby: 'midnight',
    dark: 'midnight',
    daybreak: 'dune',
    light: 'dune',
    technical: 'dune',
    'studio-showroom': 'dune',
    beach: 'dune',
    'clay-sunrise': 'dune',
    blue: 'tide',
    pink: 'neon',
    terminal: 'phosphor',
  })

export const EDITION_STORAGE_KEY = 'news.wallTheme'
export const LOOK_STORAGE_KEY = 'news.wallLook'

export const DEFAULT_EDITION: WallEdition = WALL_EDITIONS.find(
  (e) => e.id === DEFAULT_EDITION_ID,
)!

/** The edition for a stored or shared id: legacy ids migrate, unknown ids
 * land on the default. */
export const normalizeEdition = (
  id: string | null | undefined,
): WallEdition => {
  const canonical = id ? (LEGACY_EDITION_IDS[id] ?? id) : null
  return WALL_EDITIONS.find((e) => e.id === canonical) ?? DEFAULT_EDITION
}

export const isEditionId = (id: string): boolean =>
  WALL_EDITIONS.some((e) => e.id === id)

export interface WallLook {
  id: string
  label: string
  /** CSS filter parameters; the web applies them to images and chrome,
   * never to body text. The app ignores looks. */
  filter: Readonly<{
    grayscale: number
    contrast: number
    sepia: number
    brightness: number
  }>
  vignette: boolean
  grain: boolean
  scanlines: boolean
  /** A tint laid over images, as an rgba() string, or null. */
  tint: string | null
}

export const PLAIN_LOOK_ID = 'plain'

export const WALL_LOOKS: readonly WallLook[] = Object.freeze([
  {
    id: PLAIN_LOOK_ID,
    label: 'Plain',
    filter: { grayscale: 0, contrast: 1, sepia: 0, brightness: 1 },
    vignette: false,
    grain: false,
    scanlines: false,
    tint: null,
  },
  {
    id: 'noir',
    label: 'Noir',
    filter: { grayscale: 1, contrast: 1.15, sepia: 0.15, brightness: 0.95 },
    vignette: true,
    grain: true,
    scanlines: false,
    tint: null,
  },
  {
    id: 'night',
    label: 'Night',
    filter: { grayscale: 1, contrast: 1.1, sepia: 0, brightness: 0.9 },
    vignette: true,
    grain: false,
    scanlines: true,
    tint: 'rgba(31, 226, 102, 0.22)',
  },
])

export const normalizeLook = (id: string | null | undefined): WallLook =>
  WALL_LOOKS.find((l) => l.id === id) ?? WALL_LOOKS[0]!

export const isLookId = (id: string): boolean =>
  WALL_LOOKS.some((l) => l.id === id)

/** The CSS `filter` value for a look; the plain look yields `none`. */
export const lookFilter = (look: WallLook): string => {
  const f = look.filter
  if (look.id === PLAIN_LOOK_ID) return 'none'
  const parts: string[] = []
  if (f.grayscale > 0) parts.push(`grayscale(${f.grayscale})`)
  if (f.contrast !== 1) parts.push(`contrast(${f.contrast})`)
  if (f.sepia > 0) parts.push(`sepia(${f.sepia})`)
  if (f.brightness !== 1) parts.push(`brightness(${f.brightness})`)
  return parts.length > 0 ? parts.join(' ') : 'none'
}
