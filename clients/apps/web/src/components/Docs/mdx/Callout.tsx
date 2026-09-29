import { Box } from '@outception-com/orbit/Box'
import {
  AlertTriangle as AlertTriangleIcon,
  Info as InfoIcon,
  Lightbulb as LightbulbIcon,
  OctagonAlert as OctagonAlertIcon,
  Pencil as PencilIcon,
  type LucideIcon,
} from 'lucide-react'
import type { PropsWithChildren } from 'react'

type CalloutVariant = 'note' | 'info' | 'tip' | 'warning' | 'danger'

interface VariantStyle {
  background: Parameters<typeof Box>[0]['backgroundColor']
  accent: Parameters<typeof Box>[0]['color']
  Icon: LucideIcon
}

const VARIANTS: Record<CalloutVariant, VariantStyle> = {
  note: {
    background: 'background-secondary',
    accent: 'text-secondary',
    Icon: PencilIcon,
  },
  info: {
    background: 'background-pending',
    accent: 'text-pending',
    Icon: InfoIcon,
  },
  tip: {
    background: 'background-success',
    accent: 'text-success',
    Icon: LightbulbIcon,
  },
  warning: {
    background: 'background-warning',
    accent: 'text-warning',
    Icon: AlertTriangleIcon,
  },
  danger: {
    background: 'background-danger',
    accent: 'text-danger',
    Icon: OctagonAlertIcon,
  },
}

const Callout = ({
  variant,
  children,
}: PropsWithChildren<{ variant: CalloutVariant }>) => {
  const { background, accent, Icon } = VARIANTS[variant]
  return (
    <Box
      as="aside"
      backgroundColor={background}
      borderRadius="m"
      paddingVertical="m"
      paddingHorizontal="l"
      columnGap="m"
      alignItems="start"
      marginVertical="l"
    >
      <Box color={accent} paddingTop="xs" flexShrink={0}>
        <Icon size={18} aria-hidden />
      </Box>
      <Box flexDirection="column" minWidth={0}>
        <div className="contents [&>:first-child]:mt-0 [&>:last-child]:mb-0">
          {children}
        </div>
      </Box>
    </Box>
  )
}

export const Note = ({ children }: PropsWithChildren) => (
  <Callout variant="note">{children}</Callout>
)
export const Info = ({ children }: PropsWithChildren) => (
  <Callout variant="info">{children}</Callout>
)
export const Tip = ({ children }: PropsWithChildren) => (
  <Callout variant="tip">{children}</Callout>
)
export const Warning = ({ children }: PropsWithChildren) => (
  <Callout variant="warning">{children}</Callout>
)
export const Danger = ({ children }: PropsWithChildren) => (
  <Callout variant="danger">{children}</Callout>
)
