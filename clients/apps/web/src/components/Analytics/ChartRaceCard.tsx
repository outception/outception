'use client'

import { useT } from '@/providers/translate'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@outception-com/ui/components/ui/dialog'
import Link from 'next/link'
import { useMemo, useRef, useState } from 'react'
import { ChartRace, type RaceInstance } from './ChartRace'
import type { RaceMode, RaceRow } from './race'

export interface ChartRaceCardProps {
  rows: readonly RaceRow[]
  mode: RaceMode
  title: string
  isLoading?: boolean
  /** The numbers could not be fetched: said so, never shown as empty. */
  isError?: boolean
  /** Where the race lives as a card of its own, when this is the strip
   * somewhere else. */
  moreHref?: string
  /** The admin's choice of what the bars are: pages or countries. */
  dimension?: {
    value: 'path' | 'country'
    onChange: (next: 'path' | 'country') => void
  }
  /** Start expanded, for the place that is the chart's own card. */
  open?: boolean
  id?: string
}

/** The race in the glass: a tiny strip by default, a readable panel when
 * expanded in place, and a full-screen sheet on request. Only one race is
 * mounted at a time, so two never run together. The play control is the
 * card's own button, so it works from the keyboard. */
export const ChartRaceCard = ({
  rows,
  mode,
  title,
  isLoading,
  isError,
  moreHref,
  dimension,
  open = false,
  id,
}: ChartRaceCardProps) => {
  const t = useT()
  const [expanded, setExpanded] = useState(open)
  const [sheet, setSheet] = useState(false)
  const [race, setRace] = useState<RaceInstance | null>(null)
  const [playing, setPlaying] = useState(false)
  const fullScreen = useRef<HTMLButtonElement>(null)
  // Stable between renders: the chart rebuilds when its inputs change, and
  // a fresh object every render would count as a change.
  const labels = useMemo(
    () => ({
      views: t('launches.race.views'),
      clicks: t('launches.race.clicks'),
    }),
    [t],
  )
  const empty = !isLoading && !isError && rows.length === 0
  const chart = (size: 'strip' | 'panel' | 'sheet') => (
    <ChartRace
      rows={rows}
      mode={mode}
      size={size}
      labels={labels}
      title={title}
      onInstance={setRace}
      onPlaying={setPlaying}
    />
  )
  const playControl =
    race && (expanded || sheet) ? (
      <button
        type="button"
        className="ghost-pill"
        aria-pressed={playing}
        onClick={() => (playing ? race.pause() : race.play())}
      >
        {playing ? t('launches.race.pause') : t('launches.race.play')}
      </button>
    ) : null
  const sheetDialog = (
    <Dialog open={sheet} onOpenChange={setSheet}>
      <DialogContent
        overlayClassName="paper-veil"
        className="paper-sheet chart-race-sheet h-dvh w-dvw max-w-none rounded-none border-0 p-6 text-black dark:text-white"
        aria-describedby={undefined}
        onCloseAutoFocus={(event) => {
          const target = fullScreen.current
          if (target) {
            event.preventDefault()
            target.focus()
          }
        }}
      >
        <Box
          flexDirection="row"
          alignItems="center"
          justifyContent="between"
          columnGap="m"
        >
          <DialogTitle className="meta-kicker">{title}</DialogTitle>
          {playControl}
        </Box>
        {sheet && rows.length > 0 ? chart('sheet') : null}
      </DialogContent>
    </Dialog>
  )
  return (
    <Box as="section" id={id} flexDirection="column" rowGap="s">
      <Box
        flexDirection="row"
        alignItems="center"
        justifyContent="between"
        columnGap="m"
        rowGap="xs"
        flexWrap="wrap"
      >
        <span className="meta-kicker">{title}</span>
        <Box
          flexDirection="row"
          columnGap="xs"
          alignItems="center"
          flexWrap="wrap"
        >
          {dimension ? (
            <button
              type="button"
              className="ghost-pill"
              onClick={() =>
                dimension.onChange(
                  dimension.value === 'path' ? 'country' : 'path',
                )
              }
            >
              {dimension.value === 'path'
                ? t('launches.race.countries')
                : t('launches.race.pages')}
            </button>
          ) : null}
          {empty || isError ? null : (
            <>
              {sheet ? null : playControl}
              <button
                type="button"
                className="ghost-pill"
                aria-expanded={expanded}
                onClick={() => setExpanded((value) => !value)}
              >
                {expanded
                  ? t('launches.race.collapse')
                  : t('launches.race.expand')}
              </button>
              <button
                ref={fullScreen}
                type="button"
                className="ghost-pill"
                onClick={() => setSheet(true)}
              >
                {t('launches.race.fullScreen')}
              </button>
              {moreHref ? (
                <Link href={moreHref} className="ghost-pill">
                  {t('launches.race.ownCard')}
                </Link>
              ) : null}
            </>
          )}
        </Box>
      </Box>
      {isLoading ? (
        <Text variant="caption" color="muted">
          {t('news.card.loading')}
        </Text>
      ) : null}
      {isError ? (
        <Text variant="caption" color="muted">
          {t('launches.race.error')}
        </Text>
      ) : null}
      {empty ? (
        <Text variant="caption" color="muted">
          {t('launches.race.empty')}
        </Text>
      ) : null}
      {rows.length > 0 && !sheet ? chart(expanded ? 'panel' : 'strip') : null}
      {sheetDialog}
    </Box>
  )
}
