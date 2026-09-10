import 'server-only'
import { readDoc } from './content'
import { flattenLeaves, getManifest } from './manifest'
import type { DocSet } from './types'

export interface SearchEntry {
  title: string
  href: string
  description?: string
  content: string
}

/** Strip MDX/markdown syntax down to plain searchable text. */
const stripMdx = (source: string): string =>
  source
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[#>*_`|-]+/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\s+/g, ' ')
    .trim()

export async function buildSearchIndex(set: DocSet): Promise<SearchEntry[]> {
  const manifest = await getManifest(set)
  const leaves = flattenLeaves(manifest)
  return Promise.all(
    leaves.map(async (leaf) => {
      const doc = await readDoc(set, leaf.slug)
      return {
        title: leaf.title,
        href: leaf.href,
        description: doc?.frontmatter.description,
        content: doc ? stripMdx(doc.content).slice(0, 2000) : '',
      }
    }),
  )
}
