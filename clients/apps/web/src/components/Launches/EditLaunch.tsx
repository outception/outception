'use client'

import { useMyLaunches } from '@/hooks/queries/launches'
import { useT } from '@/providers/translate'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import { SubmitLaunchForm } from './SubmitLaunchForm'

/** The submit form filled with one of the reader's own products. */
export const EditLaunch = ({ id }: { id: string }) => {
  const t = useT()
  const { data, isLoading } = useMyLaunches()
  const launch = data?.find((item) => item.id === id)
  if (isLoading) {
    return (
      <Text variant="caption" color="muted">
        {t('news.card.loading')}
      </Text>
    )
  }
  if (!launch) {
    return <Text color="muted">{t('launches.mine.notYours')}</Text>
  }
  return (
    <Box flexDirection="column" rowGap="l">
      <Text variant="heading-s" as="h1">
        {t('launches.submit.editTitle')}
      </Text>
      <SubmitLaunchForm launch={launch} />
    </Box>
  )
}
