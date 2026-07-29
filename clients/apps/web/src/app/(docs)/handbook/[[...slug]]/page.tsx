import { DocArticle, generateDocMetadata } from '@/components/Docs/DocArticle'
import { listSlugs } from '@/lib/docs/content'
import type { Metadata } from 'next'

type Params = { slug?: string[] }

export async function generateStaticParams(): Promise<Params[]> {
  const slugs = await listSlugs('handbook')
  return [{ slug: [] }, ...slugs.map((slug) => ({ slug }))]
}

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>
}): Promise<Metadata> {
  const { slug } = await params
  return generateDocMetadata('handbook', slug ?? [])
}

export default async function HandbookPage({
  params,
}: {
  params: Promise<Params>
}) {
  const { slug } = await params
  return <DocArticle set="handbook" slug={slug ?? []} />
}
