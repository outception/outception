'use client'

import { useBriefingProfiles, useCard } from '@/hooks/queries/news'
import { useT } from '@/providers/translate'
import { getTranslations } from '@outception-com/i18n'
import {
  briefingPath,
  briefingProfile,
  briefingState,
  categoryQuotas,
  coverage,
  filterBriefing,
  groupByCategory,
  isBriefingCard,
  safeExternalHref,
  scoreTier,
  stateFromFetch,
  type BriefingItem,
} from '@outception-com/news-core'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import OutceptionTimeAgo from '@outception-com/ui/components/atoms/OutceptionTimeAgo'
import Link from 'next/link'
import { useMemo, useSyncExternalStore } from 'react'
import { useNow } from '@/hooks/useNow'
import type { CardProps } from './Card'
import { CardHeader } from './CardHeader'
import { ShareButton } from './ShareButton'
import {
  getMutedWords,
  getMutedWordsServerSnapshot,
  subscribeMutedWords,
} from './mutedWords'
import {
  getCollapsedServerSnapshot,
  getCollapsedSnapshot,
  subscribe,
  toggleCollapsed,
} from './newsPrefsStore'

/** Rows the card shows across its sections before the "read the whole
 * briefing" link takes over. */
const CARD_ROWS = 12

/** The profile's display name: the Starter it was built from. */
export const profileName = (profile: string, template?: string): string => {
  const names = getTranslations().news.templates.names as Record<string, string>
  return names[template ?? profile] ?? names[profile] ?? profile
}

export const ScoreMark = ({ score }: { score: number | null | undefined }) => {
  const t = useT()
  const tier = scoreTier(score)
  return (
    <span
      className="rank-numeral"
      data-tier={tier}
      aria-label={
        typeof score === 'number'
          ? t('news.briefing.score', { score })
          : undefined
      }
    >
      {typeof score === 'number' ? score : '·'}
    </span>
  )
}

export const CoverageLine = ({ item }: { item: BriefingItem }) => {
  const t = useT()
  const { lead, others } = coverage(item)
  return (
    <span className="meta-kicker">
      {others > 0
        ? `${t('news.card.outlets', { count: others + 1 })} · ${t('news.card.firstBy', { source: lead })}`
        : lead}
      {typeof item.pubDate === 'number' ? (
        <>
          {' · '}
          <OutceptionTimeAgo date={item.pubDate} locale="en" minPeriod={60} />
        </>
      ) : null}
    </span>
  )
}

/** The briefing card in the deck: the profile's ranked stories grouped by
 * section with a per-section quota, the coverage line under each, and a
 * link to the whole briefing. Collapses to its header on request. */
export const BriefingCard = ({ card, active = true, why }: CardProps) => {
  const t = useT()
  const profile = briefingProfile(card.id) ?? ''
  const { data, isLoading, isError } = useCard(card.id, 'briefing', { active })
  const { data: profiles } = useBriefingProfiles()
  const template = profiles?.profiles.find((p) => p.id === profile)?.template
  const name = t('news.briefing.profile', {
    name: profileName(profile, template),
  })
  const payload = data && isBriefingCard(data) ? data.payload : null
  const mutedWords = useSyncExternalStore(
    subscribeMutedWords,
    getMutedWords,
    getMutedWordsServerSnapshot,
  )
  const collapsed = useSyncExternalStore(
    subscribe,
    getCollapsedSnapshot,
    getCollapsedServerSnapshot,
  ).includes(card.id)
  const groups = useMemo(() => {
    if (!payload) return []
    const kept = filterBriefing(payload.items, mutedWords)
    return categoryQuotas(groupByCategory(kept), CARD_ROWS).filter(
      (g) => g.items.length > 0,
    )
  }, [payload, mutedWords])
  const now = useNow()
  const state = payload
    ? briefingState(payload, data!.state, now)
    : stateFromFetch({ loading: isLoading, error: isError, hasData: !!data })

  return (
    <Box
      flexDirection="column"
      rowGap="m"
      height="100%"
      padding={{ base: 'l', md: 'xl' }}
    >
      <CardHeader
        id={card.id}
        name={name}
        badge={false}
        updatedAt={payload?.builtAt}
        state={state}
        loading={isLoading}
        error={isError}
        why={why}
        actions={
          <>
            <ShareButton cardId={card.id} name={name} />
            <button
              type="button"
              className="ghost-pill"
              onClick={() => toggleCollapsed(card.id)}
              aria-expanded={!collapsed}
            >
              {collapsed
                ? t('news.briefing.expand')
                : t('news.briefing.collapse')}
            </button>
          </>
        }
      />
      {collapsed ? null : (
        <Box flex={1} minHeight={0} overflow="hidden">
          <div className="rule-corner min-w-0 flex-1">
            {isLoading ? (
              <Box
                flexDirection="column"
                rowGap="l"
                width="100%"
                paddingTop="s"
              >
                {[0, 1, 2].map((i) => (
                  <Box key={i} flexDirection="column" rowGap="s" width="100%">
                    <div className="skeleton-bar h-2 w-16 animate-pulse" />
                    <div className="skeleton-bar h-3.5 w-full animate-pulse" />
                  </Box>
                ))}
              </Box>
            ) : groups.length === 0 ? (
              <Text color="muted" variant="caption">
                {t('news.briefing.empty')}
              </Text>
            ) : (
              <Box as="ol" flexDirection="column" rowGap="m">
                {groups.map((group) => (
                  <Box
                    as="li"
                    key={group.category}
                    flexDirection="column"
                    rowGap="xs"
                  >
                    <span className="meta-kicker">{group.category}</span>
                    <Box as="ol" flexDirection="column" rowGap="xs">
                      {group.items.map((item) => (
                        <Box as="li" key={item.clusterId}>
                          <a
                            href={safeExternalHref(item.url)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="headline-link rule-row flex min-w-0 items-stretch gap-2 rounded-md pr-1"
                          >
                            <ScoreMark score={item.score} />
                            <Box
                              as="span"
                              display="flex"
                              flexDirection="column"
                              minWidth={0}
                              flexGrow={1}
                              flexBasis={0}
                            >
                              <Text variant="body" as="span" serif truncate={2}>
                                {item.title}
                              </Text>
                              <CoverageLine item={item} />
                            </Box>
                          </a>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                ))}
              </Box>
            )}
          </div>
        </Box>
      )}
      <Link href={briefingPath(profile)} className="headline-link">
        <Text variant="caption" as="span">
          {t('news.briefing.viewAll')}
        </Text>
      </Link>
    </Box>
  )
}
