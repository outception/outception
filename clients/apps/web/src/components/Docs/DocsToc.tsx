import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import type { TocHeading } from '@/lib/docs/types'

export function DocsToc({ headings }: { headings: TocHeading[] }) {
  if (headings.length === 0) return null
  return (
    <Box
      as="nav"
      aria-label="On this page"
      display={{ base: 'none', xl: 'flex' }}
      flexDirection="column"
      rowGap="xs"
      width={200}
      flexShrink={0}
      position="sticky"
      top={88}
      height="fit-content"
      paddingVertical="2xl"
    >
      <Text variant="caption" color="muted">
        On this page
      </Text>
      {headings.map((heading) => (
        <a
          key={heading.id}
          href={`#${heading.id}`}
          className="text-muted-foreground hover:text-foreground text-sm no-underline"
          style={{ paddingLeft: heading.depth === 3 ? 12 : 0 }}
        >
          {heading.title}
        </a>
      ))}
    </Box>
  )
}
