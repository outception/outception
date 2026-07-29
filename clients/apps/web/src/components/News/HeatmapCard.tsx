'use client'

import { useNewsHeatmap } from '@/hooks/queries/news'
import { useLocale, useT } from '@/providers/locale'
import {
  safeExternalHref,
  type NewsHeatmapTile,
  type NewsSourceMeta,
} from '@/utils/news'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import OutceptionTimeAgo from '@outception-com/ui/components/atoms/OutceptionTimeAgo'
import { useEffect, useMemo, useRef, useState } from 'react'
import { FollowButton } from './FollowButton'
import { ShareButton } from './ShareButton'
import { SourceBadge } from './SourceBadge'
import { useNewsColumn } from './NewsColumnContext'
import { squarify } from './squarify'

/** Every tile uses the finviz/TradingView language — solid green for gains,
 * red for losses, brighter with magnitude, neutral slate at exactly 0.
 * changePercent carries the right signal for every map kind: day's move for
 * markets, form/streak for standings, rank trend for polls, freshness for
 * buzz. Mirrored in the mobile HeatmapCard. */
const HEAT_NEUTRAL_RGB = [65, 69, 84]
const HEAT_GAIN_RGB = [38, 189, 82]
const HEAT_LOSS_RGB = [242, 54, 69]

/** |change| at which a tile reaches full heat — beyond ±3% everything reads
 * as "a big day" anyway. The 0.45 power stretches small moves: ±0.2% must
 * already read clearly green/red, like the reference heatmaps, not blend
 * into the neutral slate. */
const FULL_HEAT_PERCENT = 3

const heatBackground = (change: number): string => {
  if (change === 0) return `rgb(${HEAT_NEUTRAL_RGB.join(', ')})`
  const anchor = change > 0 ? HEAT_GAIN_RGB : HEAT_LOSS_RGB
  const heat = Math.pow(Math.min(Math.abs(change) / FULL_HEAT_PERCENT, 1), 0.45)
  // High floor: TradingView tiles read unmistakably green/red even at ±0.2% —
  // only an exact 0.00% stays neutral.
  const strength = 0.45 + 0.55 * heat
  const mixed = HEAT_NEUTRAL_RGB.map((neutral, i) =>
    Math.round(neutral + (anchor[i] - neutral) * strength),
  )
  return `rgb(${mixed.join(', ')})`
}

/** Treemap areas use square-root-dampened weights with a 32%-of-map cap:
 * proportional market caps let one giant (BTC, NVDA) swallow half the card
 * and crush the tail into slivers. Dampening keeps rank order — the biggest
 * is still clearly the biggest — while every listed tile stays readable. */
const dampenWeights = (weights: number[]): number[] => {
  let damped = weights.map((weight) => Math.sqrt(Math.max(weight, 0)))
  for (let pass = 0; pass < 2; pass++) {
    const total = damped.reduce((sum, weight) => sum + weight, 0)
    if (total <= 0) return damped
    const cap = total * 0.32
    damped = damped.map((weight) => Math.min(weight, cap))
  }
  return damped
}

/** Where a tapped tile leads: the symbol's public quote page. Crypto symbols
 * chart as pairs (BTC-USD); listed stocks by bare ticker. */
const quoteUrl = (heatmapId: string, symbol: string): string =>
  heatmapId === 'heatmap-crypto'
    ? `https://finance.yahoo.com/quote/${encodeURIComponent(symbol)}-USD`
    : `https://finance.yahoo.com/quote/${encodeURIComponent(symbol)}`

/**
 * A market heatmap panel: the roster source's tiles as a squarified treemap —
 * area by market cap, color by day's move. Mirrors NewsSourceCard's chrome
 * (badge header, follow/share) and renders bare like it: the SwipeDeckCard
 * wrapper owns the paper surface.
 */
export const HeatmapCard = ({
  source,
  active = true,
}: {
  source: NewsSourceMeta
  active?: boolean
}) => {
  const { markFailed, markLoaded } = useNewsColumn()
  const t = useT()
  const locale = useLocale()
  const { data, isLoading, isError, errorUpdateCount, dataUpdatedAt } =
    useNewsHeatmap(source.id, active)
  const boxRef = useRef<HTMLDivElement>(null)
  const [box, setBox] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const el = boxRef.current
    if (!el) return
    const measure = () =>
      setBox((prev) =>
        prev.width === el.clientWidth && prev.height === el.clientHeight
          ? prev
          : { width: el.clientWidth, height: el.clientHeight },
      )
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const tiles = useMemo(
    () => [...(data?.tiles ?? [])].sort((a, b) => b.weight - a.weight),
    [data?.tiles],
  )
  const rects = useMemo(
    () =>
      squarify(
        dampenWeights(tiles.map((tile) => tile.weight)),
        box.width,
        box.height,
      ),
    [tiles, box.width, box.height],
  )

  // Same deck-hygiene contract as NewsSourceCard: a heatmap whose upstream is
  // dead (or served empty) drops off the wall instead of showing a husk.
  const isEmpty = Boolean(data) && tiles.length === 0
  // errorUpdateCount/dataUpdatedAt in the deps for the same reason as
  // NewsSourceCard: else the strike effect fires once and sticks at 1, so a
  // persistently dead/empty map never reaches the drop threshold.
  useEffect(() => {
    if (isError || isEmpty) markFailed(source.id)
    else if (data) markLoaded(source.id)
  }, [
    isError,
    isEmpty,
    data,
    errorUpdateCount,
    dataUpdatedAt,
    source.id,
    markFailed,
    markLoaded,
  ])

  const tileLabel = (tile: NewsHeatmapTile, width: number, height: number) => {
    // Every tile that can physically hold type gets its symbol and number —
    // an unlabeled colored square reads as a bug, not a stock. Small tiles
    // step the type down instead of dropping it.
    if (width < 26 || height < 16) return null
    const tiny = width < 48 || height < 34
    // Server labels may carry a note after " · " ("85 pts · 25/26 final") —
    // it renders as its own smaller second row instead of truncating.
    const [labelMain, labelNote] = tile.label
      ? tile.label.split(' · ', 2)
      : [undefined, undefined]
    // Brand mark like the reference heatmaps, on tiles with room for it.
    const logo = safeExternalHref(tile.logo ?? undefined)
    const showLogo = Boolean(logo) && width >= 56 && height >= 64
    const logoSize = width >= 120 && height >= 120 ? 32 : 20
    // Tiles are solid green/red/slate at every heat, so text is always white.
    return (
      <Box
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        rowGap={tiny ? 'none' : 'xs'}
        height="100%"
      >
        {showLogo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={logo}
            alt=""
            aria-hidden
            width={logoSize}
            height={logoSize}
            loading="lazy"
            style={{ objectFit: 'contain' }}
          />
        ) : null}
        <span
          className="meta-kicker"
          style={{
            color: 'rgba(255, 255, 255, 0.92)',
            ...(tiny ? { fontSize: 8, letterSpacing: 0.4 } : null),
            maxWidth: '100%',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {tile.symbol}
        </span>
        {height >= 34 ? (
          <span
            style={{
              color: 'rgba(255, 255, 255, 0.85)',
              fontSize: tiny ? 8 : 12,
              lineHeight: 1.2,
              maxWidth: '100%',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {labelMain ??
              `${tile.changePercent > 0 ? '+' : ''}${tile.changePercent.toFixed(2)}%`}
          </span>
        ) : null}
        {labelNote && height >= 48 ? (
          <span
            style={{
              color: 'rgba(255, 255, 255, 0.6)',
              fontSize: tiny ? 7 : 10,
              lineHeight: 1.2,
              maxWidth: '100%',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {labelNote}
          </span>
        ) : null}
      </Box>
    )
  }

  return (
    <Box
      flexDirection="column"
      rowGap="m"
      height="100%"
      padding={{ base: 'l', md: 'xl' }}
    >
      <Box
        flexDirection="row"
        alignItems="center"
        justifyContent="between"
        columnGap="s"
      >
        <Box
          flexDirection="row"
          alignItems="center"
          columnGap="s"
          flexShrink={1}
          minWidth={0}
        >
          <a
            href={safeExternalHref(source.home)}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={source.name}
            style={{ flexShrink: 0, lineHeight: 0 }}
          >
            <SourceBadge
              id={source.id}
              name={source.name}
              logo={source.logo}
              size={32}
            />
          </a>
          <Box flexDirection="column" rowGap="none" minWidth={0}>
            <Box
              flexDirection="row"
              alignItems="center"
              columnGap="s"
              minWidth={0}
            >
              <span
                aria-hidden
                style={{
                  display: 'inline-block',
                  width: 8,
                  height: 8,
                  flexShrink: 0,
                  borderRadius: 9999,
                  backgroundColor: source.color,
                }}
              />
              <Text variant="body" as="h3" serif truncate>
                {source.name.endsWith(' Table')
                  ? source.name.slice(0, -' Table'.length)
                  : source.name}
              </Text>
            </Box>
            <span className="meta-kicker">
              {source.name.endsWith(' Table') ? '' : null}
              {data?.updatedTime ? (
                <>
                  {t('news.card.updated')}{' '}
                  <OutceptionTimeAgo
                    date={data.updatedTime}
                    minPeriod={60}
                    locale={locale}
                  />
                </>
              ) : isError ? (
                t('news.card.failed')
              ) : (
                t('news.card.loading')
              )}
            </span>
          </Box>
        </Box>
        <Box
          flexDirection="row"
          alignItems="center"
          columnGap="s"
          flexShrink={0}
        >
          <ShareButton source={source} />
          <FollowButton sourceId={source.id} />
        </Box>
      </Box>

      <Box
        flex={1}
        minHeight={0}
        overflow="hidden"
        position="relative"
        borderRadius="m"
      >
        <div ref={boxRef} style={{ position: 'absolute', inset: 0 }}>
          {isLoading ? (
            <div className="animate-pulse" style={{ height: '100%' }}>
              <Box
                height="100%"
                borderRadius="m"
                backgroundColor="background-card"
              />
            </div>
          ) : tiles.length === 0 ? (
            <Text variant="caption" color="muted">
              {t('news.card.failed')}
            </Text>
          ) : (
            tiles.map((tile, i) => {
              const rect = rects[i]
              // `!(> 1)` so a NaN dimension fails closed instead of styling.
              if (!rect || !(rect.width > 1) || !(rect.height > 1)) return null
              return (
                <a
                  key={`${tile.symbol}-${i}`}
                  className="heatmap-tile"
                  href={safeExternalHref(
                    // Labelled tiles (sports grids) have no meaningful quote
                    // page — without a server URL the anchor stays inert.
                    tile.url ??
                      (tile.label
                        ? undefined
                        : quoteUrl(source.id, tile.symbol)),
                  )}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`${tile.name} ${tile.changePercent}%`}
                  style={{
                    position: 'absolute',
                    left: rect.x,
                    top: rect.y,
                    width: rect.width,
                    height: rect.height,
                    backgroundColor: heatBackground(tile.changePercent),
                    outline: '1px solid var(--color-paper-sheet, #fffdf7)',
                    overflow: 'hidden',
                  }}
                >
                  {tileLabel(tile, rect.width, rect.height)}
                </a>
              )
            })
          )}
        </div>
      </Box>
    </Box>
  )
}
