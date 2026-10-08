/**
 * Every `t('...')` key used in web and app exists in `en.ts`, and no `en.ts`
 * key is unused. English is the only locale, so this is the whole check.
 *
 *   pnpm --filter @outception-com/i18n check-keys
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { flattenKeys, type NestedObject } from './utils'

const ROOT = path.resolve(import.meta.dirname, '../../..')
const SOURCES = ['apps/web/src', 'apps/app', 'packages/news-core/src']
const SKIP = new Set([
  'node_modules',
  'dist',
  '.next',
  'android',
  'ios',
  'coverage',
])

// t('a.b.c'), tr.a.b.c, getTranslations().a.b.c, and the i18n helpers that
// take a key string.
const KEY_CALL = /\b(?:t|tr|translate)\(\s*['"`]([a-zA-Z0-9_.-]+)['"`]/g
const KEY_PATH =
  /\b(?:tr|translations|strings)\.([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)/g

function walk(dir: string, out: string[]): void {
  for (const entry of readdirSync(dir)) {
    if (SKIP.has(entry)) continue
    const full = path.join(dir, entry)
    if (statSync(full).isDirectory()) walk(full, out)
    else if (/\.(ts|tsx)$/.test(entry) && !/\.test\.tsx?$/.test(entry))
      out.push(full)
  }
}

async function main(): Promise<number> {
  const en = (await import('../src/locales/en')).default as NestedObject
  const known = new Set(flattenKeys(en).keys())
  const used = new Set<string>()
  const files: string[] = []
  for (const source of SOURCES) {
    const dir = path.join(ROOT, source)
    try {
      statSync(dir)
    } catch {
      continue
    }
    walk(dir, files)
  }
  for (const file of files) {
    const text = readFileSync(file, 'utf8')
    for (const match of text.matchAll(KEY_CALL)) used.add(match[1])
    for (const match of text.matchAll(KEY_PATH)) {
      const key = match[1]
      // The longest known prefix is the key; the rest is property access.
      const parts = key.split('.')
      for (let i = parts.length; i > 0; i -= 1) {
        const candidate = parts.slice(0, i).join('.')
        if (known.has(candidate)) {
          used.add(candidate)
          break
        }
      }
    }
  }
  const missing = [...used].filter((key) => !known.has(key)).sort()
  if (missing.length > 0) {
    console.error(`${missing.length} key(s) used but missing from en.ts:`)
    for (const key of missing) console.error(`  ${key}`)
    return 1
  }
  console.log(
    `${known.size} keys in en.ts, ${used.size} referenced; nothing missing.`,
  )
  return 0
}

process.exit(await main())
