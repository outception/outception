import 'server-only'
import { promises as fs } from 'node:fs'
import path from 'node:path'
import GithubSlugger from 'github-slugger'
import matter from 'gray-matter'
import type { DocFrontmatter, DocSet, TocHeading } from './types'

const CONTENT_DIR = path.join(process.cwd(), 'content')

/** When the route slug is empty, render this page for the set. */
const SET_LANDING: Record<DocSet, string[]> = {
  docs: ['introduction'],
  handbook: ['index'],
}

export const setRoot = (set: DocSet): string => path.join(CONTENT_DIR, set)

export const basePathForSet = (set: DocSet): string => `/${set}`

export interface LoadedDoc {
  frontmatter: DocFrontmatter
  /** MDX body with frontmatter stripped */
  content: string
  slug: string[]
}

const resolveSlug = (set: DocSet, slug: string[]): string[] =>
  slug.length === 0 ? SET_LANDING[set] : slug

export async function readDoc(
  set: DocSet,
  slug: string[],
): Promise<LoadedDoc | null> {
  const resolved = resolveSlug(set, slug)
  const file = path.join(setRoot(set), `${resolved.join('/')}.mdx`)
  let raw: string
  try {
    raw = await fs.readFile(file, 'utf8')
  } catch {
    return null
  }
  const { data, content } = matter(raw)
  return { frontmatter: data as DocFrontmatter, content, slug: resolved }
}

/** Walk the set directory and return every page's slug segments. */
export async function listSlugs(set: DocSet): Promise<string[][]> {
  const root = setRoot(set)
  const out: string[][] = []
  const walk = async (dir: string): Promise<void> => {
    const entries = await fs.readdir(dir, { withFileTypes: true })
    for (const entry of entries) {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        await walk(full)
      } else if (entry.isFile() && entry.name.endsWith('.mdx')) {
        const rel = path.relative(root, full).replace(/\.mdx$/, '')
        out.push(rel.split('/'))
      }
    }
  }
  await walk(root)
  return out
}

/**
 * Frontmatter only — used by the manifest to resolve nav titles without
 * compiling MDX.
 */
export async function readFrontmatter(
  set: DocSet,
  slug: string[],
): Promise<DocFrontmatter | null> {
  const file = path.join(setRoot(set), `${slug.join('/')}.mdx`)
  try {
    const raw = await fs.readFile(file, 'utf8')
    return matter(raw).data as DocFrontmatter
  } catch {
    return null
  }
}

/**
 * Extract level-2/3 headings for the table of contents. Ids are produced with
 * github-slugger to match rehype-slug's output.
 */
export function extractHeadings(content: string): TocHeading[] {
  const slugger = new GithubSlugger()
  const headings: TocHeading[] = []
  let inFence = false
  for (const line of content.split('\n')) {
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence
      continue
    }
    if (inFence) continue
    const match = /^(#{2,3})\s+(.+?)\s*#*\s*$/.exec(line)
    if (!match) continue
    const depth = match[1].length as 2 | 3
    const title = match[2].replace(/[*`_]/g, '').trim()
    headings.push({ depth, title, id: slugger.slug(title) })
  }
  return headings
}
