import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { Grid } from '@outception-com/orbit'
import {
  Book,
  Bot,
  Building2,
  Github,
  KeyRound,
  Link as LinkGlyph,
  Lock,
  Megaphone,
  Newspaper,
  SquareDashed,
  Users,
  type LucideIcon,
} from 'lucide-react'
import Link from 'next/link'
import type { PropsWithChildren, ReactNode } from 'react'

/** Maps the Mintlify/FontAwesome icon names used in our MDX to lucide icons. */
const ICONS: Record<string, LucideIcon> = {
  newspaper: Newspaper,
  bullhorn: Megaphone,
  book: Book,
  building: Building2,
  key: KeyRound,
  'user-lock': Lock,
  link: LinkGlyph,
  robot: Bot,
  github: Github,
  users: Users,
}

interface CardProps {
  title: string
  icon?: string
  href?: string
}

const CardSurface = ({
  title,
  icon,
  interactive,
  children,
}: PropsWithChildren<CardProps & { interactive: boolean }>) => {
  const Icon = icon ? (ICONS[icon] ?? SquareDashed) : null
  return (
    <Box
      flexDirection="column"
      rowGap="s"
      padding="l"
      height="100%"
      borderWidth={1}
      borderStyle="solid"
      borderColor="border-primary"
      borderRadius="l"
      backgroundColor={
        interactive
          ? { base: 'background-card', hover: 'background-secondary' }
          : 'background-card'
      }
      transitionProperty="colors"
      transitionDuration="fast"
      cursor={interactive ? { hover: 'pointer' } : undefined}
    >
      {Icon ? (
        <Box color="text-secondary">
          <Icon size={20} aria-hidden />
        </Box>
      ) : null}
      <Text variant="heading-xs" as="h3">
        {title}
      </Text>
      {children ? <Text color="muted">{children}</Text> : null}
    </Box>
  )
}

export const Card = ({
  title,
  icon,
  href,
  children,
}: PropsWithChildren<CardProps>) => {
  if (!href) {
    return (
      <CardSurface title={title} icon={icon} interactive={false}>
        {children}
      </CardSurface>
    )
  }
  const external = /^https?:\/\//.test(href)
  return (
    <Link
      href={href}
      {...(external ? { target: '_blank', rel: 'noreferrer' } : {})}
      className="no-underline"
    >
      <CardSurface title={title} icon={icon} interactive>
        {children}
      </CardSurface>
    </Link>
  )
}

export const CardGroup = ({
  cols = 2,
  children,
}: {
  cols?: number
  children?: ReactNode
}) => (
  <Grid
    templateColumns={
      cols >= 3
        ? { base: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }
        : { base: '1fr', md: 'repeat(2, 1fr)' }
    }
    gap="m"
    marginVertical="l"
  >
    {children}
  </Grid>
)
