// Specs carry two markers:
//
//   <!-- doc-covers: path other/path -->
//   <!-- doc-verified: <commit> -->
//
// A doc is fresh while nothing under its covered paths changed since the
// commit it was verified at. --check fails on a stale doc; without it the
// stale docs are listed. Re-verify by reading the doc against the code and
// moving the marker to the current commit. Runs under Node 24 with native
// type stripping:
//
//   node scripts/check-doc-freshness.mts [--check]

import { execFileSync } from 'node:child_process'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const check = process.argv.includes('--check')

const git = (...args: string[]): string =>
  execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim()

const docs = (dir: string, out: string[] = []): string[] => {
  for (const name of readdirSync(dir)) {
    if (name === 'node_modules' || name.startsWith('.')) continue
    const full = join(dir, name)
    if (statSync(full).isDirectory()) docs(full, out)
    else if (name.endsWith('.md')) out.push(full)
  }
  return out
}

interface Spec {
  file: string
  covers: string[]
  verified: string
}

const specs: Spec[] = []
for (const file of [...docs(join(root, 'docs')), ...docs(root).filter((f) => !f.includes('/docs/'))]) {
  const text = readFileSync(file, 'utf8')
  const covers = /<!--\s*doc-covers:\s*([^>]+?)\s*-->/.exec(text)
  const verified = /<!--\s*doc-verified:\s*([0-9a-f]{7,40})\s*-->/.exec(text)
  if (!covers || !verified) continue
  specs.push({
    file: relative(root, file),
    covers: covers[1]!.split(/\s+/).filter(Boolean),
    verified: verified[1]!,
  })
}

let stale = 0
for (const spec of specs) {
  let changed: string[]
  try {
    git('cat-file', '-e', `${spec.verified}^{commit}`)
    changed = git('diff', '--name-only', spec.verified, 'HEAD', '--', ...spec.covers)
      .split('\n')
      .filter(Boolean)
  } catch {
    console.log(`${spec.file}: verified at ${spec.verified}, which this clone does not have`)
    stale += 1
    continue
  }
  if (changed.length === 0) {
    console.log(`${spec.file}: fresh (${spec.verified})`)
  } else {
    stale += 1
    console.log(`${spec.file}: stale since ${spec.verified}; changed: ${changed.slice(0, 6).join(', ')}${changed.length > 6 ? ', ...' : ''}`)
  }
}
console.log(`${specs.length} spec(s), ${stale} stale`)
if (check && stale > 0) process.exit(1)
