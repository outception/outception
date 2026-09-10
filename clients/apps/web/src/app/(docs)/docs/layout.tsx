import { DocsShell } from '@/components/Docs/DocsShell'
import { getManifest } from '@/lib/docs/manifest'

export default async function DocsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const manifest = await getManifest('docs')
  return <DocsShell manifest={manifest}>{children}</DocsShell>
}
