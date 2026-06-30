import 'server-only'
import { CONFIG } from '@/utils/config'
import { readDoc } from './content'
import { flattenLeaves, getManifest } from './manifest'
import type { DocSet } from './types'

const absolute = (href: string): string =>
  `${CONFIG.FRONTEND_BASE_URL.replace(/\/$/, '')}${href}`

/** An llms.txt index: title, summary, and a linked list of every page. */
export async function buildLlmsTxt(set: DocSet): Promise<string> {
  const manifest = await getManifest(set)
  const leaves = flattenLeaves(manifest)
  const lines: string[] = [`# ${manifest.name}`, '']
  for (const leaf of leaves) {
    const doc = await readDoc(set, leaf.slug)
    const summary = doc?.frontmatter.description
    lines.push(
      `- [${leaf.title}](${absolute(leaf.href)})${summary ? `: ${summary}` : ''}`,
    )
  }
  return `${lines.join('\n')}\n`
}

/** Full-text dump: every page's body concatenated for LLM ingestion. */
export async function buildLlmsFull(set: DocSet): Promise<string> {
  const manifest = await getManifest(set)
  const leaves = flattenLeaves(manifest)
  const sections: string[] = []
  for (const leaf of leaves) {
    const doc = await readDoc(set, leaf.slug)
    if (!doc) continue
    sections.push(
      `# ${leaf.title}\nSource: ${absolute(leaf.href)}\n\n${doc.content.trim()}`,
    )
  }
  return `${sections.join('\n\n---\n\n')}\n`
}
