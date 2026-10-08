'use client'

import { ChartRaceCard } from '@/components/Analytics/ChartRaceCard'
import { useAuth } from '@/hooks/auth'
import { useLaunch, useMyLaunches, useMyRace } from '@/hooks/queries/launches'
import { useT } from '@/providers/translate'
import { launchesPath } from '@outception-com/news-core'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import Link from 'next/link'
import { LaunchActions } from './LaunchActions'
import { siteHref } from './LaunchRow'
import { formatDay, kickerLabel, logoSrc } from './launchCopy'

/** Everything about one product: logo, name, kind, tagline, blurb, its day
 * and the link. The submitter also sees its reach and their actions. */
export const ProductPage = ({ id }: { id: string }) => {
  const t = useT()
  const { authenticated } = useAuth()
  const { data: launch, isLoading, isError } = useLaunch(id)
  const { data: mine } = useMyLaunches(authenticated)
  const own = mine?.find((item) => item.id === id) ?? null
  const {
    data: race,
    isLoading: raceLoading,
    isError: raceError,
  } = useMyRace(own !== null)
  return (
    <Box
      as="section"
      flexDirection="column"
      rowGap="l"
      paddingHorizontal="xl"
      paddingVertical="l"
      width="100%"
      maxWidth={720}
      marginHorizontal="auto"
    >
      <Link href={launchesPath()} className="headline-link w-fit">
        <Text variant="caption" as="span">
          {t('launches.archive.back')}
        </Text>
      </Link>
      {isLoading ? (
        <Text variant="caption" color="muted">
          {t('news.card.loading')}
        </Text>
      ) : null}
      {isError || (!isLoading && !launch) ? (
        <Text color="muted">{t('launches.product.notFound')}</Text>
      ) : null}
      {launch ? (
        <Box
          flexDirection="column"
          rowGap="l"
          padding="xl"
          borderRadius="l"
          borderWidth={1}
          borderStyle="solid"
          borderColor="border-primary"
          backgroundColor="background-card"
        >
          <Box flexDirection="row" alignItems="center" columnGap="l">
            {logoSrc(launch.logo) ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={logoSrc(launch.logo)}
                alt=""
                width={64}
                height={64}
                style={{
                  borderRadius: 12,
                  objectFit: 'contain',
                  flexShrink: 0,
                }}
              />
            ) : (
              <Box
                width={64}
                height={64}
                borderRadius="m"
                backgroundColor="background-secondary"
              />
            )}
            <Box flexDirection="column" rowGap="xs" minWidth={0}>
              <Box flexDirection="row" alignItems="center" columnGap="s">
                <Text variant="heading-s" as="h1" serif>
                  {launch.name}
                </Text>
                <span className="meta-kicker">
                  {kickerLabel(t, launch.kicker)}
                </span>
                {launch.featured ? (
                  <span className="meta-kicker">
                    {t('launches.archive.featured')}
                  </span>
                ) : null}
              </Box>
              <Text color="muted">{launch.tagline}</Text>
            </Box>
          </Box>
          {launch.description ? <Text as="p">{launch.description}</Text> : null}
          <Box
            flexDirection="row"
            alignItems="center"
            justifyContent="between"
            columnGap="m"
            rowGap="s"
            flexWrap="wrap"
          >
            <Text variant="caption" color="muted" as="span">
              {launch.day
                ? t('launches.product.day', { day: formatDay(launch.day) })
                : ''}
            </Text>
            {siteHref(launch) ? (
              <a
                href={siteHref(launch)}
                target="_blank"
                rel="noopener noreferrer"
                className="ghost-pill"
                data-solid=""
              >
                {t('launches.archive.openSite')}
              </a>
            ) : null}
          </Box>
          {own ? (
            <Box
              flexDirection="column"
              rowGap="m"
              paddingTop="l"
              borderTopWidth={1}
              borderStyle="solid"
              borderColor="border-secondary"
            >
              <LaunchActions launch={own} />
              <ChartRaceCard
                rows={race?.rows ?? []}
                mode={race?.mode ?? 'reach'}
                title={t('launches.race.title')}
                isLoading={raceLoading}
                isError={raceError}
                moreHref={`${launchesPath()}/analytics`}
              />
            </Box>
          ) : null}
        </Box>
      ) : null}
    </Box>
  )
}
