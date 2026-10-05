import { translate } from '@outception-com/i18n'
import { describe, expect, it } from 'vitest'
import {
  formatDay,
  kickerLabel,
  launchStateLabel,
  logoSrc,
  todayKey,
} from './launchCopy'

describe('launch copy', () => {
  it('formats days and states', () => {
    expect(formatDay('2026-10-05')).toMatch(/Monday.*5.*October|October 5/)
    expect(formatDay('nonsense')).toBe('nonsense')
    expect(
      launchStateLabel(translate, { state: 'approved', day: '2026-10-05' }),
    ).toMatch(/Approved for .*October/)
    expect(launchStateLabel(translate, { state: 'submitted' })).toBe(
      'Waiting for review',
    )
    expect(launchStateLabel(translate, { state: 'odd' })).toBe('odd')
  })

  it('labels kickers and resolves logos safely', () => {
    expect(kickerLabel(translate, 'open source')).toBe('Open source')
    expect(kickerLabel(translate, 'house')).toBe('House')
    expect(logoSrc('/media/x.png')).toBe(
      'http://api.outception.test/media/x.png',
    )
    expect(logoSrc('https://example.com/a.png')).toBe(
      'https://example.com/a.png',
    )
    expect(logoSrc('javascript:alert(1)')).toBeUndefined()
    expect(todayKey(Date.UTC(2026, 9, 5, 23, 0))).toBe('2026-10-05')
  })
})
