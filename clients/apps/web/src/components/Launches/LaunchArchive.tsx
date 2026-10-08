'use client'

import { useLaunchArchive } from '@/hooks/queries/launches'
import { useT } from '@/providers/translate'
import { launchesPath } from '@outception-com/news-core'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import Link from 'next/link'
import { LaunchRow } from './LaunchRow'
import { formatDay, todayKey } from './launchCopy'

/** Every day's products, newest first, with the house line and the way to
 * submit one. */
export const LaunchArchive = () => {
  const t = useT()
  const { data, isLoading } = useLaunchArchive()
  const today = todayKey()
  return (
    <Box
      as="section"
      flexDirection="column"
      rowGap="xl"
      paddingHorizontal="xl"
      paddingVertical="l"
      width="100%"
      maxWidth={720}
      marginHorizontal="auto"
    >
      <Box flexDirection="column" rowGap="xs">
        <Text variant="heading-s" as="h1" serif>
          {t('launches.archive.title')}
        </Text>
        <Text variant="caption" color="muted">
          {t('launches.archive.intro')}
        </Text>
        <Box
          flexDirection="row"
          columnGap="s"
          alignItems="center"
          flexWrap="wrap"
        >
          <Text variant="caption" color="muted" as="span">
            {t('news.products.house')}
          </Text>
          <Link href={`${launchesPath()}/new`} className="headline-link">
            <Text variant="caption" as="span">
              {t('news.products.submit')}
            </Text>
          </Link>
        </Box>
      </Box>
      {isLoading ? (
        <Text variant="caption" color="muted">
          {t('news.card.loading')}
        </Text>
      ) : null}
      {!isLoading && (data?.days.length ?? 0) === 0 ? (
        <Text color="muted">{t('launches.archive.empty')}</Text>
      ) : null}
      {(data?.days ?? []).map((day) => (
        <Box as="section" key={day.day} flexDirection="column" rowGap="m">
          <Text variant="heading-xxs" as="h2" serif>
            {day.day === today
              ? t('launches.archive.today')
              : formatDay(day.day)}
          </Text>
          <Box flexDirection="column" rowGap="m">
            {day.items.map((launch) => (
              <LaunchRow key={launch.id} launch={launch} />
            ))}
          </Box>
        </Box>
      ))}
    </Box>
  )
}
