'use client'

import { Box } from '@outception-com/orbit/Box'
import {
  Children,
  isValidElement,
  useState,
  type ReactElement,
  type ReactNode,
} from 'react'

const labelFor = (el: ReactElement, index: number): string => {
  const props = el.props as { 'data-code-title'?: string }
  return props['data-code-title']?.trim() || `Snippet ${index + 1}`
}

export const CodeGroup = ({ children }: { children?: ReactNode }) => {
  const tabs = Children.toArray(children).filter(
    isValidElement,
  ) as ReactElement[]
  const [active, setActive] = useState(0)

  if (tabs.length === 0) return null

  return (
    <Box
      flexDirection="column"
      borderWidth={1}
      borderStyle="solid"
      borderColor="border-primary"
      borderRadius="l"
      overflow="hidden"
      marginVertical="l"
    >
      <Box
        as="nav"
        borderBottomWidth={1}
        borderStyle="solid"
        borderColor="border-primary"
        backgroundColor="background-secondary"
        columnGap="xs"
        paddingHorizontal="s"
        overflowX="auto"
      >
        {tabs.map((tab, index) => (
          <Box
            as="label"
            key={tab.key ?? index}
            paddingHorizontal="m"
            paddingVertical="s"
            cursor="pointer"
            borderBottomWidth={2}
            borderStyle="solid"
            borderColor={
              index === active ? 'border-primary' : 'border-secondary'
            }
            color={index === active ? 'text-primary' : 'text-secondary'}
            onClick={() => setActive(index)}
          >
            <span className="text-sm whitespace-nowrap">
              {labelFor(tab, index)}
            </span>
          </Box>
        ))}
      </Box>
      <Box padding="s">
        <div className="contents [&>pre]:my-0 [&>pre]:rounded-none [&>pre]:border-none">
          {tabs[active]}
        </div>
      </Box>
    </Box>
  )
}
