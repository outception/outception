import { EDITIONS, editionColors } from './editions'
import { makeTheme, type Theme } from './theme'

/** Precomputed Restyle themes for every edition × tone. Keyed by edition id. */
export const editionThemes: Record<string, { light: Theme; dark: Theme }> =
  Object.fromEntries(
    EDITIONS.map((e) => [
      e.id,
      {
        light: makeTheme(editionColors(e.id, 'light')),
        dark: makeTheme(editionColors(e.id, 'dark')),
      },
    ]),
  )
