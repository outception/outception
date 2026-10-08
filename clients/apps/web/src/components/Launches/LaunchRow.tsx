'use client'

import { launchGoHref } from '@/hooks/queries/launches'
import { useT } from '@/providers/translate'
import { launchesPath, safeExternalHref } from '@outception-com/news-core'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import Link from 'next/link'
import type { ReactNode } from 'react'
import { kickerLabel, logoSrc } from './launchCopy'

export type RowLaunch = {
  id?: string
  name: string
  tagline: string
  url: string
  logo: string | null
  kicker: string
  description: string
  featured?: boolean
  state?: string
}

/** The site link: through the counting redirect once the product is listed,
 * straight to the site before that (the redirect only knows listed ones). */
export const siteHref = (launch: RowLaunch): string | undefined => {
  const listed = launch.state === 'live' || launch.state === 'ended'
  if (launch.id && listed) return launchGoHref(launch.id)
  return safeExternalHref(launch.url)
}

/** One product as readers see it: logo, name, kind, tagline and the link.
 * The same row serves the archive, the reader's own list and the review
 * preview. The name opens the product's own page when it has one. */
export const LaunchRow = ({
  launch,
  trailing,
  children,
}: {
  launch: RowLaunch
  trailing?: ReactNode
  children?: ReactNode
}) => {
  const t = useT()
  const logo = logoSrc(launch.logo)
  const href = siteHref(launch)
  const name = (
    <Text variant="body" as="h3" serif truncate>
      {launch.name}
    </Text>
  )
  return (
    <Box
      as="article"
      flexDirection="column"
      rowGap="s"
      padding="l"
      borderRadius="l"
      borderWidth={1}
      borderStyle="solid"
      borderColor="border-primary"
      backgroundColor="background-card"
    >
      <Box flexDirection="row" alignItems="center" columnGap="m">
        {logo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={logo}
            alt=""
            width={40}
            height={40}
            loading="lazy"
            style={{ borderRadius: 8, objectFit: 'contain', flexShrink: 0 }}
          />
        ) : (
          <Box
            width={40}
            height={40}
            borderRadius="s"
            backgroundColor="background-secondary"
          />
        )}
        <Box flexDirection="column" rowGap="none" minWidth={0} flexGrow={1}>
          <Box
            flexDirection="row"
            alignItems="center"
            columnGap="s"
            minWidth={0}
          >
            {launch.id ? (
              <Link
                href={`${launchesPath()}/${launch.id}`}
                className="headline-link"
              >
                {name}
              </Link>
            ) : (
              name
            )}
            <span className="meta-kicker">{kickerLabel(t, launch.kicker)}</span>
            {launch.featured ? (
              <span className="meta-kicker">
                {t('launches.archive.featured')}
              </span>
            ) : null}
          </Box>
          <Text variant="caption" color="muted" truncate>
            {launch.tagline}
          </Text>
        </Box>
        {trailing}
        {href ? (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="ghost-pill"
          >
            {t('launches.archive.openSite')}
          </a>
        ) : null}
      </Box>
      {launch.description ? (
        <Text variant="caption" as="p">
          {launch.description}
        </Text>
      ) : null}
      {children}
    </Box>
  )
}
