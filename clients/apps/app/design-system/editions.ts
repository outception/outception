import { type ColorSet, darkColors, lightColors } from './theme'

/**
 * The wall's theme editions — Outception's five newsprint palettes, ported from
 * the web `wallTheme` / globals.css. Each edition repaints the page, card stock,
 * ink, and accent for both tones; the OS light/dark setting picks which tone is
 * read. The logo cycles editions (see themeStore). Values mirror the web CSS
 * `--color-paper` / `--color-paper-sheet` / `--color-ink` / `--color-brand-*`.
 */

export type EditionTone = 'light' | 'dark'

type ToneColors = {
  bg: string
  card: string
  /** Stock the peeking neighbours are printed on — duller than the front card,
   * which is what gives the stack its depth. Web: --color-paper-sheet-under /
   * --color-paper-night-under. */
  cardUnder: string
  text: string
  accent: string
  /** The page gradient's LAST stop (SpectraBackground) — the color the footer
   * and pager actually sit on. Several "light" editions end DARK (dune fades
   * to #94532f), so ink-derived chrome vanishes down there; pageEndText/-Border
   * are derived against this instead. */
  pageEnd: string
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
    light: {
      bg: '#e9eef4',
      card: '#fbfdfe',
      cardUnder: '#e1e9f0',
      text: '#1b2836',
      accent: '#74a0b9',
      pageEnd: '#c6d2dd',
    },
    dark: {
      bg: '#171d25',
      card: '#1b222b',
      cardUnder: '#12181f',
      text: '#d6e1ea',
      accent: '#8fb3c9',
      pageEnd: '#06080b',
    },
  },
  {
    id: 'tide',
    label: 'Tide',
    light: {
      bg: '#dceefa',
      card: '#ffffff',
      cardUnder: '#cfe7f5',
      text: '#073a52',
      accent: '#21a1d6',
      pageEnd: '#5da8cf',
    },
    dark: {
      bg: '#08324f',
      card: '#0a3a5c',
      cardUnder: '#072b45',
      text: '#dbf2ff',
      accent: '#45b4e0',
      pageEnd: '#063d61',
    },
  },
  {
    id: 'neon',
    label: 'Neon',
    light: {
      bg: '#fae4f0',
      card: '#fffbfd',
      cardUnder: '#f5d9e8',
      text: '#55103a',
      accent: '#ff2f98',
      pageEnd: '#d891bd',
    },
    dark: {
      bg: '#2b1322',
      card: '#331728',
      cardUnder: '#22101b',
      text: '#ffd9ec',
      accent: '#ff61b2',
      pageEnd: '#25101f',
    },
  },
  {
    id: 'dune',
    label: 'Dune',
    light: {
      bg: '#f2ddc0',
      card: '#fff8ec',
      cardUnder: '#f6e9d4',
      text: '#45260f',
      accent: '#dfa053',
      pageEnd: '#94532f',
    },
    dark: {
      bg: '#211610',
      card: '#261a13',
      cardUnder: '#1a110c',
      text: '#f6e4cc',
      accent: '#f2bc74',
      pageEnd: '#120a06',
    },
  },
  {
    id: 'phosphor',
    label: 'Phosphor',
    light: {
      bg: '#dff4e7',
      card: '#fbfffc',
      cardUnder: '#d3eede',
      text: '#0a3a20',
      accent: '#1fe266',
      pageEnd: '#7cc697',
    },
    dark: {
      bg: '#04140b',
      card: '#05190e',
      cardUnder: '#030f08',
      text: '#66ff99',
      accent: '#3df57e',
      pageEnd: '#000201',
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

/** Blend a hex colour toward a background at the given alpha, the way the web
 * does with `color-mix(in srgb, var(--color-ink) N%, transparent)` over the
 * paper. Returns an opaque hex, since RN borders don't compose alpha the way
 * a CSS colour-mix over a known backdrop does. */
const mix = (ink: string, paper: string, alpha: number): string => {
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
 * warm beige hairline on a cool blue card in light, and — worse — a near-black
 * hairline in dark where the web draws a PALE one. */
export const editionColors = (id: string, tone: EditionTone): ColorSet => {
  const base = tone === 'dark' ? darkColors : lightColors
  const ov = byId(id)[tone]
  const rule = mix(ov.text, ov.card, tone === 'dark' ? 0.18 : 0.16)
  const muted = mix(ov.text, ov.card, tone === 'dark' ? 0.48 : 0.52)
  return {
    ...base,
    background: ov.bg,
    'background-regular': ov.bg,
    card: ov.card,
    cardUnder: ov.cardUnder ?? ov.card,
    text: ov.text,
    'foreground-regular': ov.text,
    primary: ov.accent,
    border: rule,
    // The web's ink-alpha ladder, mixed over the PAGE (these sit on the wall,
    // not on a card): pill ring at 30/20%, ornament rules at 7/8%, field tint
    // at 3/4% — one `border` for all three flattened the header's hierarchy.
    borderStrong: mix(ov.text, ov.bg, tone === 'dark' ? 0.2 : 0.3),
    borderFaint: mix(ov.text, ov.bg, tone === 'dark' ? 0.08 : 0.07),
    inputTint: mix(ov.text, ov.bg, tone === 'dark' ? 0.04 : 0.03),
    subtext: muted,
    // Chrome that sits at the BOTTOM of the page gradient (footer, pager).
    // Several "light" editions end dark (dune → #94532f), where ink-derived
    // colors vanish — so these pick light or dark ink by the end-stop's
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

/** Ink for chrome over the gradient's end stop: of the edition's paper and
 * ink, blend in the LIGHTER one over dark ends and the darker one over light
 * ends. (In dark tone the paper itself is near-black — blindly picking
 * "paper over dark ends" produced dark-on-dark.) */
const onPageEnd = (ov: ToneColors, alpha: number): string => {
  const [lighter, darker] =
    luminance(ov.card) >= luminance(ov.text)
      ? [ov.card, ov.text]
      : [ov.text, ov.card]
  return luminance(ov.pageEnd) < 0.5
    ? mix(lighter, ov.pageEnd, alpha)
    : mix(darker, ov.pageEnd, alpha)
}
