// Hermes ships only Intl.Collator, Intl.DateTimeFormat, Intl.NumberFormat and
// Intl.getCanonicalLocales (checked against the engine in the release build).
// Intl.RelativeTimeFormat and Intl.PluralRules THROW, so every "5m ago"
// kicker fell back to compact English in every language, and plural strings
// always took the 'other' form (wrong for Slavic, Baltic and Arabic readers).
// The web gets both natively from the browser; these polyfills give the app
// the same API, so the shared formatting code stays identical on both.
//
// Each polyfill installs itself only when the engine lacks the API (the entry
// checks should-polyfill first), so on an engine that grows native support
// these become no-ops. Order matters: RelativeTimeFormat needs Locale and
// PluralRules. Intl.getCanonicalLocales is native on Hermes, so its 215 KB
// polyfill is not loaded.
//
// Locale data is registered on demand (see ensureIntlLocaleData): the full
// set is ~1 MB of source across the two APIs, and evaluating all of it at
// launch cost every reader startup time for 46 languages they do not use.
// Metro still bundles every module (the requires are static strings), so the
// data is always present; only its evaluation is deferred to first use.
/* eslint-disable @typescript-eslint/no-require-imports -- deferred
   evaluation of bundled locale data is the whole point of this file; an
   `import` would evaluate all 46 languages at launch. */
import {
  type AcceptedLocale,
  getTranslationLocale,
  type SupportedLocale,
} from '@outception-com/i18n'

import '@formatjs/intl-locale/polyfill.js'
import '@formatjs/intl-pluralrules/polyfill.js'
import '@formatjs/intl-relativetimeformat/polyfill.js'
// English is the fallback for everything, so it is always registered.
import '@formatjs/intl-pluralrules/locale-data/en.js'
import '@formatjs/intl-relativetimeformat/locale-data/en.js'

// One entry per supported UI locale (see SUPPORTED_LOCALES in the i18n
// package): keep this in step with it. Plural rules for zh-Hans/zh-Hant come
// from the bare `zh` data (identical rules, resolved by subtag lookup).
// Filipino is `tl` in our locale list but `fil` in CLDR: RelativeTimeFormat
// data ships only as `fil`, and the formatter maps the tag (utils/news
// timeAgo) because Hermes' native getCanonicalLocales is not guaranteed to
// apply the CLDR alias; plural data is loaded under both so either resolves.
const LOADERS: Record<Exclude<SupportedLocale, 'en'>, () => void> = {
  nl: () => {
    require('@formatjs/intl-pluralrules/locale-data/nl.js')
    require('@formatjs/intl-relativetimeformat/locale-data/nl.js')
  },
  fr: () => {
    require('@formatjs/intl-pluralrules/locale-data/fr.js')
    require('@formatjs/intl-relativetimeformat/locale-data/fr.js')
  },
  sv: () => {
    require('@formatjs/intl-pluralrules/locale-data/sv.js')
    require('@formatjs/intl-relativetimeformat/locale-data/sv.js')
  },
  es: () => {
    require('@formatjs/intl-pluralrules/locale-data/es.js')
    require('@formatjs/intl-relativetimeformat/locale-data/es.js')
  },
  de: () => {
    require('@formatjs/intl-pluralrules/locale-data/de.js')
    require('@formatjs/intl-relativetimeformat/locale-data/de.js')
  },
  hu: () => {
    require('@formatjs/intl-pluralrules/locale-data/hu.js')
    require('@formatjs/intl-relativetimeformat/locale-data/hu.js')
  },
  it: () => {
    require('@formatjs/intl-pluralrules/locale-data/it.js')
    require('@formatjs/intl-relativetimeformat/locale-data/it.js')
  },
  pt: () => {
    require('@formatjs/intl-pluralrules/locale-data/pt.js')
    require('@formatjs/intl-relativetimeformat/locale-data/pt.js')
  },
  'pt-PT': () => {
    require('@formatjs/intl-pluralrules/locale-data/pt-PT.js')
    require('@formatjs/intl-relativetimeformat/locale-data/pt-PT.js')
  },
  ko: () => {
    require('@formatjs/intl-pluralrules/locale-data/ko.js')
    require('@formatjs/intl-relativetimeformat/locale-data/ko.js')
  },
  ja: () => {
    require('@formatjs/intl-pluralrules/locale-data/ja.js')
    require('@formatjs/intl-relativetimeformat/locale-data/ja.js')
  },
  tr: () => {
    require('@formatjs/intl-pluralrules/locale-data/tr.js')
    require('@formatjs/intl-relativetimeformat/locale-data/tr.js')
  },
  pl: () => {
    require('@formatjs/intl-pluralrules/locale-data/pl.js')
    require('@formatjs/intl-relativetimeformat/locale-data/pl.js')
  },
  ru: () => {
    require('@formatjs/intl-pluralrules/locale-data/ru.js')
    require('@formatjs/intl-relativetimeformat/locale-data/ru.js')
  },
  uk: () => {
    require('@formatjs/intl-pluralrules/locale-data/uk.js')
    require('@formatjs/intl-relativetimeformat/locale-data/uk.js')
  },
  ar: () => {
    require('@formatjs/intl-pluralrules/locale-data/ar.js')
    require('@formatjs/intl-relativetimeformat/locale-data/ar.js')
  },
  he: () => {
    require('@formatjs/intl-pluralrules/locale-data/he.js')
    require('@formatjs/intl-relativetimeformat/locale-data/he.js')
  },
  fa: () => {
    require('@formatjs/intl-pluralrules/locale-data/fa.js')
    require('@formatjs/intl-relativetimeformat/locale-data/fa.js')
  },
  hi: () => {
    require('@formatjs/intl-pluralrules/locale-data/hi.js')
    require('@formatjs/intl-relativetimeformat/locale-data/hi.js')
  },
  bn: () => {
    require('@formatjs/intl-pluralrules/locale-data/bn.js')
    require('@formatjs/intl-relativetimeformat/locale-data/bn.js')
  },
  ur: () => {
    require('@formatjs/intl-pluralrules/locale-data/ur.js')
    require('@formatjs/intl-relativetimeformat/locale-data/ur.js')
  },
  'zh-Hans': () => {
    require('@formatjs/intl-pluralrules/locale-data/zh.js')
    require('@formatjs/intl-relativetimeformat/locale-data/zh-Hans.js')
  },
  'zh-Hant': () => {
    require('@formatjs/intl-pluralrules/locale-data/zh.js')
    require('@formatjs/intl-relativetimeformat/locale-data/zh-Hant.js')
  },
  id: () => {
    require('@formatjs/intl-pluralrules/locale-data/id.js')
    require('@formatjs/intl-relativetimeformat/locale-data/id.js')
  },
  ms: () => {
    require('@formatjs/intl-pluralrules/locale-data/ms.js')
    require('@formatjs/intl-relativetimeformat/locale-data/ms.js')
  },
  tl: () => {
    require('@formatjs/intl-pluralrules/locale-data/tl.js')
    require('@formatjs/intl-pluralrules/locale-data/fil.js')
    require('@formatjs/intl-relativetimeformat/locale-data/fil.js')
  },
  vi: () => {
    require('@formatjs/intl-pluralrules/locale-data/vi.js')
    require('@formatjs/intl-relativetimeformat/locale-data/vi.js')
  },
  th: () => {
    require('@formatjs/intl-pluralrules/locale-data/th.js')
    require('@formatjs/intl-relativetimeformat/locale-data/th.js')
  },
  cs: () => {
    require('@formatjs/intl-pluralrules/locale-data/cs.js')
    require('@formatjs/intl-relativetimeformat/locale-data/cs.js')
  },
  sk: () => {
    require('@formatjs/intl-pluralrules/locale-data/sk.js')
    require('@formatjs/intl-relativetimeformat/locale-data/sk.js')
  },
  sl: () => {
    require('@formatjs/intl-pluralrules/locale-data/sl.js')
    require('@formatjs/intl-relativetimeformat/locale-data/sl.js')
  },
  ro: () => {
    require('@formatjs/intl-pluralrules/locale-data/ro.js')
    require('@formatjs/intl-relativetimeformat/locale-data/ro.js')
  },
  bg: () => {
    require('@formatjs/intl-pluralrules/locale-data/bg.js')
    require('@formatjs/intl-relativetimeformat/locale-data/bg.js')
  },
  sr: () => {
    require('@formatjs/intl-pluralrules/locale-data/sr.js')
    require('@formatjs/intl-relativetimeformat/locale-data/sr.js')
  },
  sq: () => {
    require('@formatjs/intl-pluralrules/locale-data/sq.js')
    require('@formatjs/intl-relativetimeformat/locale-data/sq.js')
  },
  el: () => {
    require('@formatjs/intl-pluralrules/locale-data/el.js')
    require('@formatjs/intl-relativetimeformat/locale-data/el.js')
  },
  da: () => {
    require('@formatjs/intl-pluralrules/locale-data/da.js')
    require('@formatjs/intl-relativetimeformat/locale-data/da.js')
  },
  nb: () => {
    require('@formatjs/intl-pluralrules/locale-data/nb.js')
    require('@formatjs/intl-relativetimeformat/locale-data/nb.js')
  },
  fi: () => {
    require('@formatjs/intl-pluralrules/locale-data/fi.js')
    require('@formatjs/intl-relativetimeformat/locale-data/fi.js')
  },
  et: () => {
    require('@formatjs/intl-pluralrules/locale-data/et.js')
    require('@formatjs/intl-relativetimeformat/locale-data/et.js')
  },
  lv: () => {
    require('@formatjs/intl-pluralrules/locale-data/lv.js')
    require('@formatjs/intl-relativetimeformat/locale-data/lv.js')
  },
  lt: () => {
    require('@formatjs/intl-pluralrules/locale-data/lt.js')
    require('@formatjs/intl-relativetimeformat/locale-data/lt.js')
  },
  ga: () => {
    require('@formatjs/intl-pluralrules/locale-data/ga.js')
    require('@formatjs/intl-relativetimeformat/locale-data/ga.js')
  },
  ca: () => {
    require('@formatjs/intl-pluralrules/locale-data/ca.js')
    require('@formatjs/intl-relativetimeformat/locale-data/ca.js')
  },
  eu: () => {
    require('@formatjs/intl-pluralrules/locale-data/eu.js')
    require('@formatjs/intl-relativetimeformat/locale-data/eu.js')
  },
  hr: () => {
    require('@formatjs/intl-pluralrules/locale-data/hr.js')
    require('@formatjs/intl-relativetimeformat/locale-data/hr.js')
  },
}

const loaded = new Set<SupportedLocale>(['en'])

/** Register the plural and relative-time data for `locale` with the
 * polyfills. Idempotent and synchronous (the data modules are in the bundle),
 * so the locale provider calls it during render before any consumer builds a
 * formatter for that locale. A regional variant (`de-AT`) loads its base
 * language's data; the formatters resolve to it by subtag lookup. Against a
 * native implementation the data modules are no-ops. */
export const ensureIntlLocaleData = (locale: AcceptedLocale): void => {
  const base = getTranslationLocale(locale)
  if (loaded.has(base)) return
  loaded.add(base)
  if (base !== 'en') LOADERS[base]()
}
