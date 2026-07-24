'use client'

import { useWeather } from '@/hooks/queries/weather'
import { useLocale, useT } from '@/providers/locale'
import type { NewsSourceMeta } from '@/utils/news'
import {
  formatTemp,
  weatherGlyph,
  weatherLabelKey,
  type WeatherData,
} from '@/utils/weather'
import type { TranslationKey } from '@outception-com/i18n'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { FollowButton } from './FollowButton'

// The translator only accepts literal key paths, so map the WMO label group to
// a concrete key rather than building it from a template string.
const CONDITION_KEY = {
  clear: 'news.weather.codes.clear',
  mainlyClear: 'news.weather.codes.mainlyClear',
  partlyCloudy: 'news.weather.codes.partlyCloudy',
  overcast: 'news.weather.codes.overcast',
  fog: 'news.weather.codes.fog',
  drizzle: 'news.weather.codes.drizzle',
  rain: 'news.weather.codes.rain',
  showers: 'news.weather.codes.showers',
  snow: 'news.weather.codes.snow',
  thunderstorm: 'news.weather.codes.thunderstorm',
  unknown: 'news.weather.codes.unknown',
} satisfies Record<string, TranslationKey>

type ConditionKey = (typeof CONDITION_KEY)[keyof typeof CONDITION_KEY]

const conditionKey = (code: number): ConditionKey => {
  const label = weatherLabelKey(code) as keyof typeof CONDITION_KEY
  return CONDITION_KEY[label] ?? CONDITION_KEY.unknown
}

const weekday = (iso: string, locale: string): string => {
  const date = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(locale, { weekday: 'short' })
}

const Metric = ({ label, value }: { label: string; value: string }) => (
  <Box flexDirection="column" rowGap="none" alignItems="end">
    <span className="meta-kicker">{label}</span>
    <Text variant="body" serif>
      {value}
    </Text>
  </Box>
)

const Forecast = ({
  days,
  locale,
  todayLabel,
}: {
  days: WeatherData['daily']
  locale: string
  todayLabel: string
}) => (
  <Box flexDirection="column" rowGap="s">
    {days.map((day, i) => (
      <Box
        key={day.date}
        alignItems="center"
        justifyContent="between"
        columnGap="m"
      >
        <Text variant="body" color="muted" serif>
          {i === 0 ? todayLabel : weekday(day.date, locale)}
        </Text>
        <Box alignItems="center" columnGap="m" flexShrink={0}>
          <span aria-hidden style={{ fontSize: 18, lineHeight: 1 }}>
            {weatherGlyph(day.weatherCode, true)}
          </span>
          <Box columnGap="s" alignItems="baseline">
            <Text variant="body" serif>
              {formatTemp(day.tempMax)}
            </Text>
            <Text variant="caption" color="disabled">
              {formatTemp(day.tempMin)}
            </Text>
          </Box>
        </Box>
      </Box>
    ))}
  </Box>
)

/** The weather panel: current conditions plus a short forecast for the reader's
 * location, resolved via precise geolocation (falling back to their IP
 * country). Renders bare inside the swipe deck's paper sheet, mirroring
 * NewsSourceCard's shell so it swipes and unfollows like any other card. */
export const WeatherCard = ({ source }: { source: NewsSourceMeta }) => {
  const { data, isLoading, isError } = useWeather()
  const locale = useLocale()
  const t = useT()

  return (
    <Box
      flexDirection="column"
      rowGap="m"
      height="100%"
      padding={{ base: 'l', md: 'xl' }}
    >
      <Box alignItems="center" justifyContent="between" columnGap="s">
        <Box flexDirection="column" rowGap="none">
          <Box alignItems="center" columnGap="s">
            <span aria-hidden style={{ fontSize: 16, lineHeight: 1 }}>
              📍
            </span>
            <Text variant="body" as="h3" serif>
              {data?.location ?? t('news.weather.title')}
            </Text>
          </Box>
          <span className="meta-kicker">{t('news.weather.title')}</span>
        </Box>
        <FollowButton sourceId={source.id} />
      </Box>

      <Box
        flex={1}
        minHeight={0}
        flexDirection="column"
        justifyContent="center"
      >
        {isLoading ? (
          <Box flexDirection="column" rowGap="l" paddingTop="s">
            {/* Plain divs: Box forbids className (no-classname-box), and the
                skeleton-bar/animate-pulse classes are custom-CSS escape hatches
                with no Box-prop equivalent. */}
            <div className="skeleton-bar h-12 w-40 animate-pulse" />
            <div className="skeleton-bar h-3.5 w-full animate-pulse" />
            <div className="skeleton-bar h-3.5 w-2/3 animate-pulse" />
          </Box>
        ) : isError || !data ? (
          <Text color="muted" variant="caption">
            {t('news.weather.unavailable')}
          </Text>
        ) : (
          <Box flexDirection="column" rowGap="l">
            <Box alignItems="center" justifyContent="between" columnGap="m">
              <Box alignItems="center" columnGap="m">
                <span aria-hidden style={{ fontSize: 52, lineHeight: 1 }}>
                  {weatherGlyph(data.current.weatherCode, data.current.isDay)}
                </span>
                <Box flexDirection="column" rowGap="none">
                  <Text variant="heading-2xl" as="span">
                    {formatTemp(data.current.temperature)}
                  </Text>
                  <Text variant="caption" color="muted" serif>
                    {t(conditionKey(data.current.weatherCode))}
                  </Text>
                </Box>
              </Box>
              <Box flexDirection="column" rowGap="s">
                <Metric
                  label={t('news.weather.feelsLike')}
                  value={formatTemp(data.current.apparentTemperature)}
                />
                <Metric
                  label={t('news.weather.wind')}
                  value={`${Math.round(data.current.windSpeed)} km/h`}
                />
                <Metric
                  label={t('news.weather.humidity')}
                  value={`${data.current.humidity}%`}
                />
              </Box>
            </Box>

            <div className="rule-top-hairline" />

            <Forecast
              days={data.daily.slice(0, 4)}
              locale={locale}
              todayLabel={t('news.weather.today')}
            />
          </Box>
        )}
      </Box>
    </Box>
  )
}
