/**
 * The crawler surface: server-rendered pages per country, per city card and
 * per Starter, with live headlines from the edge-cached data and a canonical
 * link to the wall. Nothing here runs in the browser.
 */

import { getServerURL } from '@/utils/api'
import type { schemas } from '@outception-com/client'

type SourceMeta = schemas['SourceMeta']
type Card = schemas['Card']
type Template = schemas['NewsTemplate']

/** The countries with their own crawler page: the catalog's largest editions. */
export const COUNTRY_PAGES: readonly string[] = [
  'IE',
  'GB',
  'US',
  'CA',
  'AU',
  'NZ',
  'IN',
  'DE',
  'FR',
  'ES',
  'IT',
  'NL',
  'SE',
  'NO',
  'DK',
  'FI',
  'PL',
  'PT',
  'BR',
  'MX',
  'AR',
  'ZA',
  'NG',
  'KE',
  'JP',
  'KR',
  'SG',
  'PH',
  'ID',
  'AE',
]

export const HEADLINES_PER_CARD = 8
export const CARDS_PER_PAGE = 6
const COUNTRY_SLUG = /^news-in-([a-z]{2})$/
const CITY_SLUG = /^city-[a-z0-9-]{3,80}$/
const STARTER_SLUG = /^starter-([a-z0-9-]{1,40})$/

export type CrawlerSlug =
  | { kind: 'country'; code: string }
  | { kind: 'city'; id: string }
  | { kind: 'starter'; id: string }

export const parseCrawlerSlug = (slug: string): CrawlerSlug | null => {
  const country = COUNTRY_SLUG.exec(slug)
  if (country) return { kind: 'country', code: country[1]!.toUpperCase() }
  if (CITY_SLUG.test(slug)) return { kind: 'city', id: slug }
  const starter = STARTER_SLUG.exec(slug)
  if (starter) return { kind: 'starter', id: starter[1]! }
  return null
}

export const countrySlug = (code: string) => `news-in-${code.toLowerCase()}`
export const starterSlug = (id: string) => `starter-${id}`

export const countryName = (code: string): string => {
  try {
    return new Intl.DisplayNames(['en'], { type: 'region' }).of(code) ?? code
  } catch {
    return code
  }
}

/** The Starter's display name from the strings, falling back to the id. */
export const starterName = (
  id: string,
  names: Record<string, string>,
): string => names[id] ?? id.replace(/-/g, ' ')

const fetchJson = async <T>(
  path: string,
  revalidate = 900,
): Promise<T | null> => {
  try {
    const response = await fetch(getServerURL(path), { next: { revalidate } })
    if (!response.ok) return null
    return (await response.json()) as T
  } catch {
    return null
  }
}

export interface CrawlerCard {
  id: string
  name: string
  home: string | null
  updatedAt: number | null
  state: string
  items: { id: string; title: string; url: string }[]
}

export interface CrawlerPageData {
  title: string
  intro: string
  /** Where the page points the crawler and the reader. */
  wallPath: string
  cards: CrawlerCard[]
  moreSources: number
}

const cardFor = async (
  id: string,
  meta?: SourceMeta,
): Promise<CrawlerCard | null> => {
  const card = await fetchJson<Card>(`/v1/cards/${encodeURIComponent(id)}`)
  if (!card || card.payload.kind !== 'feed') return null
  const name = meta?.name ?? card.meta?.name ?? id
  return {
    id,
    name,
    home: meta?.home ?? card.meta?.home ?? null,
    updatedAt: card.updatedAt,
    state: card.state,
    items: card.payload.items.slice(0, HEADLINES_PER_CARD).map((item) => ({
      id: item.id,
      title: item.title,
      url: item.url,
    })),
  }
}

const metasFor = async (
  ids: readonly string[],
): Promise<Map<string, SourceMeta>> => {
  if (ids.length === 0) return new Map()
  const metas = await fetchJson<SourceMeta[]>(
    `/v1/news/sources?ids=${encodeURIComponent(ids.join(','))}`,
    3600,
  )
  return new Map((metas ?? []).map((m) => [m.id, m]))
}

const feedIds = (ids: readonly string[]): string[] =>
  ids.filter((id) => !id.startsWith('briefing:') && id !== 'weather')

const cardsFor = async (ids: readonly string[]): Promise<CrawlerCard[]> => {
  const wanted = feedIds(ids).slice(0, CARDS_PER_PAGE)
  const metas = await metasFor(wanted)
  const cards = await Promise.all(
    wanted.map((id) => cardFor(id, metas.get(id))),
  )
  return cards.filter((c): c is CrawlerCard => c !== null && c.items.length > 0)
}

export const countryPage = async (
  code: string,
  t: { title: (country: string) => string; intro: (country: string) => string },
): Promise<CrawlerPageData | null> => {
  if (!COUNTRY_PAGES.includes(code)) return null
  const ids = await fetchJson<string[]>(
    `/v1/news/default-cards?country=${code}`,
    3600,
  )
  if (!ids || ids.length === 0) return null
  const cards = await cardsFor(ids)
  if (cards.length === 0) return null
  const country = countryName(code)
  return {
    title: t.title(country),
    intro: t.intro(country),
    wallPath: `/?card=${encodeURIComponent(`gnews-${code.toLowerCase()}`)}`,
    cards,
    moreSources: Math.max(0, feedIds(ids).length - cards.length),
  }
}

export const cityPage = async (
  id: string,
  t: { title: (city: string) => string; intro: (city: string) => string },
): Promise<CrawlerPageData | null> => {
  const meta = await fetchJson<SourceMeta>(
    `/v1/news/sources/${encodeURIComponent(id)}`,
    3600,
  )
  if (!meta || meta.column !== 'cities') return null
  const card = await cardFor(id, meta)
  if (!card || card.items.length === 0) return null
  return {
    title: t.title(meta.name),
    intro: t.intro(meta.name),
    wallPath: `/?card=${encodeURIComponent(id)}`,
    cards: [card],
    moreSources: 0,
  }
}

export const starterPage = async (
  id: string,
  names: Record<string, string>,
  t: { title: (name: string) => string; intro: (name: string) => string },
): Promise<CrawlerPageData | null> => {
  const data = await fetchJson<{ templates: Template[] }>(
    '/v1/news/templates',
    3600,
  )
  const template = data?.templates.find((item) => item.id === id)
  if (!template || template.sources.length === 0) return null
  const cards = await cardsFor(template.sources)
  if (cards.length === 0) return null
  const name = starterName(id, names)
  return {
    title: t.title(name),
    intro: t.intro(name),
    wallPath: '/',
    cards,
    moreSources: Math.max(0, template.sources.length - cards.length),
  }
}

/** Every slug the sitemap lists: the fixed countries, every city card and
 * every Starter the server serves. Falls back to the countries alone when
 * the API is unreachable at build time. */
export const crawlerSlugs = async (): Promise<string[]> => {
  const slugs = COUNTRY_PAGES.map(countrySlug)
  const templates = await fetchJson<{ templates: Template[] }>(
    '/v1/news/templates',
    86_400,
  )
  for (const template of templates?.templates ?? [])
    slugs.push(starterSlug(template.id))
  const roster = await fetchJson<SourceMeta[]>('/v1/news/sources', 86_400)
  for (const meta of roster ?? []) {
    if (meta.column === 'cities' && !meta.redirect && CITY_SLUG.test(meta.id))
      slugs.push(meta.id)
  }
  return slugs
}
