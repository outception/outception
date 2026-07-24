import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  getClientCountry,
  getLocaleFromCountry,
  hasLocaleOverride,
  resolveClientLocale,
} from './shared'

function setBrowser(languages: string[]) {
  vi.stubGlobal('navigator', { languages, language: languages[0] })
}

function setCookies(pairs: Record<string, string>) {
  const cookie = Object.entries(pairs)
    .map(([k, v]) => `${k}=${v}`)
    .join('; ')
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    get: () => cookie || 'other=1',
  })
}

function setGeoCookie(country: string | null) {
  setCookies(country ? { 'oc-geo-country': country } : {})
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('resolveClientLocale', () => {
  it('honours an explicit non-English browser language', () => {
    setBrowser(['de-DE', 'de'])
    setGeoCookie('JP')
    // Browser preference wins over the geo country.
    expect(resolveClientLocale('en')).toBe('de')
  })

  it('falls back to the geo country when the browser is English', () => {
    setBrowser(['en-US', 'en'])
    setGeoCookie('JP')
    expect(resolveClientLocale('en')).toBe('ja')
  })

  it('maps a Spanish-speaking country from the cookie', () => {
    setBrowser(['en-GB'])
    setGeoCookie('MX')
    expect(resolveClientLocale('en')).toBe('es')
  })

  it('stays English for an English/unmapped country', () => {
    setBrowser(['en-US'])
    setGeoCookie('US')
    expect(resolveClientLocale('en')).toBe('en')
  })

  it('stays English with no cookie and an English browser', () => {
    setBrowser(['en-US'])
    setGeoCookie(null)
    expect(resolveClientLocale('en')).toBe('en')
  })

  it('handles a bare primary language code', () => {
    setBrowser(['fr'])
    setGeoCookie(null)
    expect(resolveClientLocale('en')).toBe('fr')
  })
})

describe('country flag detection', () => {
  it('reads the detected country from the geo cookie (upper-cased)', () => {
    setCookies({ 'oc-geo-country': 'ie' })
    expect(getClientCountry()).toBe('IE')
  })

  it('returns null with no geo cookie', () => {
    setGeoCookie(null)
    expect(getClientCountry()).toBeNull()
  })

  it('detects an explicit language override', () => {
    setCookies({ 'oc-locale': 'es', 'oc-geo-country': 'IE' })
    expect(hasLocaleOverride()).toBe(true)
  })

  it('is not an override when only the geo cookie is set', () => {
    setCookies({ 'oc-geo-country': 'IE' })
    expect(hasLocaleOverride()).toBe(false)
  })

  it('Ireland keeps English but is detected as country IE (Irish flag)', () => {
    setBrowser(['en-IE', 'en'])
    setCookies({ 'oc-geo-country': 'IE' })
    // Ireland is unmapped, so the language stays English…
    expect(getLocaleFromCountry('IE')).toBeNull()
    expect(resolveClientLocale('en')).toBe('en')
    // …but the flag shown is the visitor's country (IE), not the language flag.
    expect(getClientCountry()).toBe('IE')
    expect(hasLocaleOverride()).toBe(false)
  })

  it.each(['BE', 'CH', 'CA', 'IN', 'PH', 'MY', 'HK', 'PK', 'ID', 'AE'])(
    'multilingual country %s defaults to English + its own flag',
    (country) => {
      setBrowser(['en-US'])
      setCookies({ 'oc-geo-country': country })
      // Unmapped → neutral English default (not one language community's), but…
      expect(getLocaleFromCountry(country)).toBeNull()
      expect(resolveClientLocale('en')).toBe('en')
      // …the visitor still sees their own country's flag.
      expect(getClientCountry()).toBe(country)
    },
  )

  it('a Dutch-speaking Belgian still gets Dutch via their browser locale', () => {
    setBrowser(['nl-BE', 'nl'])
    setCookies({ 'oc-geo-country': 'BE' })
    // Browser preference wins over the country fallback.
    expect(resolveClientLocale('en')).toBe('nl')
    expect(getClientCountry()).toBe('BE')
  })

  it('a Hindi-speaking Indian still gets Hindi via their browser locale', () => {
    setBrowser(['hi-IN', 'hi'])
    setCookies({ 'oc-geo-country': 'IN' })
    expect(resolveClientLocale('en')).toBe('hi')
    expect(getClientCountry()).toBe('IN')
  })
})
