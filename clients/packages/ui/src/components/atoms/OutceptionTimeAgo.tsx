import TimeAgo from 'react-timeago'

const RELATIVE_UNITS = new Set([
  'second',
  'minute',
  'hour',
  'day',
  'week',
  'month',
  'quarter',
  'year',
])

// The formatter runs once per rendered row, and constructing an
// Intl.RelativeTimeFormat is expensive - one instance per locale is enough.
const relativeFormatters = new Map<string, Intl.RelativeTimeFormat>()

const relativeFormatter = (locale: string): Intl.RelativeTimeFormat => {
  const cached = relativeFormatters.get(locale)
  if (cached) return cached
  const created = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
  relativeFormatters.set(locale, created)
  return created
}

/** A localized relative timestamp ("34 minutes ago", "vor 34 Minuten",
 * "34分前"). Pass the reader's `locale`; formatting, pluralization and the
 * "ago"/"in" wording come from `Intl.RelativeTimeFormat`.
 *
 * Prefer passing `date` as epoch milliseconds: a fresh `Date` object on every
 * parent render re-fires react-timeago's effect and re-arms its timer. */
const OutceptionTimeAgo = (props: {
  date: Date | number | string
  locale?: string
  suffix?: string
  minPeriod?: number
}) => {
  return (
    <TimeAgo
      date={props.date}
      minPeriod={props.minPeriod}
      formatter={(value: number, unit: string, suffix: string) => {
        if (!RELATIVE_UNITS.has(unit)) {
          return `${value} ${unit} ${props.suffix ?? suffix}`
        }
        const rtf = relativeFormatter(props.locale || 'en')
        const signed = (suffix === 'ago' ? -1 : 1) * value
        return rtf.format(signed, unit as Intl.RelativeTimeFormatUnit)
      }}
    />
  )
}

export default OutceptionTimeAgo
