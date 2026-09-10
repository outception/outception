import { describe, expect, it } from 'vitest'
import { translate } from './index'

// The exported signature is key-typed, which is the point for callers but
// gets in the way of testing the missing-key path on purpose.
const t = translate as (key: string, values?: Record<string, unknown>) => string

describe('translate', () => {
  it('returns the string at a dot-separated key', () => {
    expect(t('legal.terms.title')).toBe('Terms of Service')
  })

  it('fills in named placeholders', () => {
    expect(t('legal.lastUpdated', { date: '1 January 2026' })).toBe(
      'Last updated: 1 January 2026',
    )
  })

  it('leaves an unknown placeholder visible rather than printing undefined', () => {
    expect(t('legal.lastUpdated', {})).toBe('Last updated: {date}')
  })

  it('returns the key itself when nothing is there', () => {
    // A dynamic key that walks off the table must not throw from inside
    // render: the whole point of the null-safe walk.
    expect(t('news.nope.missing')).toBe('news.nope.missing')
    expect(t('legal')).toBe('legal')
  })
})
