import type { SupportedLocale } from '@outception-com/i18n'
import { hasFlag } from 'country-flag-icons'
import type { ComponentType, SVGProps } from 'react'

type FlagComponent = ComponentType<SVGProps<SVGSVGElement>>

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

/** The Four Provinces flag of Ireland - a quartered banner (Leinster harp,
 * Connacht eagle + armed arm, Munster's three crowns, Ulster's red hand), the
 * island's cultural emblem distinct from the state tricolour. Stylised: a
 * heraldically faithful version is illegible at flag-icon size, so each quarter
 * keeps its canonical colour with a simplified charge. */
const FourProvincesFlag = (props: SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 30 20" {...props}>
    {/* Leinster - green field, gold harp */}
    <rect width="15" height="10" fill="#169B62" />
    <g fill="#F4C430">
      <path d="M6 2.4c2.6.4 2.6 4 .9 5.2h-1c1.3-1 1.4-3.9-.7-4.2z" />
      <rect x="5.7" y="2.4" width="0.7" height="5.2" />
    </g>
    {/* Connacht - white with eagle, blue with an armed arm */}
    <rect x="15" width="7.5" height="10" fill="#fff" />
    <rect x="22.5" width="7.5" height="10" fill="#003F87" />
    <path d="M18.7 2.6 20 5l-1.3 2.4L17.4 5z" fill="#111" />
    <g fill="#F4C430">
      <rect x="25.9" y="3" width="0.8" height="4.2" />
      <path d="M25.4 3.2h1.9l-.95-1.4z" />
    </g>
    {/* Munster - blue field, three gold crowns */}
    <rect y="10" width="15" height="10" fill="#003F87" />
    <g fill="#F4C430">
      <path d="M6.1 12h2.8l-.3 1.1H6.4zM6.1 12l.55-.8.55.8.35-.8.35.8.55-.8.55.8z" />
      <path d="M4.2 14.4h2.4l-.28 1H4.48zM4.2 14.4l.5-.7.5.7.3-.7.3.7.5-.7.5.7z" />
      <path d="M8.4 14.4h2.4l-.28 1H8.68zM8.4 14.4l.5-.7.5.7.3-.7.3.7.5-.7.5.7z" />
    </g>
    {/* Ulster - gold field, red cross and the red hand on a white shield */}
    <rect x="15" y="10" width="15" height="10" fill="#FFCC00" />
    <rect x="21.8" y="10" width="1.4" height="10" fill="#CE1126" />
    <rect x="15" y="14.3" width="15" height="1.4" fill="#CE1126" />
    <circle cx="22.5" cy="15" r="2.6" fill="#fff" />
    <g stroke="#CE1126" strokeWidth="0.55" strokeLinecap="round" fill="none">
      <path d="M22.5 13.1v3.6M21.3 13.6v2.9M23.7 13.6v2.9M22 13.4v3.2M23 13.4v3.2" />
    </g>
  </svg>
)

// Flags render as flagcdn.com images (already allowed by the img-src CSP)
// instead of bundling all 257 inline SVGs, which cost ~260 KB of JS parsed on
// every page load for a picker most readers never open. The browser caches
// each flag after its first view. Each language maps to the country with the
// most speakers of it (e.g. Spanish -> Mexico, Arabic -> Egypt), per product
// direction; inline SVGs remain only for the stateless / sub-national
// languages with no ISO country (drawn above).
const FLAG_COUNTRY: Partial<Record<SupportedLocale, string>> = {
  en: 'US',
  es: 'ES',
  fr: 'FR',
  de: 'DE',
  it: 'IT',
  pt: 'BR',
  'pt-PT': 'PT',
  nl: 'NL',
  sv: 'SE',
  pl: 'PL',
  ru: 'RU',
  uk: 'UA',
  tr: 'TR',
  ar: 'EG',
  he: 'IL',
  fa: 'IR',
  hi: 'IN',
  bn: 'BD',
  ur: 'PK',
  'zh-Hans': 'CN',
  'zh-Hant': 'TW',
  ja: 'JP',
  ko: 'KR',
  id: 'ID',
  ms: 'MY',
  tl: 'PH',
  vi: 'VN',
  th: 'TH',
  cs: 'CZ',
  sk: 'SK',
  sl: 'SI',
  hu: 'HU',
  ro: 'RO',
  bg: 'BG',
  sr: 'RS',
  sq: 'AL',
  el: 'GR',
  da: 'DK',
  nb: 'NO',
  fi: 'FI',
  et: 'EE',
  lv: 'LV',
  lt: 'LT',
  hr: 'HR',
}

const CUSTOM_FLAG: Partial<Record<SupportedLocale, FlagComponent>> = {
  ga: FourProvincesFlag,
  ca: SenyeraFlag,
  eu: IkurrinaFlag,
}

const flagStyle = (width: number) => ({
  width,
  height: (width * 2) / 3,
  borderRadius: 2,
  display: 'block' as const,
  flexShrink: 0,
})

const FlagImage = ({ country, width }: { country: string; width: number }) => (
  // eslint-disable-next-line @next/next/no-img-element
  <img
    src={`https://flagcdn.com/${country.toLowerCase()}.svg`}
    alt=""
    aria-hidden
    loading="lazy"
    style={flagStyle(width)}
  />
)

/** The representative flag for a UI *language* (see FLAG_COUNTRY above). */
export const Flag = ({
  locale,
  width = 20,
}: {
  locale: SupportedLocale
  width?: number
}) => {
  const Custom = CUSTOM_FLAG[locale]
  if (Custom) return <Custom aria-hidden style={flagStyle(width)} />
  const country = FLAG_COUNTRY[locale]
  return country ? <FlagImage country={country} width={width} /> : null
}

/** Whether a flag exists for an ISO-3166 code - lets callers fall back to the
 * language flag rather than render nothing for codes with no flag (e.g.
 * Cloudflare's `T1`/`XX` edge values). `hasFlag` ships the catalog list only -
 * a few hundred bytes, none of the SVGs. */
export const hasCountryFlag = (country: string): boolean =>
  hasFlag(country.trim().toUpperCase())

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
  const code = country.trim().toUpperCase()
  return hasFlag(code) ? <FlagImage country={code} width={width} /> : null
}
