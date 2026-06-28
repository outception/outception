'use client'

import { Button, Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import type { DocsManifest } from '@/lib/docs/types'
import Link from 'next/link'
import type { PropsWithChildren } from 'react'
import { DocsSearch } from './DocsSearch'
import { DocsSidebar } from './DocsSidebar'
import { ThemeToggle } from './ThemeToggle'

export function DocsShell({
  manifest,
  children,
}: PropsWithChildren<{ manifest: DocsManifest }>) {
  return (
    <Box flexDirection="column" minHeight="100vh" backgroundColor="background-primary">
      <Box
        as="header"
        position="sticky"
        top={0}
        zIndex={20}
        height={64}
        alignItems="center"
        columnGap="l"
        paddingHorizontal="xl"
        borderBottomWidth={1}
        borderStyle="solid"
        borderColor="border-primary"
        backgroundColor="background-primary"
      >
        <Link href={manifest.basePath} className="no-underline">
          <Text variant="label" color="default">
            Outception {manifest.set === 'handbook' ? 'Handbook' : 'Docs'}
          </Text>
        </Link>
        <Box flexGrow={1} />
        <DocsSearch set={manifest.set} basePath={manifest.basePath} />
        <ThemeToggle />
        <Link href="/" className="no-underline">
          <Button variant="secondary" size="sm">
            Dashboard
          </Button>
        </Link>
      </Box>

      <Box flexGrow={1}>
        <DocsSidebar manifest={manifest} />
        <Box as="main" flexGrow={1} minWidth={0}>
          {children}
        </Box>
      </Box>
    </Box>
  )
}
