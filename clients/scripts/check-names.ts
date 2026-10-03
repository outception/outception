// The naming rule for the clients: no third party is named outside the
// allowlisted paths. Reads docs/naming/denylist.txt and scans the client
// tree; reports every hit. Exit 1 only with --strict.
//
//   node --experimental-strip-types scripts/check-names.ts [--strict]

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const repo = resolve(root, '..')
const denylist = readFileSync(join(repo, 'docs/naming/denylist.txt'), 'utf8')
  .split('\n')
  .map((line) => line.split('#')[0].trim())
  .filter(Boolean)

const allowed = ['scripts/check-names.ts', 'pnpm-lock.yaml', 'package.json']
const skipDirs = new Set(['node_modules', '.next', 'dist', 'build', '.turbo', '.git', 'coverage', 'ios', 'android'])
const skipSuffixes = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.woff', '.woff2', '.ttf', '.otf', '.pdf', '.zip', '.svg', '.mp4', '.lock']

const escape = (name: string) => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const pattern = new RegExp(
  `(?<![A-Za-z0-9_])(?:${[...denylist].sort((a, b) => b.length - a.length).map(escape).join('|')})(?![A-Za-z0-9_])`,
  'i',
)

function* walk(dir: string): Generator<string> {
  for (const entry of readdirSync(dir)) {
    if (skipDirs.has(entry)) continue
    const path = join(dir, entry)
    const stats = statSync(path)
    if (stats.isDirectory()) yield* walk(path)
    else if (!skipSuffixes.some((suffix) => entry.endsWith(suffix))) yield path
  }
}

const strict = process.argv.includes('--strict')
let hits = 0
for (const path of walk(root)) {
  const rel = relative(root, path).split('\\').join('/')
  if (allowed.some((prefix) => rel.startsWith(prefix) || rel.endsWith('/' + prefix))) continue
  let text: string
  try {
    text = readFileSync(path, 'utf8')
  } catch {
    continue
  }
  text.split('\n').forEach((line, index) => {
    const match = pattern.exec(line)
    if (match) {
      hits += 1
      console.log(`${rel}:${index + 1}: names '${match[0]}'`)
    }
  })
}
if (hits) {
  console.log(`\n${hits} hit(s) outside the allowlisted paths.`)
  process.exit(strict ? 1 : 0)
}
console.log('OK: no third party named outside the allowlisted paths.')
