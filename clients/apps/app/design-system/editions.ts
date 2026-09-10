import { type ColorSet, darkColors, lightColors } from './theme'

/**
 * The wall's theme editions - Outception's five newsprint palettes, ported from
 * the web `wallTheme` / globals.css. Each edition repaints the page, card stock,
 * ink, and accent for both tones; the OS light/dark setting picks which tone is
 * read. The logo cycles editions (see themeStore). Values mirror the web CSS
 * `--color-paper` / `--color-paper-sheet` / `--color-ink` / `--color-brand-*`.
 */

export type EditionTone = 'light' | 'dark'

type ToneColors = {
  bg: string
  card: string
  /** Stock the peeking neighbours are printed on - duller than the front card,
   * which is what gives the stack its depth. Web: --color-paper-sheet-under /
   * --color-paper-night-under. */
  cardUnder: string
  text: string
  accent: string
  /** The edition's --color-brand-700 - active chip fill under white text. The
   * web ramp is shared by both tones (`.dark` blocks only swap the page
   * gradient), so light and dark carry the same value. */
  accentStrong: string
}

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
    // The default edition: a flat neutral grey page with white cards, and the
    // mark's red as the accent. Mirrors globals.css.
    light: {
      bg: '#eeeeee',
      card: '#ffffff',
      cardUnder: '#e4e4e4',
      text: '#000000',
      accent: '#e81c2e',
      accentStrong: '#98101c',
    },
    dark: {
      bg: '#191617',
      card: '#1f1b1c',
      cardUnder: '#141112',
      text: '#ffffff',
      accent: '#e81c2e',
      accentStrong: '#98101c',
    },
  },
  {
    id: 'tide',
    label: 'Tide',
    light: {
      bg: '#dceefa',
      card: '#ffffff',
      cardUnder: '#cfe7f5',
      text: '#000000',
      accent: '#21a1d6',
      accentStrong: '#0f6a91',
    },
    dark: {
      bg: '#08324f',
      card: '#0a3a5c',
      cardUnder: '#072b45',
      text: '#ffffff',
      accent: '#45b4e0',
      accentStrong: '#0f6a91',
    },
  },
  {
    id: 'phosphor',
    label: 'Phosphor',
    light: {
      bg: '#dff4e7',
      card: '#fbfffc',
      cardUnder: '#d3eede',
      text: '#000000',
      accent: '#1fe266',
      accentStrong: '#0d953f',
    },
    dark: {
      bg: '#04140b',
      card: '#05190e',
      cardUnder: '#030f08',
      text: '#ffffff',
      accent: '#3df57e',
      accentStrong: '#0d953f',
    },
  },
  {
    id: 'neon',
    label: 'Neon',
    light: {
      bg: '#fae4f0',
      card: '#fffbfd',
      cardUnder: '#f5d9e8',
      text: '#000000',
      accent: '#ff2f98',
      accentStrong: '#ab1662',
    },
    dark: {
      bg: '#2b1322',
      card: '#331728',
      cardUnder: '#22101b',
      text: '#ffffff',
      accent: '#ff61b2',
      accentStrong: '#ab1662',
    },
  },
  {
    id: 'dune',
    label: 'Dune',
    light: {
      bg: '#f2ddc0',
      card: '#fff8ec',
      cardUnder: '#f6e9d4',
      text: '#000000',
      accent: '#dfa053',
      accentStrong: '#9c6527',
    },
    dark: {
      bg: '#211610',
      card: '#261a13',
      cardUnder: '#1a110c',
      text: '#ffffff',
      accent: '#f2bc74',
      accentStrong: '#9c6527',
    },
  },
]

// First-visit default: Midnight - flat neutral grey by day, the same page
// inverted by night, carrying the mark's red as its accent.
// the App Store hero's red glow on dark (matches the web default edition).
export const DEFAULT_EDITION_ID = 'midnight'

export const editionIds: readonly string[] = EDITIONS.map((e) => e.id)

const byId = (id: string): Edition =>
  EDITIONS.find((e) => e.id === id) ??
  EDITIONS.find((e) => e.id === DEFAULT_EDITION_ID)!

/** Blend a hex colour toward a background at the given alpha, the way the web
 * does with `color-mix(in srgb, var(--color-ink) N%, transparent)` over the
 * paper. Returns an opaque hex, since RN borders don't compose alpha the way
 * a CSS colour-mix over a known backdrop does. */
// Exported for the heatmap card's heat ramp: tile colors are statusGreen/
// statusRed mixed over the card stock by |change| so they stay theme-derived.
export const mix = (ink: string, paper: string, alpha: number): string => {
  const parse = (h: string) => {
    const v = h.replace('#', '')
    return [
      parseInt(v.slice(0, 2), 16),
      parseInt(v.slice(2, 4), 16),
      parseInt(v.slice(4, 6), 16),
    ]
  }
  const [ir, ig, ib] = parse(ink)
  const [pr, pg, pb] = parse(paper)
  const c = (i: number, p: number) =>
    Math.round(i * alpha + p * (1 - alpha))
      .toString(16)
      .padStart(2, '0')
  return `#${c(ir, pr)}${c(ig, pg)}${c(ib, pb)}`
}

/** A full colour set for an edition + tone: the tone's base set with the
 * edition's paper/card/ink/accent painted over it.
 *
 * `border` and `subtext` are DERIVED from the edition's ink, matching the web,
 * where every rule is `ink @16%` and every kicker `ink @52%` over the current
 * paper. Keeping the neutral base set here was wrong in both tones: it drew a
 * warm beige hairline on a cool blue card in light, and - worse - a near-black
 * hairline in dark where the web draws a PALE one. */
export const editionColors = (id: string, tone: EditionTone): ColorSet => {
  const base = tone === 'dark' ? darkColors : lightColors
  const ov = byId(id)[tone]
  const rule = mix(ov.text, ov.card, tone === 'dark' ? 0.18 : 0.16)
  const muted = mix(ov.text, ov.card, tone === 'dark' ? 0.58 : 0.62)
  return {
    ...base,
    background: ov.bg,
    'background-regular': ov.bg,
    card: ov.card,
    cardUnder: ov.cardUnder ?? ov.card,
    text: ov.text,
    'foreground-regular': ov.text,
    primary: ov.accent,
    primaryStrong: ov.accentStrong,
    border: rule,
    // The web's ink-alpha ladder, mixed over the PAGE (these sit on the wall,
    // not on a card): pill ring at 30/20%, ornament rules at 7/8%, field tint
    // at 3/4% - one `border` for all three flattened the header's hierarchy.
    borderStrong: mix(ov.text, ov.bg, tone === 'dark' ? 0.2 : 0.3),
    borderFaint: mix(ov.text, ov.bg, tone === 'dark' ? 0.08 : 0.07),
    inputTint: mix(ov.text, ov.bg, tone === 'dark' ? 0.04 : 0.03),
    subtext: muted,
    // Chrome that sits at the BOTTOM of the page gradient (footer, pager).
    // Several "light" editions end dark (dune → #94532f), where ink-derived
    // colors vanish - so these pick light or dark ink by the end-stop's
    // luminance instead of the tone.
    pageEndText: onPageEnd(ov, 0.75),
    pageEndBorder: onPageEnd(ov, 0.35),
  }
}

/** Perceived luminance (0..1) of a #rrggbb color. */
const luminance = (hex: string): number => {
  const v = hex.replace('#', '')
  const r = parseInt(v.slice(0, 2), 16)
  const g = parseInt(v.slice(2, 4), 16)
  const b = parseInt(v.slice(4, 6), 16)
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
}

/** Ink for chrome sitting directly on the page: of the edition's paper and
 * ink, blend in the LIGHTER one over a dark page and the darker one over a
 * light page. Derived against `bg`, the colour actually painted - it used to
 * read a separate "gradient end stop" field, and once the page became flat
 * that colour was no longer on screen anywhere, leaving Dune's light footer
 * at 1.14:1 against its own background. */
const onPageEnd = (ov: ToneColors, alpha: number): string => {
  const [lighter, darker] =
    luminance(ov.card) >= luminance(ov.text)
      ? [ov.card, ov.text]
      : [ov.text, ov.card]
  return luminance(ov.bg) < 0.5
    ? mix(lighter, ov.bg, alpha)
    : mix(darker, ov.bg, alpha)
}
