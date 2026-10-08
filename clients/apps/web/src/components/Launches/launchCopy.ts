import type { TranslateFn } from '@outception-com/i18n'

export type LaunchState =
  | 'submitted'
  | 'approved'
  | 'live'
  | 'ended'
  | 'rejected'
  | 'withdrawn'

/** A day as readers see it: weekday and date, no time. */
export const formatDay = (day: string | null | undefined): string => {
  if (!day) return ''
  const parsed = new Date(`${day}T12:00:00Z`)
  if (Number.isNaN(parsed.getTime())) return day
  try {
    return parsed.toLocaleDateString('en', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      timeZone: 'UTC',
    })
  } catch {
    return day
  }
}

/** The state line on the reader's own list. */
export const launchStateLabel = (
  t: TranslateFn,
  launch: { state: string; day?: string | null },
): string => {
  const day = formatDay(launch.day)
  switch (launch.state as LaunchState) {
    case 'submitted':
      return t('launches.mine.state.submitted')
    case 'approved':
      return t('launches.mine.state.approved', { day })
    case 'live':
      return t('launches.mine.state.live')
    case 'ended':
      return t('launches.mine.state.ended', { day })
    case 'rejected':
      return t('launches.mine.state.rejected')
    case 'withdrawn':
      return t('launches.mine.state.withdrawn')
    default:
      return launch.state
  }
}

export const kickerLabel = (t: TranslateFn, kicker: string): string => {
  switch (kicker) {
    case 'new':
      return t('launches.kinds.new')
    case 'update':
      return t('launches.kinds.update')
    case 'open source':
      return t('launches.kinds.openSource')
    case 'house':
      return t('launches.kinds.house')
    default:
      return kicker
  }
}

/** A product logo: the server's own media path, or a safe external link. */
export const logoSrc = (
  logo: string | null | undefined,
): string | undefined => {
  if (!logo) return undefined
  if (logo.startsWith('/')) return `${process.env.NEXT_PUBLIC_API_URL}${logo}`
  return /^https:\/\/\S+$/i.test(logo) ? logo : undefined
}

/** Today's date as the archive keys it, in UTC. */
export const todayKey = (now: number = Date.now()): string =>
  new Date(now).toISOString().slice(0, 10)
