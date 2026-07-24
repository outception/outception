import { execSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import * as log from './logger'
import {
  type EntryValue,
  type NestedObject,
  type TranslationCache,
  arraysEqual,
  extractPlaceholders,
  findChangedKeys,
  findOrphanedKeys,
  findPluralPaths,
  flattenKeys,
  flattenKeysToStrings,
  getStringValue,
  prepareForLLM,
  unflattenKeys,
} from './utils'

import {
  DEFAULT_LOCALE,
  LOCALE_NAMES,
  SUPPORTED_LOCALES,
  SupportedLocale,
  type TranslatedLocale,
} from '../src/config'

const LOCALES_DIR = path.join(import.meta.dirname, '../src/locales')
const CONFIG_DIR = path.join(LOCALES_DIR, 'config')
const LOCKS_FILE = path.join(CONFIG_DIR, 'locks.json')
const CACHE_FILE = path.join(CONFIG_DIR, '.cache.json')

// Google's keyless translate endpoint — the same one the news pipeline uses as
// its primary. Real Google-Translate quality (unlike LibreTranslate, which is
// fine for full-sentence headlines but mangles short UI labels), and no API key.
const GOOGLE_URL = 'https://translate.googleapis.com/translate_a/single'

// Google's `tl` param wants a language, not a region, with a few region-specific
// exceptions. Mirrors the backend's _GOOGLE_OVERRIDE.
const GOOGLE_OVERRIDE: Record<string, string> = {
  'pt-PT': 'pt',
  'zh-Hans': 'zh-CN',
  'zh-Hant': 'zh-TW',
  nb: 'no',
}
const googleCode = (locale: string): string =>
  GOOGLE_OVERRIDE[locale] ?? locale.split('-')[0]

// Interpolation placeholders ({name}) must survive translation untouched, so
// mask them with a sentinel, then restore.
const maskPlaceholders = (s: string): { masked: string; tokens: string[] } => {
  const tokens: string[] = []
  const masked = s.replace(/\{[^}]+\}/g, (m) => {
    tokens.push(m)
    return `[[${tokens.length - 1}]]`
  })
  return { masked, tokens }
}
const restorePlaceholders = (s: string, tokens: string[]): string =>
  s.replace(/\[\[(\d+)\]\]/g, (_m, i) => tokens[Number(i)] ?? '')

async function googleTranslateOne(text: string, tl: string): Promise<string> {
  const params = new URLSearchParams({
    client: 'gtx',
    sl: 'en',
    tl,
    dt: 't',
    q: text,
  })
  const res = await fetch(`${GOOGLE_URL}?${params.toString()}`, {
    headers: { 'User-Agent': 'Mozilla/5.0 (i18n-translate)' },
  })
  if (!res.ok) throw new Error(`Google translate ${res.status} (tl=${tl})`)
  // Defensive parse: a malformed upstream response degrades to '' instead of
  // throwing (which would abort the whole CI translate run).
  const data = (await res.json()) as unknown
  const segments = Array.isArray(data) && Array.isArray(data[0]) ? data[0] : []
  return segments
    .map((s: unknown) =>
      Array.isArray(s) && typeof s[0] === 'string' ? s[0] : '',
    )
    .join('')
}

// Batch a locale's strings into one call by joining with newlines (Google keeps
// the separators, so the blob splits back to one line per string); fall back to
// per-string if the line count doesn't survive the round trip.
async function googleTranslateBatch(
  texts: string[],
  tl: string,
): Promise<string[]> {
  const blob = await googleTranslateOne(texts.join('\n'), tl)
  const parts = blob.split('\n')
  if (parts.length === texts.length) return parts
  return Promise.all(texts.map((t) => googleTranslateOne(t, tl)))
}

async function callLLM(
  targetLocale: TranslatedLocale,
  sourceStrings: Record<string, { value: string }>,
): Promise<Record<string, string>> {
  const entries = Object.entries(sourceStrings)
  const tl = googleCode(targetLocale)
  log.step(`Translating ${entries.length} strings via Google → ${tl}...`)

  const masks = entries.map(([, v]) => maskPlaceholders(v.value))
  const translated = await googleTranslateBatch(
    masks.map((m) => m.masked),
    tl,
  )

  const result: Record<string, string> = {}
  entries.forEach(([k, v], i) => {
    const restored = restorePlaceholders(translated[i] ?? '', masks[i].tokens)
    // Empty (upstream failure/blank) → keep the English source rather than
    // writing an empty string into the locale.
    result[k] = restored || v.value
  })
  return result
}

function loadCache(): TranslationCache {
  if (fs.existsSync(CACHE_FILE)) {
    return JSON.parse(fs.readFileSync(CACHE_FILE, 'utf-8')) as TranslationCache
  }
  return {}
}

function saveCache(cache: TranslationCache): void {
  fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2) + '\n')
}

function writeLocaleFile(locale: string, obj: NestedObject): void {
  const filePath = path.join(LOCALES_DIR, `${locale}.ts`)
  const content = `export default ${JSON.stringify(obj, null, 2)} as const\n`
  fs.writeFileSync(filePath, content)

  // Run oxfmt on the generated file
  try {
    execSync(`npx oxfmt --write "${filePath}"`, {
      stdio: 'pipe',
      cwd: path.join(import.meta.dirname, '..'),
    })
  } catch {
    log.warning(`Oxfmt formatting failed for ${locale}.ts`)
  }
}

async function loadExistingLocale(
  locale: SupportedLocale,
): Promise<NestedObject | null> {
  const filePath = path.join(LOCALES_DIR, `${locale}.ts`)
  if (!fs.existsSync(filePath)) return null

  try {
    const mod = await import(`${filePath}?t=${Date.now()}`)
    return (mod.default ?? null) as NestedObject | null
  } catch {
    log.warning(`Could not import ${locale}.ts`)
    return null
  }
}

/**
 * Seed cache from current source values for locales that already have translations.
 * This prevents re-translating everything on first run when an existing locale file exists.
 */
function seedCacheForLocale(
  locale: string,
  sourceKeys: Map<string, EntryValue>,
  existing: NestedObject,
  cache: TranslationCache,
): void {
  const existingKeys = flattenKeys(existing)
  const localeCache: Record<string, string> = {}

  for (const [key, value] of sourceKeys) {
    if (existingKeys.has(key)) {
      localeCache[key] = getStringValue(value)
    }
  }

  if (Object.keys(localeCache).length > 0) {
    cache[locale] = localeCache
    log.info(`Seeded cache with ${Object.keys(localeCache).length} keys`)
  }
}

async function translate(
  sourceKeys: Map<string, EntryValue>,
  pluralPaths: Set<string>,
  targetLocales: TranslatedLocale[],
  locks: Record<string, string[]>,
  cache: TranslationCache,
) {
  log.header('Outception i18n')
  log.info(
    `Source: ${log.bold(sourceKeys.size.toString())} keys in ${DEFAULT_LOCALE}.ts`,
  )
  log.info(`Targets: ${targetLocales.map((l) => log.cyan(l)).join(', ')}`)

  const stats = { translated: 0, skipped: 0, removed: 0 }

  for (const locale of targetLocales) {
    const localeName = LOCALE_NAMES[locale] || locale
    log.localeHeader(locale, localeName)

    const lockedKeys = locks[locale] ?? []
    let localeCache = cache[locale] ?? {}

    const existing = (await loadExistingLocale(locale)) ?? ({} as NestedObject)

    // Seed cache on first run if locale file exists but cache is empty
    if (
      Object.keys(localeCache).length === 0 &&
      Object.keys(existing).length > 0
    ) {
      seedCacheForLocale(locale, sourceKeys, existing, cache)
      localeCache = cache[locale] ?? {}
    }

    const changedKeys = findChangedKeys(
      sourceKeys,
      localeCache,
      existing,
    ).filter((key) => !lockedKeys.includes(key))

    const orphanedKeys = findOrphanedKeys(sourceKeys, existing)

    if (changedKeys.length === 0 && orphanedKeys.length === 0) {
      log.success('Up to date')
      stats.skipped += sourceKeys.size
      continue
    }

    if (changedKeys.length > 0) {
      log.item(
        `${changedKeys.length} key${changedKeys.length > 1 ? 's' : ''} to translate`,
      )
    }
    if (orphanedKeys.length > 0) {
      log.item(
        `${orphanedKeys.length} orphaned key${orphanedKeys.length > 1 ? 's' : ''} to remove`,
      )
    }

    let translations: Record<string, string> = {}
    if (changedKeys.length > 0) {
      const toTranslate = prepareForLLM(sourceKeys, changedKeys)
      translations = await callLLM(locale, toTranslate)
    }

    const existingFlat = flattenKeys(existing)
    const updatedFlat = new Map<string, string>()

    for (const [key, value] of existingFlat) {
      if (!orphanedKeys.includes(key) && !changedKeys.includes(key)) {
        updatedFlat.set(key, getStringValue(value))
      }
    }

    let translatedCount = 0
    for (const key of changedKeys) {
      if (translations[key]) {
        updatedFlat.set(key, translations[key])
        localeCache[key] = getStringValue(sourceKeys.get(key) as EntryValue)
        translatedCount++
        log.item(`${log.dim(key)}`)
        log.item(
          `  ${log.gray(DEFAULT_LOCALE + ':')} ${getStringValue(sourceKeys.get(key) as EntryValue)}`,
        )
        log.item(`  ${log.cyan(locale + ':')} ${translations[key]}`)
      } else {
        log.warning(`No translation received for "${key}"`)
      }
    }

    for (const key of orphanedKeys) {
      delete localeCache[key]
    }

    cache[locale] = localeCache

    const updated = unflattenKeys(updatedFlat, pluralPaths)
    writeLocaleFile(locale, updated)

    stats.translated += translatedCount
    stats.removed += orphanedKeys.length
    stats.skipped += sourceKeys.size - changedKeys.length

    log.success(`Written to ${locale}.ts`)
  }

  saveCache(cache)

  log.summary(stats)
}

function validate(
  sourceKeys: Map<string, EntryValue>,
  targetLocales: TranslatedLocale[],
  localeData: Map<SupportedLocale, NestedObject>,
): boolean {
  const errors: string[] = []

  log.blank()
  log.step('Validating translations...')

  for (const locale of targetLocales) {
    const translation = localeData.get(locale)

    if (!translation) {
      errors.push(`${locale}: File does not exist`)
      log.error(`${locale}: File does not exist`)
      continue
    }

    const translationKeys = flattenKeysToStrings(translation)

    const missingKeys: string[] = []
    for (const key of sourceKeys.keys()) {
      if (!translationKeys.has(key)) {
        missingKeys.push(key)
      }
    }

    if (missingKeys.length > 0) {
      errors.push(`${locale}: Missing ${missingKeys.length} keys`)
      log.warning(
        `${locale}: Missing ${missingKeys.length} key${missingKeys.length > 1 ? 's' : ''}`,
      )
      for (const key of missingKeys) {
        log.item(log.dim(key))
      }
    }

    const extraKeys: string[] = []
    for (const key of translationKeys.keys()) {
      if (!sourceKeys.has(key)) {
        extraKeys.push(key)
      }
    }

    if (extraKeys.length > 0) {
      errors.push(`${locale}: ${extraKeys.length} extra keys`)
      log.warning(
        `${locale}: ${extraKeys.length} extra key${extraKeys.length > 1 ? 's' : ''}`,
      )
      for (const key of extraKeys) {
        log.item(log.dim(key))
      }
    }

    const sourceStrings = flattenKeysToStrings(
      localeData.get(DEFAULT_LOCALE) as NestedObject,
    )
    const placeholderErrors: string[] = []
    for (const [key, sourceValue] of sourceStrings) {
      const translationValue = translationKeys.get(key)
      if (!translationValue) continue

      const sourcePlaceholders = extractPlaceholders(sourceValue)
      const translationPlaceholders = extractPlaceholders(translationValue)

      if (!arraysEqual(sourcePlaceholders, translationPlaceholders)) {
        placeholderErrors.push(key)
        errors.push(`${locale}.${key}: Placeholder mismatch`)
      }
    }

    if (placeholderErrors.length > 0) {
      log.warning(
        `${locale}: ${placeholderErrors.length} placeholder mismatch${placeholderErrors.length > 1 ? 'es' : ''}`,
      )
      for (const key of placeholderErrors) {
        log.item(log.dim(key))
      }
    }

    if (
      missingKeys.length === 0 &&
      extraKeys.length === 0 &&
      placeholderErrors.length === 0
    ) {
      log.success(`${locale}: All keys valid`)
    }
  }

  return errors.length === 0
}

async function main() {
  // Import source locale
  const defaultLocaleModule = await import(`../src/locales/${DEFAULT_LOCALE}`)
  const defaultLocale = defaultLocaleModule.default as NestedObject

  const locks = JSON.parse(fs.readFileSync(LOCKS_FILE, 'utf-8')) as Record<
    string,
    string[]
  >
  const cache = loadCache()

  const sourceKeys = flattenKeys(defaultLocale)
  const pluralPaths = findPluralPaths(defaultLocale as Record<string, unknown>)
  const targetLocales = SUPPORTED_LOCALES.filter(
    (l): l is TranslatedLocale => l !== DEFAULT_LOCALE,
  )

  await translate(sourceKeys, pluralPaths, targetLocales, locks, cache)

  // Load all locale data for validation
  const localeData = new Map<SupportedLocale, NestedObject>()
  localeData.set(DEFAULT_LOCALE, defaultLocale)
  for (const locale of targetLocales) {
    const data = await loadExistingLocale(locale)
    if (data) localeData.set(locale, data)
  }

  const isValid = validate(sourceKeys, targetLocales, localeData)

  if (!isValid) {
    log.blank()
    log.error('Validation failed')
    process.exit(1)
  }

  log.done('Translation and validation complete')
}

main().catch((error) => {
  log.blank()
  log.error(`Translation failed: ${error.message}`)
  process.exit(1)
})
