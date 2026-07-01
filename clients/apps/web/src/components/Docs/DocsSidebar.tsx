'use client'

import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import type { DocsManifest, NavNode } from '@/lib/docs/types'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

function NavTree({ nodes, depth = 0 }: { nodes: NavNode[]; depth?: number }) {
  const pathname = usePathname()
  return (
    <ul className="flex list-none flex-col gap-1 pl-0">
      {nodes.map((node, index) => {
        if (node.kind === 'group') {
          return (
            <Box
              as="li"
              key={`${node.title}-${index}`}
              flexDirection="column"
              rowGap="xs"
            >
              <div className="tracking-wide uppercase">
                <Text variant="caption" color="muted">
                  {node.title}
                </Text>
              </div>
              <NavTree nodes={node.items} depth={depth + 1} />
            </Box>
          )
        }
        const active = pathname === node.href
        return (
          <Box as="li" key={node.href}>
            <Link href={node.href} className="no-underline">
              <Box
                paddingVertical="xs"
                paddingHorizontal="s"
                borderRadius="s"
                backgroundColor={
                  active
                    ? 'background-secondary'
                    : {
                        base: 'background-primary',
                        hover: 'background-secondary',
                      }
                }
                color={active ? 'text-primary' : 'text-secondary'}
              >
                <Text variant="label" color={active ? 'default' : 'muted'}>
                  {node.title}
                </Text>
              </Box>
            </Link>
          </Box>
        )
      })}
    </ul>
  )
}

export function DocsSidebar({ manifest }: { manifest: DocsManifest }) {
  const multiTab = manifest.tabs.length > 1
  return (
    <Box
      as="nav"
      aria-label={`${manifest.name} navigation`}
      display={{ base: 'none', md: 'flex' }}
      flexDirection="column"
      rowGap="l"
      width={260}
      flexShrink={0}
      position="sticky"
      top={64}
      height="calc(100vh - 64px)"
      overflowY="auto"
      paddingVertical="xl"
      paddingHorizontal="l"
      borderRightWidth={1}
      borderStyle="solid"
      borderColor="border-primary"
    >
      {manifest.tabs.map((tab, index) => (
        <Box key={`${tab.title}-${index}`} flexDirection="column" rowGap="s">
          {multiTab ? (
            <Text variant="label" color="default">
              {tab.title}
            </Text>
          ) : null}
          <NavTree nodes={tab.items} />
        </Box>
      ))}
    </Box>
  )
}
