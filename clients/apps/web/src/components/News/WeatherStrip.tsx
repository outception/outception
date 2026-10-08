'use client'

import { useCard } from '@/hooks/queries/news'
import { useT } from '@/providers/translate'
import { isStripCard, WEATHER_STRIP_ID } from '@outception-com/news-core'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'

/** A WMO weather code's family, for one short word. */
const codeFamily = (
  code: number,
):
  | 'clear'
  | 'cloudy'
  | 'fog'
  | 'drizzle'
  | 'rain'
  | 'snow'
  | 'showers'
  | 'thunder' => {
  if (code === 0) return 'clear'
  if (code <= 3) return 'cloudy'
  if (code <= 48) return 'fog'
  if (code <= 57) return 'drizzle'
  if (code <= 67) return 'rain'
  if (code <= 77) return 'snow'
  if (code <= 82) return 'showers'
  if (code <= 86) return 'snow'
  return 'thunder'
}

/** The one-line weather attachment on the country and city cards: place,
 * temperature, conditions and today's range. Only the top card asks. */
export const WeatherStrip = ({ attachedTo }: { attachedTo: string }) => {
  const t = useT()
  const { data } = useCard(WEATHER_STRIP_ID, 'strip', { attachedTo })
  const weather = data && isStripCard(data) ? data.payload.weather : null
  if (!weather) return null
  const family = codeFamily(weather.current.weatherCode)
  const label = {
    clear: t('news.strip.codes.clear'),
    cloudy: t('news.strip.codes.cloudy'),
    fog: t('news.strip.codes.fog'),
    drizzle: t('news.strip.codes.drizzle'),
    rain: t('news.strip.codes.rain'),
    snow: t('news.strip.codes.snow'),
    showers: t('news.strip.codes.showers'),
    thunder: t('news.strip.codes.thunder'),
  }[family]
  const today = weather.daily[0]
  return (
    <Box
      as="aside"
      flexDirection="row"
      alignItems="center"
      flexWrap="wrap"
      columnGap="s"
      rowGap="none"
      paddingTop="xs"
      aria-label={weather.location}
      data-testid="weather-strip"
    >
      <Text variant="caption" color="muted" as="span" truncate>
        {weather.location} · {Math.round(weather.current.temperature)}° ·{' '}
        {label}
        {today
          ? ` · ${Math.round(today.tempMax)}° / ${Math.round(today.tempMin)}°`
          : ''}
        {' · '}
        {t('news.strip.feelsLike', {
          temp: Math.round(weather.current.apparentTemperature),
        })}
      </Text>
    </Box>
  )
}
