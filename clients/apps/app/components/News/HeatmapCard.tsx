import { Box } from '@/components/Shared/Box'
import { Image } from '@/components/Shared/Image/Image'
import { PlaceholderBox } from '@/components/Shared/PlaceholderBox'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'

import { useTheme } from '@/design-system/useTheme'
import {
  useNewsHeatmap,
  type NewsHeatmapTile,
  type NewsSourceMeta,
} from '@/hooks/outception/news'
import { useLocale, useT } from '@/providers/LocaleProvider'
import { markFailed, markLoaded } from '@/utils/failedSources'
import { openExternalUrl, timeAgo } from '@/utils/news'
import { useIsRestoring } from '@tanstack/react-query'
import { memo, useEffect, useMemo, useState } from 'react'
import { FollowButton } from './FollowButton'
import { useMinuteNow } from './NewsSourceCard'
import { ShareButton } from './ShareButton'
import { KICKER_STYLE } from './newsStyles'
import { SourceAccentTab } from './SourceAccentTab'
import { SourceBadge } from './SourceBadge'
import { squarify } from './squarify'

/** Every tile uses the finviz/TradingView language - solid green for gains,
 * red for losses, brighter with magnitude, neutral slate at exactly 0.
 * changePercent carries the right signal for every map kind: day's move for
 * markets, form/streak for standings, rank trend for polls, freshness for
 * buzz. Mirrors the web HeatmapCard. */
const HEAT_NEUTRAL_RGB = [65, 69, 84]
const HEAT_GAIN_RGB = [38, 189, 82]
const HEAT_LOSS_RGB = [242, 54, 69]
const HEAT_TEXT = 'rgba(255, 255, 255, 0.92)'
const HEAT_TEXT_FAINT = 'rgba(255, 255, 255, 0.6)'
const LOGO_GAP = 2
/** Small tiles step type down instead of dropping their labels. */
const TINY_KICKER_STYLE = { fontSize: 8, letterSpacing: 0.4, lineHeight: 10 }
const TINY_VALUE_STYLE = { fontSize: 8, lineHeight: 10 }
/** The quieter second label row ("25/26 final"). */
const NOTE_STYLE = { color: HEAT_TEXT_FAINT, fontSize: 10, lineHeight: 12 }

/** |change| at which a tile reaches full heat; the 0.45 power stretches
 * small moves so ±0.2% already reads clearly green/red. */
const FULL_HEAT_PERCENT = 3

const heatBackground = (change: number): string => {
  if (change === 0) return `rgb(${HEAT_NEUTRAL_RGB.join(', ')})`
  const anchor = change > 0 ? HEAT_GAIN_RGB : HEAT_LOSS_RGB
  const heat = Math.pow(Math.min(Math.abs(change) / FULL_HEAT_PERCENT, 1), 0.45)
  const strength = 0.45 + 0.55 * heat
  const mixed = HEAT_NEUTRAL_RGB.map((neutral, i) =>
    Math.round(neutral + (anchor[i] - neutral) * strength),
  )
  return `rgb(${mixed.join(', ')})`
}

/** Square-root-dampened weights with a 32%-of-map cap: proportional market
 * caps let one giant swallow half the card and crush the tail into slivers. */
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

const HeatmapSkeleton = () => {
  const t = useT()
  return (
    <Box
      flex={1}
      gap="spacing-4"
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={t('news.mobile.loadingHeadlines')}
    >
      <Box flexDirection="row" gap="spacing-4">
        <Box flex={2}>
          <PlaceholderBox height={96} />
        </Box>
        <Box flex={1}>
          <PlaceholderBox height={96} />
        </Box>
      </Box>
      <Box flexDirection="row" gap="spacing-4">
        <Box flex={1}>
          <PlaceholderBox height={56} />
        </Box>
        <Box flex={1}>
          <PlaceholderBox height={56} />
        </Box>
        <Box flex={1}>
          <PlaceholderBox height={56} />
        </Box>
      </Box>
    </Box>
  )
}

/** A market heatmap card: the roster source's tiles laid out as a squarified
 * treemap - area by market cap, color by day's move. Mirrors NewsSourceCard's
 * chrome (accent tab, badge header, follow/share) so it sits in the deck as a
 * first-class card; memoized for the same parent-churn reasons. */
export const HeatmapCard = memo(function HeatmapCard({
  source,
  elevated,
}: {
  source: NewsSourceMeta
  elevated?: boolean
}) {
  const { data, isLoading, isError, errorUpdateCount, dataUpdatedAt } =
    useNewsHeatmap(source.id, elevated)
  const isRestoring = useIsRestoring()
  const t = useT()
  const theme = useTheme()

  const locale = useLocale()
  const now = useMinuteNow(Boolean(elevated))
  const [box, setBox] = useState({ width: 0, height: 0 })

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
  // errorUpdateCount/dataUpdatedAt are in the deps for the same reason as
  // NewsSourceCard: once a map has served (or failed), `data`/`isError` keep
  // their identity across polls, so without a per-poll counter the strike
  // effect fires once and sticks at 1, never reaching the drop threshold.
  useEffect(() => {
    if (isError || isEmpty) markFailed(source.id)
    else if (data) markLoaded(source.id)
  }, [isError, isEmpty, data, errorUpdateCount, dataUpdatedAt, source.id])

  const tileLabel = (tile: NewsHeatmapTile, width: number, height: number) => {
    // Every tile that can physically hold type gets its symbol and number -
    // an unlabeled colored square reads as a bug, not a stock. Small tiles
    // step the type down instead of dropping it.
    if (width < 26 || height < 16) return null
    const tiny = width < 48 || height < 34
    // Server labels may carry a note after " · " ("85 pts · 25/26 final") -
    // it renders as its own smaller second row instead of truncating.
    const [labelMain, labelNote] = tile.label
      ? tile.label.split(' · ', 2)
      : [undefined, undefined]
    // Brand mark like the reference heatmaps, on tiles with room for it.
    const showLogo = Boolean(tile.logo) && width >= 56 && height >= 64
    const logoSize = width >= 120 && height >= 120 ? 30 : 20
    // Tiles are solid green/red/slate at every heat, so text is always white.
    return (
      <>
        {showLogo ? (
          <Image
            source={{ uri: tile.logo ?? undefined }}
            style={{
              width: logoSize,
              height: logoSize,
              marginBottom: LOGO_GAP,
            }}
            contentFit="contain"
          />
        ) : null}
        <Text
          variant="caption"
          numberOfLines={1}
          style={[
            KICKER_STYLE,
            { color: HEAT_TEXT },
            tiny ? TINY_KICKER_STYLE : null,
          ]}
        >
          {tile.symbol}
        </Text>
        {height >= 34 ? (
          <Text
            variant="caption"
            numberOfLines={1}
            style={[{ color: HEAT_TEXT }, tiny ? TINY_VALUE_STYLE : null]}
          >
            {labelMain ??
              `${tile.changePercent > 0 ? '+' : ''}${tile.changePercent.toFixed(2)}%`}
          </Text>
        ) : null}
        {labelNote && height >= 48 ? (
          <Text
            variant="caption"
            numberOfLines={1}
            style={[NOTE_STYLE, tiny ? TINY_VALUE_STYLE : null]}
          >
            {labelNote}
          </Text>
        ) : null}
      </>
    )
  }

  return (
    <Box
      flex={1}
      gap="spacing-12"
      padding="spacing-16"
      borderRadius="border-radius-16"
      backgroundColor={elevated ? 'card' : 'cardUnder'}
      borderWidth={1}
      borderColor="border"
      style={
        elevated
          ? {
              shadowOffset: {
                width: 0,
                height: theme.dimension['dimension-12'],
              },
              shadowOpacity: 0.18,
              shadowRadius: theme.dimension['dimension-24'],
              elevation: 8,
            }
          : { elevation: 1 }
      }
    >
      <SourceAccentTab color={source.color} />
      <Box
        flexDirection="row"
        alignItems="center"
        justifyContent="space-between"
        gap="spacing-8"
      >
        <Box
          flexDirection="row"
          alignItems="center"
          gap="spacing-8"
          flexShrink={1}
        >
          <Touchable onPress={() => openExternalUrl(source.home ?? undefined)}>
            <SourceBadge
              id={source.id}
              name={source.name}
              logo={source.logo}
              size={32}
            />
          </Touchable>
          <Box gap="spacing-2" flexShrink={1}>
            <Box flexDirection="row" alignItems="center" gap="spacing-8">
              <Box
                width={8}
                height={8}
                borderRadius="border-radius-999"
                flexShrink={0}
                style={{ backgroundColor: source.color }}
              />
              <Text
                variant="bodySerif"
                numberOfLines={1}
                style={{ flexShrink: 1 }}
              >
                {source.name.endsWith(' Table')
                  ? source.name.slice(0, -6)
                  : source.name}
              </Text>
            </Box>
            <Text variant="caption" color="subtext" style={KICKER_STYLE}>
              {data?.updatedTime
                ? `${t('news.card.updated')} ${timeAgo(data.updatedTime, now, locale)}`
                : isError
                  ? t('news.card.failed')
                  : t('news.card.loading')}
            </Text>
          </Box>
        </Box>
        <Box flexDirection="row" alignItems="center" gap="spacing-8">
          <ShareButton source={source} />
          <FollowButton sourceId={source.id} />
        </Box>
      </Box>

      <Box
        flex={1}
        borderRadius="border-radius-12"
        style={{ position: 'relative', overflow: 'hidden' }}
        onLayout={(e) => {
          const { width, height } = e.nativeEvent.layout
          setBox((prev) =>
            prev.width === width && prev.height === height
              ? prev
              : { width, height },
          )
        }}
      >
        {isLoading || (isRestoring && !data) ? (
          <HeatmapSkeleton />
        ) : tiles.length === 0 ? (
          <Text variant="caption" color="subtext">
            {t('news.card.failed')}
          </Text>
        ) : box.width > 0 && box.height > 0 ? (
          tiles.map((tile, i) => {
            const rect = rects[i]
            // `!(> 1)` (not `<= 1`) so a NaN width/height - which every
            // comparison returns false for - fails closed instead of reaching
            // an absolute view and red-screening RN's layout.
            if (!rect || !(rect.width > 1) || !(rect.height > 1)) return null
            return (
              <Touchable
                key={`${tile.symbol}-${i}`}
                onPress={() =>
                  // Labelled tiles (sports grids) have no meaningful quote
                  // page - without a server URL the tap is a no-op.
                  openExternalUrl(
                    tile.url ??
                      (tile.label
                        ? undefined
                        : quoteUrl(source.id, tile.symbol)),
                  )
                }
                accessibilityLabel={`${tile.name} ${tile.changePercent}%`}
                style={{
                  position: 'absolute',
                  left: rect.x,
                  top: rect.y,
                  width: rect.width,
                  height: rect.height,
                }}
              >
                <Box
                  flex={1}
                  alignItems="center"
                  justifyContent="center"
                  borderWidth={1}
                  borderColor={elevated ? 'card' : 'cardUnder'}
                  style={{
                    backgroundColor: heatBackground(tile.changePercent),
                  }}
                >
                  {tileLabel(tile, rect.width, rect.height)}
                </Box>
              </Touchable>
            )
          })
        ) : null}
      </Box>
    </Box>
  )
})
