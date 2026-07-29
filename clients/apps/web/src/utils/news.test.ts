import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest'

vi.mock('@/utils/client', () => ({
  api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() },
}))

import { api } from '@/utils/client'
import { newsApi, safeExternalHref } from './news'

const ok = (data: unknown) => ({
  data,
  error: undefined,
  response: { ok: true, status: 200, headers: new Headers() },
})

const get = api.GET as unknown as Mock

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
})

beforeEach(() => {
  get.mockReset()
  get.mockResolvedValue(ok([]))
})

describe('newsApi', () => {
  it('sources GETs the sources endpoint', async () => {
    await newsApi.sources()
    expect(get).toHaveBeenCalledWith('/v1/news/sources')
  })

  it('source forwards the id with default latest/sort', async () => {
    get.mockResolvedValue(ok({ id: 'hackernews' }))
    await newsApi.source('hackernews')
    expect(get).toHaveBeenCalledWith('/v1/news/{source_id}', {
      params: {
        path: { source_id: 'hackernews' },
        query: { latest: false, sort: 'hot' },
      },
    })
  })

  it('source forwards an explicit latest flag and sort', async () => {
    get.mockResolvedValue(ok({ id: 'hackernews' }))
    await newsApi.source('hackernews', true, 'top')
    expect(get).toHaveBeenCalledWith('/v1/news/{source_id}', {
      params: {
        path: { source_id: 'hackernews' },
        query: { latest: true, sort: 'top' },
      },
    })
  })

  it('search GETs with the query', async () => {
    get.mockResolvedValue(ok({ sources: [], items: [] }))
    // lang is undefined here; the hook supplies the reader's locale.
    await newsApi.search('rust')
    expect(get).toHaveBeenCalledWith('/v1/news/search', {
      params: { query: { q: 'rust', lang: undefined } },
    })
  })
})
