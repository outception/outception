import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { createApi, requiresToken, type FetchLike } from './api'
import { loadSkills } from './skills'
import { TOOLS, UNTRUSTED_NOTE, toolByName } from './tools'

const fakeFetch = (routes: Record<string, unknown>) => {
  const calls: string[] = []
  const fetch: FetchLike = async (input) => {
    calls.push(input)
    const path = input.replace(/^https?:\/\/[^/]+/, '').split('?')[0]!
    const body = routes[path]
    return {
      ok: body !== undefined,
      status: body !== undefined ? 200 : 404,
      json: async () => body,
      text: async () => JSON.stringify(body),
    }
  }
  return { fetch, calls }
}

const skillsDir = () => {
  const dir = mkdtempSync(join(tmpdir(), 'skills-'))
  mkdirSync(join(dir, 'outception-news'))
  writeFileSync(
    join(dir, 'outception-news', 'SKILL.md'),
    '---\nname: outception-news\ndescription: Read the wall.\n---\n# Body\n',
  )
  return dir
}

describe('api', () => {
  it('requires a token off loopback and not on it', () => {
    expect(requiresToken('http://127.0.0.1:8000')).toBe(false)
    expect(requiresToken('http://localhost:8000/')).toBe(false)
    expect(requiresToken('https://api.outception.com')).toBe(true)
    expect(() => createApi({ baseUrl: 'https://api.outception.com' })).toThrow(
      /TOKEN/,
    )
    expect(() =>
      createApi({ baseUrl: 'https://api.outception.com', token: 'x' }),
    ).not.toThrow()
  })

  it('sends the token and encodes the query', async () => {
    const { fetch, calls } = fakeFetch({
      '/v1/news/search': { items: [], sources: [] },
    })
    const api = createApi({
      baseUrl: 'https://api.outception.com/',
      token: 't',
      fetch,
    })
    await api.get('/v1/news/search', { q: 'a b', lang: undefined })
    expect(calls[0]).toBe('https://api.outception.com/v1/news/search?q=a%20b')
  })
})

describe('tools', () => {
  const env = { skillsDir: skillsDir() }
  const routes = {
    '/v1/news/search': {
      items: Array.from({ length: 40 }, (_, i) => ({
        sourceId: 's',
        item: { id: String(i) },
      })),
      sources: [{ id: 's', name: 'S' }],
    },
    '/v1/news/default-cards': ['a', 'b', 'weather'],
    '/v1/cards/bbc-world': {
      id: 'bbc-world',
      kind: 'feed',
      state: 'nominal',
      updatedAt: 1,
      payload: {
        kind: 'feed',
        items: Array.from({ length: 35 }, (_, i) => ({ id: i })),
      },
    },
    '/v1/news/story/abc': {
      id: 'abc',
      title: 'T',
      publisherCount: 2,
      items: [],
    },
    '/v1/news/briefing/profiles': {
      profiles: [
        { id: 'news-junkie', template: 'news-junkie', categories: [] },
      ],
    },
    '/v1/news/briefing/news-junkie': {
      profile: 'news-junkie',
      items: Array.from({ length: 50 }, (_, i) => ({ clusterId: String(i) })),
    },
    '/v1/news/summary/available': { available: false },
    '/v1/news/sources': [
      {
        id: 'heatmap-tech',
        name: 'Tech Table',
        type: 'heatmap',
        column: 'tech',
      },
      { id: 'bbc-world', name: 'BBC', type: 'hottest' },
    ],
    '/v1/news/weather': { location: 'Dublin', current: {}, daily: [] },
    '/v1/news/cities': {
      query: 'Dublin',
      place: { name: 'Dublin', latitude: 53.35, longitude: -6.26 },
      cardId: 'city-ireland-dublin',
    },
  }
  const { fetch, calls } = fakeFetch(routes)
  const api = createApi({ baseUrl: 'http://127.0.0.1:8000', fetch })

  it('registers eleven read-only tools with limits in every description', () => {
    expect(TOOLS).toHaveLength(11)
    for (const tool of TOOLS) {
      expect(tool.description.length).toBeGreaterThan(20)
    }
    expect(TOOLS.filter((t) => /at most \d+/.test(t.description)).length).toBe(
      6,
    )
  })

  it('caps results and marks every answer as data', async () => {
    const search = await toolByName('search_headlines')!.run(
      api,
      { query: 'rust' },
      env,
    )
    expect(search.text.startsWith(UNTRUSTED_NOTE)).toBe(true)
    expect(
      (JSON.parse(search.text.split('\n')[1]!) as { items: unknown[] }).items,
    ).toHaveLength(30)
    const card = await toolByName('get_card')!.run(
      api,
      { id: 'bbc-world', limit: 5 },
      env,
    )
    expect(
      (
        JSON.parse(card.text.split('\n')[1]!) as {
          payload: { items: unknown[] }
        }
      ).payload.items,
    ).toHaveLength(5)
    const briefing = await toolByName('get_briefing')!.run(
      api,
      { profile: 'news-junkie' },
      env,
    )
    expect(
      (JSON.parse(briefing.text.split('\n')[1]!) as { items: unknown[] }).items,
    ).toHaveLength(40)
    const tables = await toolByName('list_tables')!.run(api, {}, env)
    expect(JSON.parse(tables.text.split('\n')[1]!)).toEqual({
      tables: [{ id: 'heatmap-tech', name: 'Tech Table', section: 'tech' }],
    })
  })

  it('never triggers a summary that is not cached', async () => {
    const before = calls.length
    const result = await toolByName('get_summary')!.run(
      api,
      { url: 'https://example.com/a' },
      env,
    )
    expect(JSON.parse(result.text.split('\n')[1]!)).toMatchObject({
      cached: false,
      summary: null,
    })
    expect(
      calls.slice(before).some((c) => c.includes('/v1/news/summary?')),
    ).toBe(false)
  })

  it('validates ids and countries before any call', () => {
    expect(() => toolByName('get_card')!.schema.parse({ id: '../x' })).toThrow()
    expect(() =>
      toolByName('list_cards')!.schema.parse({ country: 'IRL' }),
    ).toThrow()
    expect(toolByName('get_weather')!.schema.parse({ country: 'ie' })).toEqual({
      country: 'ie',
    })
  })

  it('lists and reads skills', async () => {
    const list = await toolByName('list_skills')!.run(api, {}, env)
    expect(JSON.parse(list.text)).toEqual([
      { name: 'outception-news', description: 'Read the wall.' },
    ])
    const one = await toolByName('list_skills')!.run(
      api,
      { name: 'outception-news' },
      env,
    )
    expect(one.text).toContain('# Body')
    expect(loadSkills('/nonexistent')).toEqual([])
  })

  it('resolves a city through the catalog and refuses unknown arguments', async () => {
    const { parseArguments } = await import('./tools')
    const weather = toolByName('get_weather')!
    const out = await weather.run(api, { city: 'Dublin' }, env)
    expect(
      (JSON.parse(out.text.split('\n')[1]!) as { location: string }).location,
    ).toBe('Dublin')
    const weatherCall = calls.find((c) => c.includes('/v1/news/weather'))
    expect(weatherCall).toContain('latitude=53.35')
    expect(weatherCall).toContain('longitude=-6.26')
    expect(() => parseArguments(weather, { town: 'Dublin' })).toThrow()
    expect(parseArguments(weather, { city: ' Dublin ' })).toEqual({
      city: 'Dublin',
    })
  })
})
