'use client'

import {
  useDeleteLaunch,
  useWithdrawLaunch,
  type MyLaunch,
} from '@/hooks/queries/launches'
import { useT } from '@/providers/translate'
import { launchesPath } from '@outception-com/news-core'
import { Button } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import Link from 'next/link'
import { useState } from 'react'
import { launchStateLabel } from './launchCopy'

const EDITABLE = new Set(['submitted', 'withdrawn', 'rejected'])
const WITHDRAWABLE = new Set(['submitted', 'approved'])
const DELETABLE = new Set(['submitted', 'withdrawn', 'rejected', 'ended'])

/** The state line, the reach, and what the submitter can do next: edit
 * while nothing is listed, withdraw while waiting or approved, delete once
 * it is off any day. The second step of withdraw and delete asks first. */
export const LaunchActions = ({ launch }: { launch: MyLaunch }) => {
  const t = useT()
  const withdraw = useWithdrawLaunch()
  const remove = useDeleteLaunch()
  const [confirming, setConfirming] = useState<'withdraw' | 'delete' | null>(
    null,
  )
  const busy = withdraw.isPending || remove.isPending
  const reach = t('launches.mine.reach', {
    views: String(launch.views),
    clicks: String(launch.clicks),
  })
  return (
    <Box
      flexDirection="row"
      alignItems="center"
      justifyContent="between"
      columnGap="m"
      rowGap="s"
      flexWrap="wrap"
    >
      <Box flexDirection="column" rowGap="xs">
        <span className="meta-kicker">{launchStateLabel(t, launch)}</span>
        <Text variant="caption" color="muted" as="span">
          {reach}
        </Text>
      </Box>
      {confirming ? (
        <Box flexDirection="row" columnGap="s" alignItems="center">
          <Text variant="caption" as="span">
            {confirming === 'withdraw'
              ? t('launches.mine.confirmWithdraw')
              : t('launches.mine.confirmDelete')}
          </Text>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setConfirming(null)}
          >
            {t('launches.mine.keep')}
          </Button>
          <Button
            size="sm"
            disabled={busy}
            onClick={() => {
              const action =
                confirming === 'withdraw'
                  ? withdraw.mutateAsync(launch.id)
                  : remove.mutateAsync(launch.id)
              void action.finally(() => setConfirming(null))
            }}
          >
            {confirming === 'withdraw'
              ? t('launches.mine.withdraw')
              : t('launches.mine.delete')}
          </Button>
        </Box>
      ) : (
        <Box flexDirection="row" columnGap="s" alignItems="center">
          {EDITABLE.has(launch.state) ? (
            <Link
              href={`${launchesPath()}/${launch.id}/edit`}
              className="ghost-pill"
            >
              {t('launches.mine.edit')}
            </Link>
          ) : null}
          {WITHDRAWABLE.has(launch.state) ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setConfirming('withdraw')}
            >
              {t('launches.mine.withdraw')}
            </Button>
          ) : null}
          {DELETABLE.has(launch.state) ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setConfirming('delete')}
            >
              {t('launches.mine.delete')}
            </Button>
          ) : null}
        </Box>
      )}
    </Box>
  )
}
