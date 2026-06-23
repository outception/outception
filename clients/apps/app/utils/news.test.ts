import type { Client } from '@polar-sh/client'
import { newsApi } from './news'

const makeClient = () => {
  const GET = jest.fn().mockResolvedValue({
    data: [],
    error: undefined,
    response: { status: 200 },
  })
  const PUT = jest.fn().mockResolvedValue({
    data: undefined,
    error: undefined,
    response: { status: 204 },
  })
  const DELETE = jest.fn().mockResolvedValue({
    data: undefined,
    error: undefined,
    response: { status: 204 },
  })
  const client = { GET, PUT, DELETE } as unknown as Client
  return { client, GET, PUT, DELETE }
}

const okGet = (data: unknown) => ({
  data,
  error: undefined,
  response: { status: 200 },
})

describe('newsApi', () => {
  it('sources GETs the sources endpoint', async () => {
    const { client, GET } = makeClient()
    GET.mockResolvedValue(okGet([{ id: 'hackernews' }]))
    await newsApi(client).sources()
    expect(GET).toHaveBeenCalledWith('/v1/news/sources')
  })

  it('source forwards the id with the default sort', async () => {
    const { client, GET } = makeClient()
    GET.mockResolvedValue(okGet({ id: 'hackernews' }))
    await newsApi(client).source('hackernews')
    expect(GET).toHaveBeenCalledWith('/v1/news/{source_id}', {
      params: { path: { source_id: 'hackernews' }, query: { sort: 'hot' } },
    })
  })

  it('source forwards an explicit sort', async () => {
    const { client, GET } = makeClient()
    GET.mockResolvedValue(okGet({ id: 'hackernews' }))
    await newsApi(client).source('hackernews', 'top')
    expect(GET).toHaveBeenCalledWith('/v1/news/{source_id}', {
      params: { path: { source_id: 'hackernews' }, query: { sort: 'top' } },
    })
  })

  it('search GETs with the query', async () => {
    const { client, GET } = makeClient()
    GET.mockResolvedValue(okGet({ sources: [], items: [] }))
    await newsApi(client).search('rust')
    expect(GET).toHaveBeenCalledWith('/v1/news/search', {
      params: { query: { q: 'rust' } },
    })
  })

  it('followed GETs the followed endpoint', async () => {
    const { client, GET } = makeClient()
    GET.mockResolvedValue(okGet({ sourceIds: [] }))
    await newsApi(client).followed()
    expect(GET).toHaveBeenCalledWith('/v1/news/followed')
  })

  it('follow PUTs / unfollow DELETEs the source id', async () => {
    const { client, PUT, DELETE } = makeClient()
    await newsApi(client).follow('hackernews')
    expect(PUT).toHaveBeenCalledWith('/v1/news/followed/{source_id}', {
      params: { path: { source_id: 'hackernews' } },
    })
    await newsApi(client).unfollow('hackernews')
    expect(DELETE).toHaveBeenCalledWith('/v1/news/followed/{source_id}', {
      params: { path: { source_id: 'hackernews' } },
    })
  })
})
