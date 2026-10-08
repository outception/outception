'use client'

import { useAuth } from '@/hooks/auth'
import {
  useMyLaunches,
  useMyRace,
  useVisitsRace,
} from '@/hooks/queries/launches'
import { useT } from '@/providers/translate'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import { useMemo, useState } from 'react'
import { ChartRaceCard } from './ChartRaceCard'
import { trimRows, type RaceRow } from './race'

const RANGES = [7, 14, 30] as const
// One empty list, so an absent query result never looks like new data.
const NO_ROWS: readonly RaceRow[] = []
type Range = (typeof RANGES)[number]
type Tab = 'reach' | 'visits'

const Stat = ({ label, value }: { label: string; value: string }) => (
  <Box
    flexDirection="column"
    rowGap="xs"
    padding="l"
    borderRadius="l"
    borderWidth={1}
    borderStyle="solid"
    borderColor="border-primary"
    backgroundColor="background-card"
    flex={1}
    minWidth={140}
  >
    <span className="meta-kicker">{label}</span>
    <Text variant="heading-s" as="span" serif>
      {value}
    </Text>
  </Box>
)

/** The analytics page: the reader's reach as totals and a race, and for
 * the admin list the site's visits by page or country. One place, its own
 * entry in the sidebar, like the dashboard it descends from. */
export const AnalyticsPage = () => {
  const t = useT()
  const { currentUser } = useAuth()
  const isAdmin = !!currentUser?.is_admin
  const [tab, setTab] = useState<Tab>('reach')
  const [range, setRange] = useState<Range>(30)
  const [dimension, setDimension] = useState<'path' | 'country'>('path')
  const { data: mine, isLoading: mineLoading } = useMyLaunches()
  const { data: race, isLoading: raceLoading, isError: raceError } = useMyRace()
  const {
    data: visits,
    isLoading: visitsLoading,
    isError: visitsError,
  } = useVisitsRace(dimension, isAdmin && tab === 'visits')
  const totals = (mine ?? []).reduce(
    (sum, launch) => ({
      views: sum.views + launch.views,
      clicks: sum.clicks + launch.clicks,
    }),
    { views: 0, clicks: 0 },
  )
  const rows: readonly RaceRow[] =
    tab === 'reach' ? (race?.rows ?? NO_ROWS) : (visits?.rows ?? NO_ROWS)
  // Stable until the data or the range changes: the chart rebuilds on a
  // new rows reference, and a fresh array every render would never settle.
  const shown = useMemo(() => trimRows(rows, range), [rows, range])
  const rangeLabel = (days: Range) =>
    days === 7
      ? t('launches.analytics.last7')
      : days === 14
        ? t('launches.analytics.last14')
        : t('launches.analytics.last30')
  return (
    <Box flexDirection="column" rowGap="l">
      <Box
        flexDirection="row"
        alignItems="center"
        justifyContent="between"
        columnGap="m"
        rowGap="s"
        flexWrap="wrap"
      >
        <Box flexDirection="row" columnGap="xs">
          <button
            type="button"
            aria-pressed={tab === 'reach'}
            className="ghost-pill"
            data-solid={tab === 'reach' ? '' : undefined}
            onClick={() => setTab('reach')}
          >
            {t('launches.analytics.reach')}
          </button>
          {isAdmin ? (
            <button
              type="button"
              aria-pressed={tab === 'visits'}
              className="ghost-pill"
              data-solid={tab === 'visits' ? '' : undefined}
              onClick={() => setTab('visits')}
            >
              {t('launches.analytics.visits')}
            </button>
          ) : null}
        </Box>
        <Box flexDirection="row" columnGap="xs">
          {RANGES.map((days) => (
            <button
              key={days}
              type="button"
              className="ghost-pill"
              aria-pressed={range === days}
              data-solid={range === days ? '' : undefined}
              onClick={() => setRange(days)}
            >
              {rangeLabel(days)}
            </button>
          ))}
        </Box>
      </Box>
      {tab === 'reach' ? (
        <Box flexDirection="row" columnGap="m" rowGap="m" flexWrap="wrap">
          <Stat
            label={t('launches.analytics.products')}
            value={mineLoading ? '' : String(mine?.length ?? 0)}
          />
          <Stat
            label={t('launches.race.views')}
            value={mineLoading ? '' : String(totals.views)}
          />
          <Stat
            label={t('launches.race.clicks')}
            value={mineLoading ? '' : String(totals.clicks)}
          />
        </Box>
      ) : null}
      <ChartRaceCard
        id={tab === 'reach' ? 'reach' : 'analytics'}
        rows={shown}
        mode={tab === 'reach' ? (race?.mode ?? 'products') : 'visits'}
        title={
          tab === 'reach'
            ? t('launches.race.title')
            : t('launches.analytics.visits')
        }
        isLoading={tab === 'reach' ? raceLoading : visitsLoading}
        isError={tab === 'reach' ? raceError : visitsError}
        dimension={
          tab === 'visits'
            ? { value: dimension, onChange: setDimension }
            : undefined
        }
        open
      />
    </Box>
  )
}
