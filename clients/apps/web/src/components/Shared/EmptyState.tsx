import { Button, Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { ButtonProps } from '@outception-com/orbit/ui/button'
import { ReactNode } from 'react'

interface EmptyStateProps {
  icon: ReactNode
  title: string
  description: string
  actions?: ButtonProps[]
}

export const EmptyState = ({
  icon,
  title,
  description,
  actions,
}: EmptyStateProps) => {
  return (
    <Box
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      gap="s"
      borderRadius="m"
      borderWidth={1}
      borderStyle="solid"
      borderColor="border-primary"
      padding="3xl"
    >
      <div className="dark:text-outception-500 text-5xl text-gray-500">
        {icon}
      </div>
      <Box flexDirection="column" alignItems="center" textAlign="center">
        <Text variant="heading-xxs" as="h3">
          {title}
        </Text>
        <Text color="muted">{description}</Text>
      </Box>
      {(actions?.length ?? 0) > 0 ? (
        <Box marginTop="l" columnGap="l">
          {actions?.map((action, index) => (
            <Button key={index} {...action} />
          ))}
        </Box>
      ) : null}
    </Box>
  )
}
