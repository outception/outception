import type { SupportedLocale } from '@outception-com/i18n'
import * as Flags from 'country-flag-icons/react/3x2'
import { createElement, type SVGProps } from 'react'

type FlagComponent = (typeof Flags)['GB']

// Custom inline flags for stateless / sub-national languages that have no ISO
// country of their own, so `country-flag-icons` (national flags only) can't
// supply them. Each is drawn at a 3:2 viewBox to match the country flags.

/** The Basque Ikurriña: red field, green saltire, white cross on top. */
const IkurrinaFlag = (props: SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 30 20" {...props}>
    <rect width="30" height="20" fill="#D52B1E" />
    <path d="M0 0 30 20M30 0 0 20" stroke="#009B48" strokeWidth="3.2" />
    <rect x="13" width="4" height="20" fill="#fff" />
    <rect y="8" width="30" height="4" fill="#fff" />
  </svg>
)

/** The Catalan Senyera: nine horizontal stripes, five gold and four red. */
const SenyeraFlag = (props: SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 27 18" {...props}>
    <rect width="27" height="18" fill="#FCDD09" />
    <g fill="#DA121A">
      <rect y="2" width="27" height="2" />
      <rect y="6" width="27" height="2" />
      <rect y="10" width="27" height="2" />
      <rect y="14" width="27" height="2" />
    </g>
  </svg>
)

/** The Four Provinces flag of Ireland — a quartered banner (Leinster harp,
 * Connacht eagle + armed arm, Munster's three crowns, Ulster's red hand), the
 * island's cultural emblem distinct from the state tricolour. Stylised: a
 * heraldically faithful version is illegible at flag-icon size, so each quarter
 * keeps its canonical colour with a simplified charge. */
const FourProvincesFlag = (props: SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 30 20" {...props}>
    {/* Leinster — green field, gold harp */}
    <rect width="15" height="10" fill="#169B62" />
    <g fill="#F4C430">
      <path d="M6 2.4c2.6.4 2.6 4 .9 5.2h-1c1.3-1 1.4-3.9-.7-4.2z" />
      <rect x="5.7" y="2.4" width="0.7" height="5.2" />
    </g>
    {/* Connacht — white with eagle, blue with an armed arm */}
    <rect x="15" width="7.5" height="10" fill="#fff" />
    <rect x="22.5" width="7.5" height="10" fill="#003F87" />
    <path d="M18.7 2.6 20 5l-1.3 2.4L17.4 5z" fill="#111" />
    <g fill="#F4C430">
      <rect x="25.9" y="3" width="0.8" height="4.2" />
      <path d="M25.4 3.2h1.9l-.95-1.4z" />
    </g>
    {/* Munster — blue field, three gold crowns */}
    <rect y="10" width="15" height="10" fill="#003F87" />
    <g fill="#F4C430">
      <path d="M6.1 12h2.8l-.3 1.1H6.4zM6.1 12l.55-.8.55.8.35-.8.35.8.55-.8.55.8z" />
      <path d="M4.2 14.4h2.4l-.28 1H4.48zM4.2 14.4l.5-.7.5.7.3-.7.3.7.5-.7.5.7z" />
      <path d="M8.4 14.4h2.4l-.28 1H8.68zM8.4 14.4l.5-.7.5.7.3-.7.3.7.5-.7.5.7z" />
    </g>
    {/* Ulster — gold field, red cross and the red hand on a white shield */}
    <rect x="15" y="10" width="15" height="10" fill="#FFCC00" />
    <rect x="21.8" y="10" width="1.4" height="10" fill="#CE1126" />
    <rect x="15" y="14.3" width="15" height="1.4" fill="#CE1126" />
    <circle cx="22.5" cy="15" r="2.6" fill="#fff" />
    <g stroke="#CE1126" strokeWidth="0.55" strokeLinecap="round" fill="none">
      <path d="M22.5 13.1v3.6M21.3 13.6v2.9M23.7 13.6v2.9M22 13.4v3.2M23 13.4v3.2" />
    </g>
  </svg>
)

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
  ga: FourProvincesFlag as FlagComponent,
  ca: SenyeraFlag as FlagComponent,
  eu: IkurrinaFlag as FlagComponent,
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
