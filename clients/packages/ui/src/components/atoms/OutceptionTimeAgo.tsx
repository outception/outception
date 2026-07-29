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

/** A localized relative timestamp ("34 minutes ago", "vor 34 Minuten",
 * "34分前"). Pass the reader's `locale`; formatting, pluralization and the
 * "ago"/"in" wording come from `Intl.RelativeTimeFormat`. */
const OutceptionTimeAgo = (props: {
  date: Date
  locale?: string
  suffix?: string
}) => {
  return (
    <TimeAgo
      date={props.date}
      formatter={(value: number, unit: string, suffix: string) => {
        if (!RELATIVE_UNITS.has(unit)) {
          return `${value} ${unit} ${props.suffix ?? suffix}`
        }
        const rtf = new Intl.RelativeTimeFormat(props.locale || 'en', {
          numeric: 'auto',
        })
        const signed = (suffix === 'ago' ? -1 : 1) * value
        return rtf.format(signed, unit as Intl.RelativeTimeFormatUnit)
      }}
    />
  )
}

export default OutceptionTimeAgo
