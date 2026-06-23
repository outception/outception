import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest'

vi.mock('@/utils/client', () => ({
  api: { GET: vi.fn(), POST: vi.fn() },
}))

import { api } from '@/utils/client'
import { newsApi } from './news'

const ok = (data: unknown) => ({
  data,
  error: undefined,
  response: { ok: true, status: 200, headers: new Headers() },
})

const get = api.GET as unknown as Mock
const post = api.POST as unknown as Mock

beforeEach(() => {
  get.mockReset()
  post.mockReset()
  get.mockResolvedValue(ok([]))
  post.mockResolvedValue(ok({}))
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

  it('batch POSTs the requested source ids', async () => {
    await newsApi.batch(['hackernews', 'reddit'])
    expect(post).toHaveBeenCalledWith('/v1/news/batch', {
      body: { sources: ['hackernews', 'reddit'] },
    })
  })

  it('search GETs with the query', async () => {
    get.mockResolvedValue(ok({ sources: [], items: [] }))
    await newsApi.search('rust')
    expect(get).toHaveBeenCalledWith('/v1/news/search', {
      params: { query: { q: 'rust' } },
    })
  })
})
