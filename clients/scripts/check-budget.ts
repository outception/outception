// The web performance budget: the gzipped script weight of the wall route
// after `next build`, against budget.json. The root bundle is what every
// page loads; the wall figure adds the landing route's own chunks. Exit 1
// when either is over. Runs in CI after the build.
//
//   pnpm exec tsx scripts/check-budget.ts

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { gzipSync } from 'node:zlib'

const root = resolve(import.meta.dirname, '..')
const next = join(root, 'apps/web/.next')
const budget = JSON.parse(readFileSync(join(root, 'budget.json'), 'utf8')) as {
  rootGzipKb: number
  wallGzipKb: number
}

if (!existsSync(join(next, 'build-manifest.json'))) {
  console.error('check-budget: no build found; run the web build first')
  process.exit(1)
}

const manifest = JSON.parse(
  readFileSync(join(next, 'build-manifest.json'), 'utf8'),
) as { rootMainFiles: string[] }

/** The landing route's client reference manifest, wherever the router put it. */
const findLandingManifest = (dir: string): string | null => {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) {
      const found = findLandingManifest(full)
      if (found) return found
    } else if (
      name === 'page_client-reference-manifest.js' &&
      full.includes('(landing)')
    ) {
      return full
    }
  }
  return null
}

const landing = findLandingManifest(join(next, 'server/app'))
if (!landing) {
  console.error('check-budget: the landing route manifest is missing')
  process.exit(1)
}

const landingChunks = new Set(
  readFileSync(landing, 'utf8').match(/static\/chunks\/[^"'\\]+\.js/g) ?? [],
)

const gzipKb = (files: Iterable<string>): number => {
  let total = 0
  for (const file of files) {
    const path = join(next, file)
    if (!existsSync(path)) continue
    total += gzipSync(readFileSync(path)).length
  }
  return Math.round(total / 1024)
}

const rootFiles = new Set(manifest.rootMainFiles)
const wallFiles = new Set([...rootFiles, ...landingChunks])
const rootKb = gzipKb(rootFiles)
const wallKb = gzipKb(wallFiles)

const rows = [
  ['root bundle', rootFiles.size, rootKb, budget.rootGzipKb],
  ['wall route', wallFiles.size, wallKb, budget.wallGzipKb],
] as const
console.log('check-budget: gzipped script weight')
for (const [name, count, kb, limit] of rows) {
  const mark = kb <= limit ? 'ok' : 'OVER'
  console.log(
    `  ${name.padEnd(12)} ${String(count).padStart(3)} files ${String(kb).padStart(5)} KB / ${limit} KB  ${mark}`,
  )
}
if (rootKb > budget.rootGzipKb || wallKb > budget.wallGzipKb) {
  process.exit(1)
}
