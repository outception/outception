import { execFileSync } from 'node:child_process'
import { join } from 'node:path'

/**
 * Node has native Intl, so importing the polyfills in this process is a no-op
 * and the formatjs packages are ESM that jest's transform does not parse. To
 * test what the app gets on Hermes, a child Node process strips the APIs the
 * engine lacks, loads every polyfill and locale-data module the app
 * references (parsed straight from polyfills/intl.ts, so the list under test
 * is the shipped one), and formats a few probes.
 */
const probe = (script: string): Record<string, string> => {
  const source = `
    import { readFileSync } from 'node:fs'
    delete Intl.RelativeTimeFormat
    delete Intl.PluralRules
    delete Intl.Locale
    const src = readFileSync(${JSON.stringify(join(__dirname, 'intl.ts'))}, 'utf8')
    const specs = [...src.matchAll(/(?:^import|require\\()\\s*'(@formatjs[^']+)'/gm)].map((m) => m[1])
    // Polyfills first (they precede every data module in the file), then data.
    for (const spec of specs) await import(spec)
    const out = {}
    ${script}
    process.stdout.write(JSON.stringify(out))
  `
  const stdout = execFileSync(
    process.execPath,
    ['--input-type=module', '--eval', source],
    { cwd: __dirname, encoding: 'utf8' },
  )
  return JSON.parse(stdout) as Record<string, string>
}

describe('Intl polyfills for Hermes', () => {
  it('installs RelativeTimeFormat with our locales', () => {
    const out = probe(`
      out.hr = new Intl.RelativeTimeFormat('hr', { style: 'narrow', numeric: 'auto' }).format(-39, 'minute')
      out.de = new Intl.RelativeTimeFormat('de', { numeric: 'auto' }).format(-1, 'day')
      out.ja = new Intl.RelativeTimeFormat('ja', { style: 'narrow' }).format(-2, 'hour')
      out.zh = new Intl.RelativeTimeFormat('zh-Hant', { style: 'narrow' }).format(-3, 'day')
    `)
    expect(out.hr).toBe('prije 39 min')
    expect(out.de).toBe('gestern')
    expect(out.ja).toBe('2時間前')
    expect(out.zh).toContain('天前')
  })

  it('serves Filipino under the tag the formatter maps to', () => {
    // utils/news timeAgo maps our `tl` to CLDR `fil` before constructing.
    const out = probe(`
      out.fil = new Intl.RelativeTimeFormat('fil', { style: 'narrow' }).format(-5, 'minute')
      out.tlPlural = new Intl.PluralRules('tl').select(1)
    `)
    expect(out.fil).toContain('nakalipas')
    expect(out.tlPlural).toBe('one')
  })

  it('installs PluralRules with CLDR categories, not just other', () => {
    const out = probe(`
      out.hr = new Intl.PluralRules('hr').select(2)
      out.ru = new Intl.PluralRules('ru').select(5)
      out.ar = new Intl.PluralRules('ar').select(0)
      out.zh = new Intl.PluralRules('zh-Hant').select(3)
    `)
    expect(out.hr).toBe('few')
    expect(out.ru).toBe('many')
    expect(out.ar).toBe('zero')
    // Chinese variants resolve to the bare zh data.
    expect(out.zh).toBe('other')
  })
})
