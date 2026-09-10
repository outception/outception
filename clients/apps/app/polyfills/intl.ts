// Hermes ships only Intl.Collator, Intl.DateTimeFormat, Intl.NumberFormat and
// Intl.getCanonicalLocales (checked against the engine in the release build).
// Intl.RelativeTimeFormat and Intl.PluralRules THROW, so every "5m ago"
// kicker fell back to compact English and plural strings always took the
// 'other' form. The web gets both natively from the browser; these polyfills
// give the app the same API, so the shared formatting code stays identical on
// both.
//
// Each polyfill installs itself only when the engine lacks the API (the entry
// checks should-polyfill first), so on an engine that grows native support
// these become no-ops. Order matters: RelativeTimeFormat needs Locale and
// PluralRules. Intl.getCanonicalLocales is native on Hermes, so its 215 KB
// polyfill is not loaded.
//
// English is the only locale, so its data is imported directly and there is
// nothing to defer.
import '@formatjs/intl-locale/polyfill.js'
import '@formatjs/intl-pluralrules/polyfill.js'
import '@formatjs/intl-relativetimeformat/polyfill.js'
import '@formatjs/intl-pluralrules/locale-data/en.js'
import '@formatjs/intl-relativetimeformat/locale-data/en.js'
