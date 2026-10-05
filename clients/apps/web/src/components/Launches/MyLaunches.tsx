'use client'

import { useMyLaunches, useWithdrawLaunch } from '@/hooks/queries/launches'
import { useT } from '@/providers/translate'
import { Button } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import Link from 'next/link'
import { useState } from 'react'
import { LaunchRow } from './LaunchRow'
import { launchStateLabel } from './launchCopy'

/** The reader's own submissions with their state, the founder's note when
 * there is one, and a two-step withdraw. */
export const MyLaunches = () => {
  const t = useT()
  const { data, isLoading } = useMyLaunches()
  const withdraw = useWithdrawLaunch()
  const [confirming, setConfirming] = useState<string | null>(null)
  return (
    <Box flexDirection="column" rowGap="l">
      <Box flexDirection="row" alignItems="center" justifyContent="between">
        <Text variant="heading-xs" as="h1" serif>
          {t('launches.mine.title')}
        </Text>
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
      {(data ?? []).map((launch) => {
        const open = launch.state === 'submitted' || launch.state === 'approved'
        return (
          <LaunchRow key={launch.id} launch={launch}>
            <Box
              flexDirection="row"
              alignItems="center"
              justifyContent="between"
              columnGap="m"
            >
              <span className="meta-kicker">{launchStateLabel(t, launch)}</span>
              {open ? (
                confirming === launch.id ? (
                  <Box flexDirection="row" columnGap="s">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setConfirming(null)}
                    >
                      {t('launches.mine.keep')}
                    </Button>
                    <Button
                      size="sm"
                      disabled={withdraw.isPending}
                      onClick={() => {
                        void withdraw
                          .mutateAsync(launch.id)
                          .finally(() => setConfirming(null))
                      }}
                    >
                      {t('launches.mine.confirmWithdraw')}
                    </Button>
                  </Box>
                ) : (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setConfirming(launch.id)}
                  >
                    {t('launches.mine.withdraw')}
                  </Button>
                )
              ) : null}
            </Box>
            {launch.reviewer_note ? (
              <Text variant="caption" color="muted" as="p">
                {t('launches.mine.note')}: {launch.reviewer_note}
              </Text>
            ) : null}
          </LaunchRow>
        )
      })}
    </Box>
  )
}
