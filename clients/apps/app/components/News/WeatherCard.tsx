import { Box } from '@/components/Shared/Box'
import { PlaceholderBox } from '@/components/Shared/PlaceholderBox'
import { Text } from '@/components/Shared/Text'
import { useWeather } from '@/hooks/outception/news'
import type { NewsSourceMeta } from '@/hooks/outception/news'
import { useLocale, useT } from '@/providers/LocaleProvider'
import {
  formatTemp,
  weatherGlyph,
  weatherLabelKey,
  type WeatherData,
} from '@/utils/weather'
import type { TranslationKey } from '@outception-com/i18n'
import { FollowButton } from './FollowButton'
import { KICKER_STYLE } from './newsStyles'
import { SourceAccentTab } from './SourceAccentTab'

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
  try {
    return date.toLocaleDateString(locale, { weekday: 'short' })
  } catch {
    return date.toLocaleDateString(undefined, { weekday: 'short' })
  }
}

const Metric = ({ label, value }: { label: string; value: string }) => (
  <Box alignItems="flex-end" gap="spacing-2">
    <Text variant="caption" color="subtext" style={KICKER_STYLE}>
      {label}
    </Text>
    <Text variant="body">{value}</Text>
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
  <Box gap="spacing-8">
    {days.map((day, i) => (
      <Box
        key={day.date}
        flexDirection="row"
        alignItems="center"
        justifyContent="space-between"
        gap="spacing-12"
      >
        <Text variant="body" color="subtext">
          {i === 0 ? todayLabel : weekday(day.date, locale)}
        </Text>
        <Box flexDirection="row" alignItems="center" gap="spacing-12">
          <Text variant="body">{weatherGlyph(day.weatherCode, true)}</Text>
          <Box flexDirection="row" alignItems="baseline" gap="spacing-8">
            <Text variant="body">{formatTemp(day.tempMax)}</Text>
            <Text variant="caption" color="subtext">
              {formatTemp(day.tempMin)}
            </Text>
          </Box>
        </Box>
      </Box>
    ))}
  </Box>
)

/** The weather panel: current conditions plus a short forecast for the reader's
 * device region. Shares NewsSourceCard's shell so it sits in the deck like any
 * other card. Mirrors the web WeatherCard. */
export const WeatherCard = ({ source }: { source: NewsSourceMeta }) => {
  const { data, isLoading, isError } = useWeather()
  const locale = useLocale()
  const t = useT()

  return (
    <Box
      flex={1}
      gap="spacing-12"
      padding="spacing-16"
      borderRadius="border-radius-16"
      backgroundColor="card"
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
          <Text variant="body">📍</Text>
          <Text variant="title">
            {data?.location ?? t('news.weather.title')}
          </Text>
        </Box>
        <FollowButton sourceId={source.id} />
      </Box>

      <Box flex={1} justifyContent="center">
        {isLoading ? (
          <Box gap="spacing-12">
            <PlaceholderBox width={120} height={40} />
            <PlaceholderBox height={13} />
            <PlaceholderBox width="66%" height={13} />
          </Box>
        ) : isError || !data ? (
          <Text variant="caption" color="subtext">
            {t('news.weather.unavailable')}
          </Text>
        ) : (
          <Box gap="spacing-16">
            <Box
              flexDirection="row"
              alignItems="center"
              justifyContent="space-between"
              gap="spacing-12"
            >
              <Box flexDirection="row" alignItems="center" gap="spacing-12">
                <Text variant="titleLarge">
                  {weatherGlyph(data.current.weatherCode, data.current.isDay)}
                </Text>
                <Box gap="spacing-2">
                  <Text variant="titleLarge">
                    {formatTemp(data.current.temperature)}
                  </Text>
                  <Text variant="caption" color="subtext">
                    {t(conditionKey(data.current.weatherCode))}
                  </Text>
                </Box>
              </Box>
              <Box gap="spacing-8">
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

            <Box height={1} backgroundColor="border" />

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
