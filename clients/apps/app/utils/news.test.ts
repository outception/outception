import type { Client } from '@polar-sh/client'
import { newsApi } from './news'

const makeClient = () => {
  const GET = jest.fn().mockResolvedValue({
    data: [],
    error: undefined,
    response: { status: 200 },
  })
  const client = { GET } as unknown as Client
  return { client, GET }
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
})
