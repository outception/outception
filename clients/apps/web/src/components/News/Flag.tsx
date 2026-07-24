import type { SupportedLocale } from '@outception-com/i18n'
import * as Flags from 'country-flag-icons/react/3x2'
import { createElement } from 'react'

type FlagComponent = (typeof Flags)['GB']

// Inline SVG flags (not emoji — country-flag emoji don't render on Windows).
// Each language maps to the country with the most speakers of it (e.g. Spanish
// → Mexico, Arabic → Egypt, Bengali → Bangladesh), per product direction. This
// is the flag shown for a *language*; the visitor's detected-country flag is
// resolved separately via CountryFlag.
//
// NOTE: `import * as Flags` bundles the full country set (~53KB gzipped) because
// CountryFlag resolves an arbitrary ISO code at runtime, which defeats
// tree-shaking. That's a deliberate cost of supporting a flag for *every*
// visitor country; see the review notes if this needs trimming.
const FLAG: Record<SupportedLocale, FlagComponent> = {
  en: Flags.US,
  es: Flags.MX,
  fr: Flags.FR,
  de: Flags.DE,
  it: Flags.IT,
  pt: Flags.BR,
  'pt-PT': Flags.PT,
  nl: Flags.NL,
  sv: Flags.SE,
  pl: Flags.PL,
  ru: Flags.RU,
  uk: Flags.UA,
  tr: Flags.TR,
  ar: Flags.EG,
  he: Flags.IL,
  fa: Flags.IR,
  hi: Flags.IN,
  bn: Flags.BD,
  ur: Flags.PK,
  'zh-Hans': Flags.CN,
  'zh-Hant': Flags.TW,
  ja: Flags.JP,
  ko: Flags.KR,
  id: Flags.ID,
  ms: Flags.MY,
  tl: Flags.PH,
  vi: Flags.VN,
  th: Flags.TH,
  cs: Flags.CZ,
  sk: Flags.SK,
  sl: Flags.SI,
  hu: Flags.HU,
  ro: Flags.RO,
  bg: Flags.BG,
  sr: Flags.RS,
  sq: Flags.AL,
  el: Flags.GR,
  da: Flags.DK,
  nb: Flags.NO,
  fi: Flags.FI,
  et: Flags.EE,
  lv: Flags.LV,
  lt: Flags.LT,
  ga: Flags.IE,
  ca: Flags.ES,
  eu: Flags.ES,
  hr: Flags.HR,
}

const flagStyle = (width: number) => ({
  width,
  height: (width * 2) / 3,
  borderRadius: 2,
  display: 'block' as const,
  flexShrink: 0,
})

// The flag SVG is resolved dynamically (by language or ISO country), so it's
// rendered via createElement rather than a JSX `<Svg />` on a lookup variable.
const renderFlag = (Svg: FlagComponent, width: number) =>
  createElement(Svg, { 'aria-hidden': true, style: flagStyle(width) })

/** The representative flag for a UI *language* (see FLAG above). */
export const Flag = ({
  locale,
  width = 20,
}: {
  locale: SupportedLocale
  width?: number
}) => renderFlag(FLAG[locale], width)

const countryFlagComponent = (country: string): FlagComponent | undefined =>
  (Flags as Record<string, FlagComponent | undefined>)[
    country.trim().toUpperCase()
  ]

/** Whether a flag exists for an ISO-3166 code — lets callers fall back to the
 * language flag rather than render nothing for codes with no flag (e.g.
 * Cloudflare's `T1`/`XX` edge values). */
export const hasCountryFlag = (country: string): boolean =>
  countryFlagComponent(country) !== undefined

/** The flag for a specific ISO-3166 alpha-2 country (the visitor's detected
 * country), so e.g. an Ireland visitor reading English still sees 🇮🇪 rather
 * than the English language flag. Returns null for an unknown code. */
export const CountryFlag = ({
  country,
  width = 20,
}: {
  country: string
  width?: number
}) => {
  const Svg = countryFlagComponent(country)
  return Svg ? renderFlag(Svg, width) : null
}
