import rehypeShiki from '@shikijs/rehype'
import type { PluggableList } from 'unified'
// Reuse the exact Shiki themes the build-time @next/mdx pipeline uses so
// self-hosted docs highlight identically (see next.config.mjs / shiki.config.mjs).
import { themeConfig } from '../../../shiki.config.mjs'
import rehypeSlug from 'rehype-slug'
import remarkGfm from 'remark-gfm'

// Surface the fenced-code meta (e.g. ```bash curl (Production)) onto the <pre>
// so the tabbed <CodeGroup> can label each snippet.
const codeTitleTransformer = {
  name: 'docs:code-title',
  pre(
    this: { options: { meta?: { __raw?: string } } },
    node: {
      properties: Record<string, unknown>
    },
  ) {
    const raw = this.options.meta?.__raw?.trim()
    if (raw) node.properties['data-code-title'] = raw
  },
}

export const remarkPlugins: PluggableList = [remarkGfm]

export const rehypePlugins: PluggableList = [
  rehypeSlug,
  [rehypeShiki, { themes: themeConfig, transformers: [codeTitleTransformer] }],
]
