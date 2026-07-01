import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import {
  Children,
  isValidElement,
  type PropsWithChildren,
  type ReactNode,
} from 'react'

export const Step = ({
  title,
  children,
  index,
}: PropsWithChildren<{ title?: string; index?: number }>) => (
  <Box as="li" columnGap="m" alignItems="start">
    <Box
      flexShrink={0}
      width={28}
      height={28}
      borderRadius="full"
      backgroundColor="background-secondary"
      borderWidth={1}
      borderStyle="solid"
      borderColor="border-primary"
      alignItems="center"
      justifyContent="center"
    >
      <Text variant="caption" color="muted">
        {(index ?? 0) + 1}
      </Text>
    </Box>
    <Box
      flexDirection="column"
      rowGap="xs"
      flexGrow={1}
      minWidth={0}
      paddingBottom="m"
    >
      <div className="contents [&>:first-child]:mt-0 [&>:last-child]:mb-0">
        {title ? (
          <Text variant="heading-xs" as="h3">
            {title}
          </Text>
        ) : null}
        {children}
      </div>
    </Box>
  </Box>
)

export const Steps = ({ children }: { children?: ReactNode }) => {
  const steps = Children.toArray(children).filter(isValidElement)
  return (
    <ol className="my-4 flex list-none flex-col pl-0">
      {steps.map((step, index) => (
        <Step
          key={step.key ?? index}
          index={index}
          {...(step.props as { title?: string; children?: ReactNode })}
        />
      ))}
    </ol>
  )
}
