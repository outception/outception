import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit'
import { type ReactNode } from 'react'

export function Section({
  title,
  description,
  children,
}: {
  title?: string
  description?: ReactNode
  children: ReactNode
}) {
  return (
    <Box as="section" flexDirection="column" rowGap="xl" marginBottom="4xl">
      {(title || description) && (
        <Box flexDirection="column" rowGap="s">
          {title && (
            <Text variant="heading-xs" as="h2">
              {title}
            </Text>
          )}
          {description && (
            <Text variant="body" color="default">
              {description}
            </Text>
          )}
        </Box>
      )}
      {children}
    </Box>
  )
}

export function Prose({ children }: { children: ReactNode }) {
  return (
    <Box flexDirection="column" rowGap="m">
      {children}
    </Box>
  )
}
