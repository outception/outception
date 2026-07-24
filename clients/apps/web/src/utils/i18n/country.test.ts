import { describe, expect, it } from 'vitest'
import { getLocaleFromCountry } from './index'

describe('getLocaleFromCountry', () => {
  it('maps countries to their supported UI locale', () => {
    expect(getLocaleFromCountry('JP')).toBe('ja')
    expect(getLocaleFromCountry('DE')).toBe('de')
    expect(getLocaleFromCountry('FR')).toBe('fr')
    expect(getLocaleFromCountry('KR')).toBe('ko')
    expect(getLocaleFromCountry('TR')).toBe('tr')
  })

  it('maps Portuguese variants apart (Brazil vs Portugal)', () => {
    expect(getLocaleFromCountry('BR')).toBe('pt')
    expect(getLocaleFromCountry('PT')).toBe('pt-PT')
  })

  it('maps Latin-American countries to Spanish', () => {
    expect(getLocaleFromCountry('MX')).toBe('es')
    expect(getLocaleFromCountry('AR')).toBe('es')
    expect(getLocaleFromCountry('ES')).toBe('es')
    // El Salvador's country code SV must map to Spanish, not the sv locale.
    expect(getLocaleFromCountry('SV')).toBe('es')
  })

  it('is case-insensitive and trims', () => {
    expect(getLocaleFromCountry('jp')).toBe('ja')
    expect(getLocaleFromCountry('  de  ')).toBe('de')
  })

  it('returns null for unmapped, unknown, or empty countries', () => {
    expect(getLocaleFromCountry('US')).toBeNull() // English → default path
    expect(getLocaleFromCountry('XX')).toBeNull()
    expect(getLocaleFromCountry('')).toBeNull()
    expect(getLocaleFromCountry(null)).toBeNull()
  })
})
