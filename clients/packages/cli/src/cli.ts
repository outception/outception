import { defaultSkillsDir } from '@outception-com/mcp'
import { homedir } from 'node:os'
import { detectTargets, install } from './install'
import { TARGETS } from './targets'

const usage = `outception: install the tools and skills into the coding agents on this machine

  outception install [--target <id>]... [--api-url <url>] [--token <token>] [--dry-run]
  outception targets
  outception doctor [--api-url <url>]

The API URL defaults to OUTCEPTION_API_URL or the public API; a token is
required for anything but a local server.
`

const flag = (argv: string[], name: string): string | undefined => {
  const i = argv.indexOf(name)
  return i >= 0 ? argv[i + 1] : undefined
}

const flags = (argv: string[], name: string): string[] =>
  argv.flatMap((arg, i) => (arg === name && argv[i + 1] ? [argv[i + 1]!] : []))

const main = async (argv: string[]): Promise<number> => {
  const [command] = argv
  const apiUrl =
    flag(argv, '--api-url') ??
    process.env.OUTCEPTION_API_URL ??
    'https://api.outception.com'
  if (command === 'targets') {
    const found = new Set(detectTargets(homedir()).map((t) => t.id))
    for (const target of TARGETS) {
      process.stdout.write(
        `${found.has(target.id) ? 'found   ' : 'absent  '}${target.id}\t${target.label}\n`,
      )
    }
    return 0
  }
  if (command === 'install') {
    const steps = install({
      home: homedir(),
      skillsDir: defaultSkillsDir(),
      apiUrl,
      token: flag(argv, '--token') ?? process.env.OUTCEPTION_API_TOKEN,
      targets: flags(argv, '--target'),
      dryRun: argv.includes('--dry-run'),
    })
    if (steps.length === 0) {
      process.stdout.write(
        'No coding agent found on this machine; nothing installed.\n',
      )
      return 1
    }
    for (const step of steps) {
      process.stdout.write(
        `${step.action.padEnd(11)} ${step.target}\t${step.path}${step.note ? `  (${step.note})` : ''}\n`,
      )
    }
    return 0
  }
  if (command === 'doctor') {
    try {
      const response = await fetch(`${apiUrl.replace(/\/+$/, '')}/health`)
      process.stdout.write(`${apiUrl}: ${response.status}\n`)
      return response.ok ? 0 : 1
    } catch (error) {
      process.stdout.write(
        `${apiUrl}: unreachable (${error instanceof Error ? error.message : String(error)})\n`,
      )
      return 1
    }
  }
  process.stdout.write(usage)
  return command === undefined || command === '--help' || command === 'help'
    ? 0
    : 1
}

main(process.argv.slice(2)).then(
  (code) => process.exit(code),
  (error: unknown) => {
    process.stderr.write(
      `${error instanceof Error ? error.message : String(error)}\n`,
    )
    process.exit(1)
  },
)
