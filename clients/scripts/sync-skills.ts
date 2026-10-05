// The skills live once, at the repository root under skills/. The MCP
// package carries a copy so an installed server can serve them without the
// tree. This script refreshes that copy, and with --check fails when the
// two differ. Runs in the skills sync workflow.
//
//   pnpm exec tsx scripts/sync-skills.ts [--check]

import {
  cpSync,
  existsSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
} from 'node:fs'
import { join, resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const source = resolve(root, '..', 'skills')
const target = join(root, 'packages', 'mcp', 'skills')
const check = process.argv.includes('--check')

const snapshot = (dir: string): Map<string, string> => {
  const out = new Map<string, string>()
  if (!existsSync(dir)) return out
  const walk = (current: string, prefix: string) => {
    for (const name of readdirSync(current).sort()) {
      const full = join(current, name)
      const rel = prefix ? `${prefix}/${name}` : name
      if (statSync(full).isDirectory()) walk(full, rel)
      else out.set(rel, readFileSync(full, 'utf8'))
    }
  }
  walk(dir, '')
  return out
}

const same = (a: Map<string, string>, b: Map<string, string>): boolean =>
  a.size === b.size && [...a].every(([k, v]) => b.get(k) === v)

if (!existsSync(source)) {
  console.error(`sync-skills: no skills folder at ${source}`)
  process.exit(1)
}
if (check) {
  if (same(snapshot(source), snapshot(target))) {
    console.log('sync-skills: the bundled copy matches skills/')
  } else {
    console.error(
      'sync-skills: packages/mcp/skills differs from skills/; run pnpm exec tsx scripts/sync-skills.ts',
    )
    process.exit(1)
  }
} else {
  rmSync(target, { recursive: true, force: true })
  cpSync(source, target, { recursive: true })
  console.log(
    `sync-skills: copied ${snapshot(target).size} file(s) into packages/mcp/skills`,
  )
}
