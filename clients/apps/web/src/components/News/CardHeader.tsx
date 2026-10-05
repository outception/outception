'use client'

import { useT } from '@/providers/translate'
import {
  safeExternalHref,
  stateWord,
  type SignalState,
} from '@outception-com/news-core'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import OutceptionTimeAgo from '@outception-com/ui/components/atoms/OutceptionTimeAgo'
import type { ReactNode } from 'react'
import { SourceBadge } from './SourceBadge'

/**
 * The one header every card kind shares: the badge, the accent dot and the
 * name, the kicker with the update time and the state line, and an optional
 * "why this card" line. The state shows as a tertiary word after the time,
 * never as a banner: a stale card still reads.
 */
export const CardHeader = ({
  id,
  name,
  color,
  logo,
  home,
  updatedAt,
  state,
  loading = false,
  error = false,
  why,
  actions,
  badge = true,
}: {
  id: string
  name: string
  /** The accent; the brand colour when the card has no publisher. */
  color?: string | null
  logo?: string | null
  home?: string | null
  /** Epoch milliseconds of the card's last update. */
  updatedAt?: number | null
  state?: SignalState
  loading?: boolean
  error?: boolean
  why?: string | null
  actions?: ReactNode
  badge?: boolean
}) => {
  const t = useT()
  const word = state ? stateWord(state) : null
  const stateLabel = word
    ? {
        degraded: t('news.state.degraded'),
        stale: t('news.state.stale'),
        fallback: t('news.state.fallback'),
        unavailable: t('news.state.unavailable'),
      }[word]
    : null
  const href = safeExternalHref(home)
  const mark = badge ? (
    <SourceBadge id={id} name={name} logo={logo} size={32} />
  ) : null
  return (
    <Box flexDirection="column" rowGap="xs">
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
          {mark ? (
            href ? (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={name}
                style={{ flexShrink: 0, lineHeight: 0 }}
              >
                {mark}
              </a>
            ) : (
              <span style={{ flexShrink: 0, lineHeight: 0 }}>{mark}</span>
            )
          ) : null}
          <Box flexDirection="column" rowGap="none" minWidth={0}>
            <Box
              flexDirection="row"
              alignItems="center"
              columnGap="s"
              minWidth={0}
            >
              {/* The accent dot is a dynamic per-card colour, which Box's
                  token-only backgroundColor cannot take. */}
              <span
                aria-hidden
                style={{
                  display: 'inline-block',
                  width: 8,
                  height: 8,
                  flexShrink: 0,
                  borderRadius: 9999,
                  backgroundColor: color ?? 'var(--color-brand-500)',
                }}
              />
              <Text variant="body" as="h3" serif truncate>
                {name}
              </Text>
            </Box>
            {/* Uppercase micro-kicker, like the row timestamps. */}
            <span className="meta-kicker" data-testid="card-kicker">
              {updatedAt ? (
                <>
                  {t('news.card.updated')}{' '}
                  <OutceptionTimeAgo
                    date={updatedAt}
                    locale="en"
                    minPeriod={60}
                  />
                </>
              ) : error ? (
                t('news.card.failed')
              ) : loading ? (
                t('news.card.loading')
              ) : null}
              {stateLabel ? (
                <span data-testid="card-state"> · {stateLabel}</span>
              ) : null}
            </span>
          </Box>
        </Box>
        {actions ? (
          <Box
            flexDirection="row"
            alignItems="center"
            columnGap="s"
            flexShrink={0}
          >
            {actions}
          </Box>
        ) : null}
      </Box>
      {why ? (
        <Text variant="caption" color="muted" as="p">
          {why}
        </Text>
      ) : null}
    </Box>
  )
}
