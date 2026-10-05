import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  detectTargets,
  install,
  mergeJsonConfig,
  mergeTomlConfig,
} from './install'
import { TARGETS } from './targets'

const home = () => {
  const dir = mkdtempSync(join(tmpdir(), 'home-'))
  mkdirSync(join(dir, '.cursor'), { recursive: true })
  mkdirSync(join(dir, '.codex'), { recursive: true })
  return dir
}

const skills = () => {
  const dir = mkdtempSync(join(tmpdir(), 'skills-'))
  mkdirSync(join(dir, 'outception-news'))
  writeFileSync(
    join(dir, 'outception-news', 'SKILL.md'),
    '---\nname: outception-news\n---\n',
  )
  return dir
}

describe('install', () => {
  it('detects agents by their folders', () => {
    const h = home()
    expect(
      detectTargets(h)
        .map((t) => t.id)
        .sort(),
    ).toEqual(['codex', 'cursor'])
    expect(TARGETS.every((t) => t.config && t.marker)).toBe(true)
  })

  it('merges into a JSON config without touching other servers', () => {
    const merged = mergeJsonConfig(
      { theme: 'dark', mcpServers: { other: { command: 'x' } } },
      'mcpServers',
      {
        command: 'outception-mcp',
        args: [],
        env: { OUTCEPTION_API_URL: 'http://127.0.0.1:8000' },
      },
    )
    expect(merged).toEqual({
      theme: 'dark',
      mcpServers: {
        other: { command: 'x' },
        outception: {
          command: 'outception-mcp',
          args: [],
          env: { OUTCEPTION_API_URL: 'http://127.0.0.1:8000' },
        },
      },
    })
  })

  it('replaces its own TOML section and keeps the rest', () => {
    const entry = {
      command: 'outception-mcp',
      args: [],
      env: { OUTCEPTION_API_URL: 'u', OUTCEPTION_API_TOKEN: 't' },
    }
    const once = mergeTomlConfig(
      'model = "x"\n\n[mcp_servers.other]\ncommand = "y"\n',
      entry,
    )
    const twice = mergeTomlConfig(once, {
      ...entry,
      env: { OUTCEPTION_API_URL: 'v' },
    })
    expect(twice).toContain('model = "x"')
    expect(twice).toContain('[mcp_servers.other]')
    expect(twice.match(/\[mcp_servers\.outception\]/g)).toHaveLength(1)
    expect(twice).toContain('OUTCEPTION_API_URL = "v"')
    expect(twice).not.toContain('OUTCEPTION_API_TOKEN')
  })

  it('writes configs and copies skills for the detected agents', () => {
    const h = home()
    const steps = install({
      home: h,
      skillsDir: skills(),
      apiUrl: 'http://127.0.0.1:8000',
    })
    expect(steps.map((s) => `${s.target}:${s.action}`).sort()).toEqual([
      'codex:configured',
      'codex:skills',
      'cursor:configured',
    ])
    const cursor = JSON.parse(
      readFileSync(join(h, '.cursor/mcp.json'), 'utf8'),
    ) as {
      mcpServers: Record<string, { command: string }>
    }
    expect(cursor.mcpServers.outception?.command).toBe('outception-mcp')
    expect(existsSync(join(h, '.codex/skills/outception-news/SKILL.md'))).toBe(
      true,
    )
    expect(readFileSync(join(h, '.codex/config.toml'), 'utf8')).toContain(
      '[mcp_servers.outception]',
    )
  })

  it('a dry run writes nothing', () => {
    const h = home()
    const steps = install({
      home: h,
      skillsDir: null,
      apiUrl: 'http://127.0.0.1:8000',
      dryRun: true,
    })
    expect(steps.length).toBeGreaterThan(0)
    expect(existsSync(join(h, '.cursor/mcp.json'))).toBe(false)
  })
})
