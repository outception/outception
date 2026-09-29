import { DocsShell } from '@/components/Docs/DocsShell'
import { getManifest } from '@/lib/docs/manifest'

export default async function HandbookLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const manifest = await getManifest('handbook')
  return <DocsShell manifest={manifest}>{children}</DocsShell>
}
