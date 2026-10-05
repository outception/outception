// Import directions for the clients, declared in boundaries.json: news-core
// imports no React, no React Native and no DOM; the web never imports from
// the app and the app never from the web; helpers that moved into news-core
// are not duplicated back. Exit 1 on any hit. Runs in `pnpm lint`.
//
//   pnpm exec tsx scripts/check-boundaries.ts

import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

interface Rule {
  scope: string
  why: string
  forbidImports?: string[]
  forbidGlobals?: string[]
}

interface Boundaries {
  rules: Rule[]
  duplicates?: { why: string; forbidFiles: string[] }
}

const root = resolve(import.meta.dirname, '..')
const config = JSON.parse(
  readFileSync(join(root, 'boundaries.json'), 'utf8'),
) as Boundaries

const skipDirs = new Set([
  'node_modules',
  '.next',
  'dist',
  'build',
  '.turbo',
  '.git',
  'coverage',
  'ios',
  'android',
  '.expo',
])
const sourceSuffixes = ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs']

const walk = (dir: string, out: string[] = []): string[] => {
  let entries: string[] = []
  try {
    entries = readdirSync(dir)
  } catch {
    return out
  }
  for (const name of entries) {
    if (skipDirs.has(name)) continue
    const full = join(dir, name)
    let stat
    try {
      stat = statSync(full)
    } catch {
      continue
    }
    if (stat.isDirectory()) walk(full, out)
    else if (sourceSuffixes.some((s) => name.endsWith(s))) out.push(full)
  }
  return out
}

// Comments and string literals are not code: strip them before looking for
// globals, so a doc comment may name localStorage without tripping the rule.
const stripComments = (code: string): string =>
  code.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1')

const importSpecifiers = (code: string): string[] => {
  const out: string[] = []
  const patterns = [
    /\bimport\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]/g,
    /\bexport\s+[^'"]*?\s+from\s+['"]([^'"]+)['"]/g,
    /\brequire\(\s*['"]([^'"]+)['"]\s*\)/g,
    /\bimport\(\s*['"]([^'"]+)['"]\s*\)/g,
  ]
  for (const pattern of patterns) {
    for (const match of code.matchAll(pattern)) out.push(match[1]!)
  }
  return out
}

const matchesImport = (specifier: string, forbidden: string): boolean =>
  specifier === forbidden ||
  specifier.startsWith(`${forbidden}/`) ||
  (forbidden.includes('/') && specifier.includes(forbidden))

const problems: string[] = []

for (const rule of config.rules) {
  const scope = join(root, rule.scope)
  if (!existsSync(scope)) continue
  for (const file of walk(scope)) {
    const rel = relative(root, file)
    const raw = readFileSync(file, 'utf8')
    for (const specifier of importSpecifiers(raw)) {
      for (const forbidden of rule.forbidImports ?? []) {
        if (matchesImport(specifier, forbidden)) {
          problems.push(`${rel}: imports '${specifier}' (${rule.why})`)
        }
      }
    }
    if (rule.forbidGlobals?.length) {
      const code = stripComments(raw)
      for (const name of rule.forbidGlobals) {
        const pattern = new RegExp(
          `(^|[^\\w.$'"\`])${name}\\b(?![\\w$]|\\s*:)`,
          'm',
        )
        if (pattern.test(code)) {
          problems.push(`${rel}: uses the global '${name}' (${rule.why})`)
        }
      }
    }
  }
}

for (const file of config.duplicates?.forbidFiles ?? []) {
  if (existsSync(join(root, file))) {
    problems.push(`${file}: exists (${config.duplicates!.why})`)
  }
}

if (problems.length > 0) {
  console.error(`check-boundaries: ${problems.length} problem(s)`)
  for (const problem of problems) console.error(`  ${problem}`)
  process.exit(1)
}
console.log('check-boundaries: clean')
