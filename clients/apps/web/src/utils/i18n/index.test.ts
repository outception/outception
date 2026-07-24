import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@outception-com/i18n', () => {
  const SUPPORTED_LOCALES = ['en', 'fr', 'nl', 'ja'] as const
  return {
    DEFAULT_LOCALE: 'en',
    SUPPORTED_LOCALES,
    isAcceptedLocale: (value: string) => {
      const language = value.split('-')[0].toLowerCase()
      return (SUPPORTED_LOCALES as readonly string[]).includes(language)
    },
  }
})

// Route header/cookie lookups by name so accept-language, cf-ipcountry and the
// locale/geo cookies can be set independently.
const requestHeaders = new Map<string, string>()
const requestCookies = new Map<string, string>()
vi.mock('next/headers', () => ({
  headers: () => ({ get: (name: string) => requestHeaders.get(name) ?? null }),
  cookies: () => ({
    get: (name: string) => {
      const value = requestCookies.get(name)
      return value ? { value } : undefined
    },
  }),
}))

import {
  getBrowserLocale,
  parseAcceptLanguageHeader,
  resolveLocale,
} from './index'

describe('parseAcceptLanguageHeader', () => {
  it('returns [] for null / empty', () => {
    expect(parseAcceptLanguageHeader(null)).toEqual([])
    expect(parseAcceptLanguageHeader('')).toEqual([])
  })

  it('sorts entries by descending q', () => {
    expect(parseAcceptLanguageHeader('fr;q=0.3,nl;q=0.9,en-CA;q=0.7')).toEqual([
      { code: 'nl', q: 0.9 },
      { code: 'en-CA', q: 0.7 },
      { code: 'fr', q: 0.3 },
    ])
  })
})

describe('getBrowserLocale', () => {
  it('returns the highest-priority supported locale', () => {
    expect(getBrowserLocale('fr;q=0.3,nl;q=0.9')).toBe('nl')
  })

  it('normalizes a region variant to its supported primary language', () => {
    expect(getBrowserLocale('fr-CA,en;q=0.8')).toBe('fr')
  })

  it('skips unsupported codes', () => {
    expect(getBrowserLocale('xx;q=0.9,fr;q=0.5')).toBe('fr')
  })

  it('returns null when nothing is supported / header absent', () => {
    expect(getBrowserLocale('xx,zz;q=0.8')).toBeNull()
    expect(getBrowserLocale(null)).toBeNull()
  })
})

describe('resolveLocale', () => {
  beforeEach(() => {
    requestHeaders.clear()
    requestCookies.clear()
  })

  it('returns an accepted ?locale override', async () => {
    requestHeaders.set('accept-language', 'nl')
    await expect(resolveLocale('fr')).resolves.toBe('fr')
  })

  it('honors the saved language choice (oc-locale cookie) over headers', async () => {
    requestHeaders.set('accept-language', 'nl')
    requestCookies.set('oc-locale', 'ja')
    await expect(resolveLocale()).resolves.toBe('ja')
  })

  it('falls back to the geo cookie when no header country is present', async () => {
    requestHeaders.set('accept-language', 'en-US')
    requestCookies.set('oc-geo-country', 'FR')
    await expect(resolveLocale()).resolves.toBe('fr')
  })

  it('ignores an unsupported ?locale and uses the header', async () => {
    requestHeaders.set('accept-language', 'nl')
    await expect(resolveLocale('xx')).resolves.toBe('nl')
  })

  it('returns a non-English browser preference', async () => {
    requestHeaders.set('accept-language', 'xx,fr;q=0.9')
    await expect(resolveLocale()).resolves.toBe('fr')
  })

  it('falls back to the country language when the browser is English', async () => {
    requestHeaders.set('accept-language', 'en-US')
    requestHeaders.set('cf-ipcountry', 'FR')
    await expect(resolveLocale()).resolves.toBe('fr')
  })

  it('a non-English browser preference beats the country', async () => {
    requestHeaders.set('accept-language', 'nl')
    requestHeaders.set('cf-ipcountry', 'FR')
    await expect(resolveLocale()).resolves.toBe('nl')
  })

  it('defaults to English when neither browser nor country match', async () => {
    requestHeaders.set('accept-language', 'xx,yy;q=0.5')
    requestHeaders.set('cf-ipcountry', 'US')
    await expect(resolveLocale()).resolves.toBe('en')
  })
})
