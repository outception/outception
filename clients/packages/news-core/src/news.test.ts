import { describe, expect, it } from 'vitest'
import {
  briefingPath,
  shareCardPath,
  sourceIconPath,
  storyPath,
  timeAgo,
  wallPath,
} from './news'

describe('paths', () => {
  it('builds the paths the web app serves', () => {
    expect(sourceIconPath('bbc-world')).toBe('/news-icons/bbc.png')
    expect(shareCardPath('a b')).toBe('/?card=a%20b')
    expect(wallPath()).toBe('/')
    expect(wallPath('tech')).toBe('/?topic=tech')
    expect(storyPath('s/1')).toBe('/story/s%2F1')
    expect(briefingPath('news-junkie')).toBe('/briefing/news-junkie')
  })
})

describe('timeAgo', () => {
  const now = Date.UTC(2026, 9, 5, 12, 0, 0)
  const minutes = 60_000
  const hours = 60 * minutes
  const days = 24 * hours

  it('clamps the future and the first minute to now', () => {
    expect(timeAgo(now + 5 * minutes, now, 'en')).toBe('now')
    expect(timeAgo(now - 30_000, now, 'en')).toBe('now')
    expect(timeAgo(Number.NaN, now, 'en')).toBe('now')
  })

  it('buckets minutes, hours, days, weeks, months and years', () => {
    expect(timeAgo(now - 5 * minutes, now, 'en')).toMatch(/5 ?m/)
    expect(timeAgo(now - 3 * hours, now, 'en')).toMatch(/3 ?h/)
    expect(timeAgo(now - 2 * days, now, 'en')).toMatch(/2 ?d/)
    expect(timeAgo(now - 29 * days, now, 'en')).toMatch(/4 ?w/)
    expect(timeAgo(now - 364 * days, now, 'en')).toMatch(/12 ?mo/)
    expect(timeAgo(now - 400 * days, now, 'en')).toMatch(/1 ?y|last y/)
  })
})
