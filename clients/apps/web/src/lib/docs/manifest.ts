import 'server-only'
import { promises as fs } from 'node:fs'
import path from 'node:path'
import { getOperation } from '@/lib/openapi/parse'
import { basePathForSet, readFrontmatter, setRoot } from './content'
import type {
  DocRedirect,
  DocSet,
  DocsManifest,
  NavGroup,
  NavNode,
  NavTab,
} from './types'

interface RawGroup {
  group: string
  pages?: RawPage[]
}
type RawPage = string | RawGroup
interface RawTab {
  tab: string
  icon?: string
  groups?: RawGroup[]
  pages?: RawPage[]
}
interface RawDocsJson {
  name?: string
  navigation?: {
    tabs?: RawTab[]
    groups?: RawGroup[]
  }
  redirects?: DocRedirect[]
}

const cache = new Map<DocSet, Promise<RawDocsJson>>()

const loadDocsJson = (set: DocSet): Promise<RawDocsJson> => {
  let cached = cache.get(set)
  if (!cached) {
    cached = fs
      .readFile(path.join(setRoot(set), 'docs.json'), 'utf8')
      .then((raw) => JSON.parse(raw) as RawDocsJson)
    cache.set(set, cached)
  }
  return cached
}

const titleize = (slugTail: string): string =>
  slugTail
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')

const buildLeaf = async (set: DocSet, pagePath: string): Promise<NavNode> => {
  const slug = pagePath.split('/')
  const frontmatter = await readFrontmatter(set, slug)
  let title = frontmatter?.sidebarTitle ?? frontmatter?.title
  if (!title && frontmatter?.openapi) {
    // API-reference pages carry only `openapi` frontmatter; label them with the
    // operation summary, matching Mintlify's auto-generated titles.
    title = (await getOperation(frontmatter.openapi))?.summary
  }
  title = title ?? titleize(slug[slug.length - 1])
  return {
    kind: 'leaf',
    title,
    slug,
    href: `${basePathForSet(set)}/${pagePath}`,
  }
}

const buildPages = async (set: DocSet, pages: RawPage[]): Promise<NavNode[]> =>
  Promise.all(
    pages.map((page) =>
      typeof page === 'string' ? buildLeaf(set, page) : buildGroup(set, page),
    ),
  )

const buildGroup = async (set: DocSet, group: RawGroup): Promise<NavGroup> => ({
  kind: 'group',
  title: group.group,
  items: await buildPages(set, group.pages ?? []),
})

const buildTab = async (set: DocSet, tab: RawTab): Promise<NavTab> => {
  const items = tab.groups
    ? await Promise.all(tab.groups.map((g) => buildGroup(set, g)))
    : await buildPages(set, tab.pages ?? [])
  return { title: tab.tab, icon: tab.icon, items }
}

export async function getManifest(set: DocSet): Promise<DocsManifest> {
  const json = await loadDocsJson(set)
  const nav = json.navigation ?? {}
  let tabs: NavTab[]
  if (nav.tabs) {
    tabs = await Promise.all(nav.tabs.map((tab) => buildTab(set, tab)))
  } else {
    // Handbook: flat groups, modelled as a single implicit tab.
    const items = await Promise.all(
      (nav.groups ?? []).map((g) => buildGroup(set, g)),
    )
    tabs = [{ title: json.name ?? 'Handbook', items }]
  }
  return {
    set,
    basePath: basePathForSet(set),
    name: json.name ?? set,
    tabs,
  }
}

export async function getRedirects(set: DocSet): Promise<DocRedirect[]> {
  const json = await loadDocsJson(set)
  return json.redirects ?? []
}

/**
 * For a section path with no page of its own (e.g. /docs/api-reference), return
 * the href of its first child leaf so it can redirect there instead of 404ing.
 */
export function firstLeafUnder(
  manifest: DocsManifest,
  slug: string[],
): string | null {
  const prefix = `${manifest.basePath}/${slug.join('/')}/`
  return (
    flattenLeaves(manifest).find((leaf) => leaf.href.startsWith(prefix))
      ?.href ?? null
  )
}

/** Flattened, in-order list of every leaf across all tabs. */
export function flattenLeaves(manifest: DocsManifest): {
  title: string
  href: string
  slug: string[]
}[] {
  const out: { title: string; href: string; slug: string[] }[] = []
  const visit = (node: NavNode): void => {
    if (node.kind === 'leaf') {
      out.push({ title: node.title, href: node.href, slug: node.slug })
    } else {
      node.items.forEach(visit)
    }
  }
  manifest.tabs.forEach((tab) => tab.items.forEach(visit))
  return out
}
