'use client'

import { SourceBadge } from '@/components/News/SourceBadge'
import { useStory } from '@/hooks/queries/news'
import { useT } from '@/providers/translate'
import { safeExternalHref } from '@outception-com/news-core'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import OutceptionTimeAgo from '@outception-com/ui/components/atoms/OutceptionTimeAgo'
import Link from 'next/link'

/** One story across outlets: the lead headline, how many carry it, and every
 * outlet's own headline with a link out. */
export const StoryPage = ({ id }: { id: string }) => {
  const t = useT()
  const { data, isLoading, isError } = useStory(id)
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
      {data ? (
        <>
          <Box flexDirection="column" rowGap="xs">
            <span className="meta-kicker">{t('news.story.title')}</span>
            <Text variant="heading-s" as="h1" serif>
              {data.title}
            </Text>
            <Text variant="caption" color="muted" as="p">
              {data.publisherCount > 1
                ? t('news.story.outlets', { count: data.publisherCount })
                : t('news.story.outlet')}
              {' · '}
              {t('news.card.firstBy', { source: data.leadSourceName })}
              {' · '}
              {t('news.story.firstSeen')}{' '}
              <OutceptionTimeAgo
                date={data.firstSeenAt}
                locale="en"
                minPeriod={60}
              />
            </Text>
          </Box>
          <Box as="ol" flexDirection="column" rowGap="m">
            {data.items.map((member) => (
              <Box as="li" key={`${member.sourceId}-${member.url}`}>
                <a
                  href={safeExternalHref(member.url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="headline-link rule-row flex min-w-0 items-center gap-3 rounded-md pr-1"
                >
                  <SourceBadge
                    id={member.sourceId}
                    logo={member.logo}
                    size={24}
                  />
                  <Box
                    as="span"
                    display="flex"
                    flexDirection="column"
                    minWidth={0}
                    flexGrow={1}
                    flexBasis={0}
                  >
                    <Text variant="body" as="span" serif>
                      {member.title}
                    </Text>
                    <span className="meta-kicker">
                      {member.sourceName}
                      {typeof member.pubDate === 'number' ? (
                        <>
                          {' · '}
                          <OutceptionTimeAgo
                            date={member.pubDate}
                            locale="en"
                            minPeriod={60}
                          />
                        </>
                      ) : null}
                    </span>
                  </Box>
                </a>
              </Box>
            ))}
          </Box>
        </>
      ) : isError ? (
        <Text color="muted">{t('news.story.missing')}</Text>
      ) : isLoading ? (
        <Text color="muted" variant="caption">
          {t('news.card.loading')}
        </Text>
      ) : null}
      <Link href="/" className="headline-link">
        <Text variant="caption" as="span">
          {t('news.story.back')}
        </Text>
      </Link>
    </Box>
  )
}
