import type { Client } from '@outception-com/client'
import { Linking } from 'react-native'
import * as WebBrowser from 'expo-web-browser'
import { newsApi, openExternalUrl } from './news'

jest.mock('expo-web-browser', () => ({ openBrowserAsync: jest.fn() }))

describe('openExternalUrl', () => {
  it('opens http(s) URLs', () => {
    const spy = jest.spyOn(Linking, 'openURL').mockResolvedValue(true as never)
    openExternalUrl('https://example.com/a')
    expect(spy).toHaveBeenCalledWith('https://example.com/a')
    spy.mockRestore()
  })

  it('falls back to the in-app browser when the OS refuses the link', async () => {
    const spy = jest
      .spyOn(Linking, 'openURL')
      .mockRejectedValue(new Error('Unable to open URL'))
    const browser = jest
      .mocked(WebBrowser.openBrowserAsync)
      .mockResolvedValue({ type: 'cancel' as WebBrowser.WebBrowserResultType })
    openExternalUrl('https://www.youtube.com/shorts/x')
    await new Promise<void>((resolve) => setImmediate(resolve))
    expect(browser).toHaveBeenCalledWith('https://www.youtube.com/shorts/x')
    spy.mockRestore()
  })

  it('ignores unsafe schemes, deep links, and empty values', () => {
    const spy = jest.spyOn(Linking, 'openURL').mockResolvedValue(true as never)
    openExternalUrl('javascript:alert(1)')
    openExternalUrl('tel:12345')
    openExternalUrl('myapp://deeplink')
    openExternalUrl('')
    openExternalUrl(null)
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
  })
})

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

  it('source forwards the id', async () => {
    const { client, GET } = makeClient()
    GET.mockResolvedValue(okGet({ id: 'hackernews' }))
    await newsApi(client).source('hackernews')
    expect(GET).toHaveBeenCalledWith('/v1/news/{source_id}', {
      params: {
        path: { source_id: 'hackernews' },
        query: { lang: undefined, latest: true },
      },
    })
  })

  it('search GETs with the query', async () => {
    const { client, GET } = makeClient()
    GET.mockResolvedValue(okGet({ sources: [], items: [] }))
    await newsApi(client).search('rust')
    expect(GET).toHaveBeenCalledWith('/v1/news/search', {
      params: { query: { q: 'rust', lang: undefined } },
    })
  })
})
