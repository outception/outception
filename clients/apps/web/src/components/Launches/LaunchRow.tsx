'use client'

import { useT } from '@/providers/translate'
import { safeExternalHref } from '@outception-com/news-core'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import type { ReactNode } from 'react'
import { kickerLabel, logoSrc } from './launchCopy'

/** One product as readers see it: logo, name, kind, tagline and the link.
 * The same row serves the archive, the reader's own list and the review
 * preview. */
export const LaunchRow = ({
  launch,
  trailing,
  children,
}: {
  launch: {
    name: string
    tagline: string
    url: string
    logo: string | null
    kicker: string
    description: string
    featured?: boolean
  }
  trailing?: ReactNode
  children?: ReactNode
}) => {
  const t = useT()
  const logo = logoSrc(launch.logo)
  const href = safeExternalHref(launch.url)
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
            <Text variant="body" as="h3" serif truncate>
              {launch.name}
            </Text>
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
            {t('launches.archive.visit')}
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
