import ProseWrapper from '@/components/MDX/ProseWrapper'
import { extractHeadings, readDoc } from '@/lib/docs/content'
import { firstLeafUnder, getManifest } from '@/lib/docs/manifest'
import { rehypePlugins, remarkPlugins } from '@/lib/docs/mdx-options'
import type { DocSet } from '@/lib/docs/types'
import { getMDXComponents } from '@/mdx-components'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import type { Metadata } from 'next'
import { MDXRemote } from 'next-mdx-remote/rsc'
import { notFound, redirect } from 'next/navigation'
import { ApiReference } from './api/ApiReference'
import { DocsToc } from './DocsToc'

interface DocArticleProps {
  set: DocSet
  slug: string[]
}

export async function generateDocMetadata(
  set: DocSet,
  slug: string[],
): Promise<Metadata> {
  const doc = await readDoc(set, slug)
  if (!doc) return {}
  const title = doc.frontmatter.title ?? doc.frontmatter.sidebarTitle
  return {
    title,
    description: doc.frontmatter.description,
    // The handbook is auth-gated; keep it out of search indexes.
    ...(set === 'handbook' ? { robots: { index: false, follow: false } } : {}),
  }
}

export async function DocArticle({ set, slug }: DocArticleProps) {
  const doc = await readDoc(set, slug)
  if (!doc) {
    // A section path with no page of its own (e.g. /docs/api-reference) lands on
    // its first child rather than 404ing.
    const sectionChild = firstLeafUnder(await getManifest(set), slug)
    if (sectionChild) redirect(sectionChild)
    notFound()
  }

  const headings = extractHeadings(doc.content)
  const components = getMDXComponents({})
  const { title, description, openapi } = doc.frontmatter

  return (
    <Box
      flexGrow={1}
      justifyContent="center"
      columnGap="2xl"
      paddingHorizontal="xl"
    >
      <Box
        as="article"
        flexDirection="column"
        flexGrow={1}
        maxWidth={768}
        paddingVertical="2xl"
        minWidth={0}
      >
        <Box flexDirection="column" rowGap="s" marginBottom="l">
          {title ? (
            <Text variant="heading-xl" as="h1">
              {title}
            </Text>
          ) : null}
          {description ? (
            <Text color="muted" variant="body">
              {description}
            </Text>
          ) : null}
        </Box>
        {openapi ? <ApiReference operation={openapi} /> : null}
        <ProseWrapper className="w-full max-w-none">
          <MDXRemote
            source={doc.content}
            components={components}
            options={{ mdxOptions: { remarkPlugins, rehypePlugins } }}
          />
        </ProseWrapper>
      </Box>
      <DocsToc headings={headings} />
    </Box>
  )
}
