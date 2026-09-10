import { DocArticle, generateDocMetadata } from '@/components/Docs/DocArticle'
import { listSlugs } from '@/lib/docs/content'
import type { Metadata } from 'next'

type Params = { slug?: string[] }

export async function generateStaticParams(): Promise<Params[]> {
  const slugs = await listSlugs('docs')
  return [{ slug: [] }, ...slugs.map((slug) => ({ slug }))]
}

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>
}): Promise<Metadata> {
  const { slug } = await params
  return generateDocMetadata('docs', slug ?? [])
}

export default async function DocsPage({
  params,
}: {
  params: Promise<Params>
}) {
  const { slug } = await params
  return <DocArticle set="docs" slug={slug ?? []} />
}
