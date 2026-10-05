import { describe, expect, it } from 'vitest'
import {
  hostOf,
  isHttpUrl,
  isSummarizable,
  safeExternalHref,
} from './urlSafety'

describe('isSummarizable', () => {
  it('rejects video pages and junk, but lets aggregator links try', () => {
    expect(isSummarizable('https://news.google.com/rss/articles/x?oc=5')).toBe(
      true,
    )
    expect(isSummarizable('https://www.youtube.com/watch?v=x')).toBe(false)
    expect(isSummarizable('https://youtu.be/x')).toBe(false)
    expect(isSummarizable('https://YouTube.com:443/x')).toBe(false)
    expect(isSummarizable('not a url')).toBe(false)
    expect(isSummarizable(null)).toBe(false)
  })

  it('accepts ordinary article links', () => {
    expect(isSummarizable('https://www.bbc.co.uk/news/articles/abc')).toBe(true)
  })
})

describe('safeExternalHref', () => {
  it('returns http(s) URLs unchanged', () => {
    expect(safeExternalHref('https://example.com/a')).toBe(
      'https://example.com/a',
    )
    expect(safeExternalHref('http://example.com')).toBe('http://example.com')
  })

  it('returns undefined for unsafe schemes, junk, or empty', () => {
    expect(safeExternalHref('javascript:alert(1)')).toBeUndefined()
    expect(safeExternalHref('data:text/html,x')).toBeUndefined()
    expect(safeExternalHref('not a url')).toBeUndefined()
    expect(safeExternalHref('')).toBeUndefined()
    expect(safeExternalHref(null)).toBeUndefined()
    expect(safeExternalHref(undefined)).toBeUndefined()
  })

  it('isHttpUrl narrows and hostOf lowercases', () => {
    expect(isHttpUrl('ftp://x')).toBe(false)
    expect(hostOf('HTTPS://Example.COM/path')).toBe('example.com')
    expect(hostOf('mailto:x')).toBeNull()
  })
})
