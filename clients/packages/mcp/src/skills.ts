import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export interface Skill {
  name: string
  description: string
  /** The whole file, front matter included. */
  text: string
  path: string
}

const FRONT_MATTER = /^---\n([\s\S]*?)\n---\n?/

const field = (block: string, key: string): string | null => {
  const match = new RegExp(`^${key}:\\s*(.+)$`, 'm').exec(block)
  return match?.[1]?.trim().replace(/^["']|["']$/g, '') ?? null
}

/** Every skill file (SKILL.md in a folder) under `dir`, by folder name. */
export const loadSkills = (dir: string): Skill[] => {
  if (!existsSync(dir)) return []
  const out: Skill[] = []
  for (const name of readdirSync(dir).sort()) {
    const file = join(dir, name, 'SKILL.md')
    if (!existsSync(file) || !statSync(file).isFile()) continue
    const text = readFileSync(file, 'utf8')
    const block = FRONT_MATTER.exec(text)?.[1] ?? ''
    out.push({
      name: field(block, 'name') ?? name,
      description: field(block, 'description') ?? '',
      text,
      path: file,
    })
  }
  return out
}

/** Where the skills live: the operator's choice, or the folder shipped with
 * the package (the one copy in the tree). */
export const defaultSkillsDir = (
  env: NodeJS.ProcessEnv = process.env,
): string => {
  if (env.OUTCEPTION_SKILLS_DIR) return env.OUTCEPTION_SKILLS_DIR
  const here = dirname(fileURLToPath(import.meta.url))
  return resolve(here, '..', 'skills')
}
