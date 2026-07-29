/**
 * Remove keys from every target locale that no longer exist in `en.ts`.
 *
 * `translate.ts` already does this, but only as part of a full translation run,
 * which needs network access and re-translates every changed string. Deleting a
 * key from `en.ts` therefore left its translations sitting in all 46 locale
 * files until the CI job next ran — dead weight bundled into both the web build
 * and the mobile JS bundle, and invisible at runtime because `deepMerge` only
 * ever reads keys that `en.ts` still defines.
 *
 * This does the removal half on its own: no API calls, no re-translation.
 */
import { execSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import * as log from './logger'
import {
  type NestedObject,
  findOrphanedKeys,
  findPluralPaths,
  flattenKeys,
  flattenKeysToStrings,
  unflattenKeys,
} from './utils'

import {
  DEFAULT_LOCALE,
  LOCALE_NAMES,
  SUPPORTED_LOCALES,
  type TranslatedLocale,
} from '../src/config'

const LOCALES_DIR = path.join(import.meta.dirname, '../src/locales')

function writeLocaleFile(locale: string, obj: NestedObject): void {
  const filePath = path.join(LOCALES_DIR, `${locale}.ts`)
  const content = `export default ${JSON.stringify(obj, null, 2)} as const\n`
  fs.writeFileSync(filePath, content)

  // Same as translate.ts: raw JSON.stringify output is not repo style, so every
  // rewritten file would fail `oxfmt --check` and break lint.
  try {
    execSync(`npx oxfmt --write "${filePath}"`, {
      stdio: 'pipe',
      cwd: path.join(import.meta.dirname, '..'),
    })
  } catch {
    log.warning(`Oxfmt formatting failed for ${locale}.ts`)
  }
}

/**
 * The pure half of a prune: drop `orphaned` from `locale` and rebuild the tree.
 *
 * Exported so the regression tests exercise THIS code rather than a copy —
 * `flattenKeys` deliberately drops `_mode: 'plural'` markers and
 * `unflattenKeys` only restores them for the paths it is handed, so omitting
 * `findPluralPaths` here would silently strip every plural marker and make
 * `t()` call `.replace()` on a raw object in all 46 locales.
 */
export function pruneLocaleObject(
  sourceKeys: Map<string, unknown>,
  locale: NestedObject,
  orphaned: string[],
): NestedObject {
  void sourceKeys
  const pluralPaths = findPluralPaths(locale)
  const kept = flattenKeysToStrings(locale)
  for (const key of orphaned) kept.delete(key)
  return unflattenKeys(kept, pluralPaths)
}

async function loadLocale(locale: string): Promise<NestedObject | null> {
  try {
    const mod = await import(`../src/locales/${locale}`)
    return mod.default as NestedObject
  } catch {
    return null
  }
}

async function prune() {
  const defaultLocaleModule = await import(`../src/locales/${DEFAULT_LOCALE}`)
  const sourceKeys = flattenKeys(defaultLocaleModule.default as NestedObject)

  const targetLocales = SUPPORTED_LOCALES.filter(
    (l): l is TranslatedLocale => l !== DEFAULT_LOCALE,
  )

  log.header('Outception i18n Prune')
  log.info(
    `Source: ${log.bold(sourceKeys.size.toString())} keys in ${DEFAULT_LOCALE}.ts`,
  )

  let totalRemoved = 0
  let filesChanged = 0

  for (const locale of targetLocales) {
    const existing = await loadLocale(locale)
    if (!existing) {
      log.warning(`${locale}: file does not exist, skipping`)
      continue
    }

    const orphaned = findOrphanedKeys(sourceKeys, existing)
    if (orphaned.length === 0) continue

    writeLocaleFile(locale, pruneLocaleObject(sourceKeys, existing, orphaned))
    totalRemoved += orphaned.length
    filesChanged += 1
    log.localeHeader(locale, LOCALE_NAMES[locale] || locale)
    log.item(`removed ${orphaned.length} orphaned keys`)
  }

  if (totalRemoved === 0) {
    log.success('No orphaned keys')
    return
  }
  log.success(
    `Removed ${totalRemoved} orphaned keys across ${filesChanged} locales`,
  )
}

prune().catch((error) => {
  log.error(String(error))
  process.exit(1)
})
