import { type ColorSet, darkColors, lightColors } from './theme'

/**
 * The wall's theme editions — Outception's five newsprint palettes, ported from
 * the web `wallTheme` / globals.css. Each edition repaints the page, card stock,
 * ink, and accent for both tones; the OS light/dark setting picks which tone is
 * read. The logo cycles editions (see themeStore). Values mirror the web CSS
 * `--color-paper` / `--color-paper-sheet` / `--color-ink` / `--color-brand-*`.
 */

export type EditionTone = 'light' | 'dark'

type ToneColors = { bg: string; card: string; text: string; accent: string }

export interface Edition {
  id: string
  label: string
  light: ToneColors
  dark: ToneColors
}

export const EDITIONS: readonly Edition[] = [
  {
    id: 'midnight',
    label: 'Midnight',
    light: {
      bg: '#e9eef4',
      card: '#fbfdfe',
      text: '#1b2836',
      accent: '#74a0b9',
    },
    dark: {
      bg: '#171d25',
      card: '#1b222b',
      text: '#d6e1ea',
      accent: '#8fb3c9',
    },
  },
  {
    id: 'tide',
    label: 'Tide',
    light: {
      bg: '#dceefa',
      card: '#ffffff',
      text: '#073a52',
      accent: '#21a1d6',
    },
    dark: {
      bg: '#08324f',
      card: '#0a3a5c',
      text: '#dbf2ff',
      accent: '#45b4e0',
    },
  },
  {
    id: 'neon',
    label: 'Neon',
    light: {
      bg: '#fae4f0',
      card: '#fffbfd',
      text: '#55103a',
      accent: '#ff2f98',
    },
    dark: {
      bg: '#2b1322',
      card: '#331728',
      text: '#ffd9ec',
      accent: '#ff61b2',
    },
  },
  {
    id: 'dune',
    label: 'Dune',
    light: {
      bg: '#f2ddc0',
      card: '#fff8ec',
      text: '#45260f',
      accent: '#dfa053',
    },
    dark: {
      bg: '#211610',
      card: '#261a13',
      text: '#f6e4cc',
      accent: '#f2bc74',
    },
  },
  {
    id: 'phosphor',
    label: 'Phosphor',
    light: {
      bg: '#dff4e7',
      card: '#fbfffc',
      text: '#0a3a20',
      accent: '#1fe266',
    },
    dark: {
      bg: '#04140b',
      card: '#05190e',
      text: '#66ff99',
      accent: '#3df57e',
    },
  },
]

// First-visit default: Phosphor — mint paper on light, green-on-black on dark
// (matches the web default edition).
export const DEFAULT_EDITION_ID = 'phosphor'

export const editionIds: readonly string[] = EDITIONS.map((e) => e.id)

const byId = (id: string): Edition =>
  EDITIONS.find((e) => e.id === id) ??
  EDITIONS.find((e) => e.id === DEFAULT_EDITION_ID)!

/** A full colour set for an edition + tone: the tone's base set with the
 * edition's paper/card/ink/accent painted over it (status/border/etc. keep the
 * neutral base so component tokens stay coherent). */
export const editionColors = (id: string, tone: EditionTone): ColorSet => {
  const base = tone === 'dark' ? darkColors : lightColors
  const ov = byId(id)[tone]
  return {
    ...base,
    background: ov.bg,
    'background-regular': ov.bg,
    card: ov.card,
    text: ov.text,
    'foreground-regular': ov.text,
    primary: ov.accent,
  }
}
