import { Box } from '@outception-com/orbit/Box'
import { ChevronRight } from 'lucide-react'
import type { PropsWithChildren } from 'react'

export const Accordion = ({
  title,
  children,
}: PropsWithChildren<{ title?: string }>) => (
  <Box
    borderWidth={1}
    borderStyle="solid"
    borderColor="border-primary"
    borderRadius="m"
    backgroundColor="background-card"
    overflow="hidden"
  >
    <details className="group">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 font-medium [&::-webkit-details-marker]:hidden">
        <ChevronRight
          size={16}
          aria-hidden
          className="transition-transform group-open:rotate-90"
        />
        {title}
      </summary>
      <Box
        paddingHorizontal="l"
        paddingBottom="m"
        flexDirection="column"
        className="[&>:first-child]:mt-0 [&>:last-child]:mb-0"
      >
        {children}
      </Box>
    </details>
  </Box>
)

export const AccordionGroup = ({ children }: PropsWithChildren) => (
  <Box flexDirection="column" rowGap="s" marginVertical="l">
    {children}
  </Box>
)
