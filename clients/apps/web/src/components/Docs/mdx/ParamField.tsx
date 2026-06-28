import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import type { PropsWithChildren } from 'react'

interface ParamFieldProps {
  /** Mintlify exposes the parameter name under one of these depending on location. */
  path?: string
  query?: string
  body?: string
  header?: string
  type?: string
  required?: boolean
  default?: string
}

export const ParamField = ({
  path,
  query,
  body,
  header,
  type,
  required,
  default: defaultValue,
  children,
}: PropsWithChildren<ParamFieldProps>) => {
  const name = path ?? query ?? body ?? header
  return (
    <Box
      flexDirection="column"
      rowGap="xs"
      paddingVertical="m"
      borderBottomWidth={1}
      borderStyle="solid"
      borderColor="border-secondary"
    >
      <Box alignItems="baseline" columnGap="s" flexWrap="wrap">
        {name ? <code className="font-mono text-sm font-medium">{name}</code> : null}
        {type ? (
          <Text variant="caption" color="muted">
            {type}
          </Text>
        ) : null}
        {required ? (
          <Text variant="caption" color="danger">
            required
          </Text>
        ) : null}
        {defaultValue ? (
          <Text variant="caption" color="muted">
            default: {defaultValue}
          </Text>
        ) : null}
      </Box>
      {children ? (
        <Box
          flexDirection="column"
          className="[&>:first-child]:mt-0 [&>:last-child]:mb-0"
        >
          {children}
        </Box>
      ) : null}
    </Box>
  )
}
