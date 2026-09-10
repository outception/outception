import { describe, expect, it } from 'vitest'
import { SUPPORTED_LOCALES, toSupportedLocale } from './config'

describe('toSupportedLocale', () => {
  it('resolves the Chinese tags real devices actually report', () => {
    // The supported list holds zh-Hans/zh-Hant, never a bare `zh`, so an
    // exact-match-then-primary-language reducer dropped every one of these
    // and opened the app in English on a phone set to 简体中文.
    expect(toSupportedLocale('zh-Hans-CN')).toBe('zh-Hans')
    expect(toSupportedLocale('zh-CN')).toBe('zh-Hans')
    expect(toSupportedLocale('zh-SG')).toBe('zh-Hans')
    expect(toSupportedLocale('zh')).toBe('zh-Hans')
    expect(toSupportedLocale('zh-Hant-TW')).toBe('zh-Hant')
    expect(toSupportedLocale('zh-TW')).toBe('zh-Hant')
    expect(toSupportedLocale('zh-HK')).toBe('zh-Hant')
    expect(toSupportedLocale('zh-MO')).toBe('zh-Hant')
  })

  it('maps the CLDR Filipino code onto the tl locale', () => {
    expect(toSupportedLocale('fil-PH')).toBe('tl')
    expect(toSupportedLocale('fil')).toBe('tl')
    expect(toSupportedLocale('tl')).toBe('tl')
  })

  it('still prefers an exact match and then the primary language', () => {
    expect(toSupportedLocale('pt-PT')).toBe('pt-PT')
    expect(toSupportedLocale('pt-BR')).toBe('pt')
    expect(toSupportedLocale('de-DE')).toBe('de')
    expect(toSupportedLocale('en-US')).toBe('en')
  })

  it('returns null for languages we do not translate', () => {
    expect(toSupportedLocale('xx-YY')).toBeNull()
    expect(toSupportedLocale('is')).toBeNull()
  })

  it('resolves every supported locale to itself', () => {
    for (const locale of SUPPORTED_LOCALES) {
      expect(toSupportedLocale(locale)).toBe(locale)
    }
  })
})
