import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
} from 'node:fs'
import { dirname, join } from 'node:path'
import { TARGETS, type AgentTarget } from './targets'

export const SERVER_KEY = 'outception'

export interface InstallOptions {
  home: string
  /** The skills to copy, a folder of `<name>/SKILL.md`. */
  skillsDir: string | null
  apiUrl: string
  token?: string | null
  /** Target ids; every detected agent when empty. */
  targets?: readonly string[]
  dryRun?: boolean
}

export interface InstallStep {
  target: string
  action: 'configured' | 'skills' | 'skipped'
  path: string
  note?: string
}

/** The targets present on this machine, by their marker folder. */
export const detectTargets = (home: string): AgentTarget[] =>
  TARGETS.filter((t) => existsSync(join(home, t.marker)))

const serverEntry = (apiUrl: string, token: string | null | undefined) => ({
  command: 'outception-mcp',
  args: [],
  env: {
    OUTCEPTION_API_URL: apiUrl,
    ...(token ? { OUTCEPTION_API_TOKEN: token } : {}),
  },
})

const readJson = (file: string): Record<string, unknown> => {
  if (!existsSync(file)) return {}
  try {
    const parsed: unknown = JSON.parse(readFileSync(file, 'utf8'))
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {}
  } catch {
    throw new Error(`${file} is not valid JSON; fix or move it first`)
  }
}

/** Merge the server into a JSON config, touching nothing else. */
export const mergeJsonConfig = (
  current: Record<string, unknown>,
  serversKey: string,
  entry: ReturnType<typeof serverEntry>,
): Record<string, unknown> => {
  const servers =
    current[serversKey] && typeof current[serversKey] === 'object'
      ? { ...(current[serversKey] as Record<string, unknown>) }
      : {}
  servers[SERVER_KEY] = entry
  return { ...current, [serversKey]: servers }
}

const TOML_SECTION = /\n?\[mcp_servers\.outception\][\s\S]*?(?=\n\[|$)/

/** Replace or append our section in a TOML config, touching nothing else. */
export const mergeTomlConfig = (
  current: string,
  entry: ReturnType<typeof serverEntry>,
): string => {
  const env = Object.entries(entry.env)
    .map(([k, v]) => `${k} = ${JSON.stringify(v)}`)
    .join('\n')
  const section = `\n[mcp_servers.outception]\ncommand = ${JSON.stringify(entry.command)}\nargs = []\n\n[mcp_servers.outception.env]\n${env}\n`
  const stripped = current
    .replace(TOML_SECTION, '')
    .replace(/\n?\[mcp_servers\.outception\.env\][\s\S]*?(?=\n\[|$)/, '')
  return `${stripped.replace(/\s+$/, '')}\n${section}`
}

export const install = (options: InstallOptions): InstallStep[] => {
  const wanted = options.targets?.length
    ? TARGETS.filter((t) => options.targets!.includes(t.id))
    : detectTargets(options.home)
  const entry = serverEntry(options.apiUrl, options.token)
  const steps: InstallStep[] = []
  for (const target of wanted) {
    const file = join(options.home, target.config)
    if (target.format === 'json') {
      const next = mergeJsonConfig(readJson(file), target.serversKey, entry)
      if (!options.dryRun) {
        mkdirSync(dirname(file), { recursive: true })
        writeFileSync(file, `${JSON.stringify(next, null, 2)}\n`)
      }
    } else {
      const current = existsSync(file) ? readFileSync(file, 'utf8') : ''
      if (!options.dryRun) {
        mkdirSync(dirname(file), { recursive: true })
        writeFileSync(file, mergeTomlConfig(current, entry))
      }
    }
    steps.push({ target: target.id, action: 'configured', path: file })
    if (
      target.skillsDir &&
      options.skillsDir &&
      existsSync(options.skillsDir)
    ) {
      const dest = join(options.home, target.skillsDir)
      if (!options.dryRun) {
        mkdirSync(dest, { recursive: true })
        cpSync(options.skillsDir, dest, { recursive: true })
      }
      steps.push({ target: target.id, action: 'skills', path: dest })
    } else if (target.skillsDir) {
      steps.push({
        target: target.id,
        action: 'skipped',
        path: join(options.home, target.skillsDir),
        note: 'no skills folder to copy',
      })
    }
  }
  return steps
}
