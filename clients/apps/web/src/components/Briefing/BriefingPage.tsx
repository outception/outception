'use client'

import { profileName } from '@/components/News/BriefingCard'
import { CoverageLine, ScoreMark } from '@/components/News/BriefingCard'
import {
  getMutedWords,
  getMutedWordsServerSnapshot,
  subscribeMutedWords,
} from '@/components/News/mutedWords'
import { useBriefing, useBriefingProfiles } from '@/hooks/queries/news'
import { useT } from '@/providers/translate'
import {
  briefingPath,
  filterBriefing,
  groupByCategory,
  safeExternalHref,
} from '@outception-com/news-core'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import OutceptionTimeAgo from '@outception-com/ui/components/atoms/OutceptionTimeAgo'
import Link from 'next/link'
import { useMemo, useSyncExternalStore } from 'react'

/** The whole briefing for one profile: every section in full, the why line
 * under each story, and the other profiles to switch to. */
export const BriefingPage = ({ profile }: { profile: string }) => {
  const t = useT()
  const { data, isLoading, isError } = useBriefing(profile)
  const { data: profiles } = useBriefingProfiles()
  const template = profiles?.profiles.find((p) => p.id === profile)?.template
  const mutedWords = useSyncExternalStore(
    subscribeMutedWords,
    getMutedWords,
    getMutedWordsServerSnapshot,
  )
  const groups = useMemo(
    () => (data ? groupByCategory(filterBriefing(data.items, mutedWords)) : []),
    [data, mutedWords],
  )
  return (
    <Box
      as="section"
      flexDirection="column"
      rowGap="xl"
      paddingHorizontal="xl"
      paddingVertical="l"
      width="100%"
      maxWidth={720}
      marginHorizontal="auto"
    >
      <Box flexDirection="column" rowGap="xs">
        <Text variant="heading-s" as="h1" serif>
          {t('news.briefing.profile', { name: profileName(profile, template) })}
        </Text>
        <span className="meta-kicker">
          {data ? (
            <>
              {t('news.briefing.built')}{' '}
              <OutceptionTimeAgo
                date={data.builtAt}
                locale="en"
                minPeriod={60}
              />
            </>
          ) : isError ? (
            t('news.card.failed')
          ) : isLoading ? (
            t('news.card.loading')
          ) : null}
        </span>
      </Box>

      {profiles && profiles.profiles.length > 1 ? (
        <Box
          as="nav"
          flexDirection="row"
          flexWrap="wrap"
          columnGap="s"
          rowGap="s"
          aria-label={t('news.briefing.profiles')}
        >
          {profiles.profiles.map((p) => (
            <Link
              key={p.id}
              href={briefingPath(p.id)}
              className="ghost-pill"
              aria-current={p.id === profile ? 'page' : undefined}
              data-active={p.id === profile}
            >
              {profileName(p.id, p.template)}
            </Link>
          ))}
        </Box>
      ) : null}

      {!isLoading && groups.length === 0 ? (
        <Text color="muted">{t('news.briefing.empty')}</Text>
      ) : null}

      {groups.map((group) => (
        <Box
          as="section"
          key={group.category}
          flexDirection="column"
          rowGap="s"
        >
          <Text variant="heading-xxs" as="h2" serif>
            {group.category}
          </Text>
          <Box as="ol" flexDirection="column" rowGap="m">
            {group.items.map((item) => (
              <Box
                as="li"
                key={item.clusterId}
                flexDirection="column"
                rowGap="xs"
              >
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
                    <Text variant="body" as="span" serif>
                      {item.title}
                    </Text>
                    <CoverageLine item={item} />
                  </Box>
                </a>
                {item.why ? (
                  <Text variant="caption" color="muted" as="p">
                    {item.why}
                  </Text>
                ) : null}
              </Box>
            ))}
          </Box>
        </Box>
      ))}

      <Link href="/" className="headline-link">
        <Text variant="caption" as="span">
          {t('news.briefing.back')}
        </Text>
      </Link>
    </Box>
  )
}
