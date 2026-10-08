'use client'

import { useMyLaunches } from '@/hooks/queries/launches'
import { useT } from '@/providers/translate'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import Link from 'next/link'
import { LaunchActions } from './LaunchActions'
import { LaunchRow } from './LaunchRow'

/** The reader's own submissions with their state, reach, the founder's
 * note when there is one, and what they can do next. */
export const MyLaunches = () => {
  const t = useT()
  const { data, isLoading } = useMyLaunches()
  return (
    <Box flexDirection="column" rowGap="l">
      <Box flexDirection="row" alignItems="center" justifyContent="end">
        <Link href="/launches/new" className="ghost-pill">
          {t('launches.mine.submit')}
        </Link>
      </Box>
      {isLoading ? (
        <Text variant="caption" color="muted">
          {t('news.card.loading')}
        </Text>
      ) : null}
      {!isLoading && (data?.length ?? 0) === 0 ? (
        <Text color="muted">{t('launches.mine.empty')}</Text>
      ) : null}
      {(data ?? []).map((launch) => (
        <LaunchRow key={launch.id} launch={launch}>
          <LaunchActions launch={launch} />
          {launch.reviewer_note ? (
            <Text variant="caption" color="muted" as="p">
              {t('launches.mine.note')}: {launch.reviewer_note}
            </Text>
          ) : null}
        </LaunchRow>
      ))}
    </Box>
  )
}
