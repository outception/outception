import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import {
  useBriefing,
  useBriefingHistory,
  useBriefingProfiles,
} from '@/hooks/outception/news'
import { usePushSubscription } from '@/hooks/usePushSubscription'
import {
  getSpeakingSnapshot,
  speakHeadlines,
  stopSpeaking,
} from '@/utils/listen'
import { useT } from '@/providers/translate'
import { openExternalUrl } from '@/utils/news'
import { getMutedWords, subscribeMutedWords } from '@/utils/prefs'
import { getTranslations } from '@outception-com/i18n'
import {
  briefingDayOf,
  coverage,
  dayBefore,
  diffBriefings,
  filterBriefing,
  groupByCategory,
  scoreTier,
  timeAgo,
} from '@outception-com/news-core'
import { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { ActivityIndicator, ScrollView } from 'react-native'

const DEFAULT_PROFILE = 'news-junkie'

/** The profile's display name: the Starter it was built from. */
const profileName = (profile: string, template?: string): string => {
  const names = getTranslations().news.templates.names as Record<string, string>
  return names[template ?? profile] ?? names[profile] ?? profile
}

/** One switch in the tools row above the briefing. */
const Pill = ({
  active,
  disabled,
  label,
  onPress,
}: {
  active: boolean
  disabled?: boolean
  label: string
  onPress: () => void
}) => (
  <Touchable onPress={onPress} disabled={disabled}>
    <Box
      paddingVertical="spacing-4"
      paddingHorizontal="spacing-12"
      borderRadius="border-radius-8"
      backgroundColor={active ? 'card' : undefined}
      borderWidth={1}
      borderColor="border"
      opacity={disabled ? 0.5 : 1}
    >
      <Text variant="caption" color={active ? 'text' : 'subtext'}>
        {label}
      </Text>
    </Box>
  </Touchable>
)

/** The whole briefing for one profile: every section in full, the coverage
 * line and the why line under each story, and the other profiles to switch
 * to. The same model the web page renders, through news-core. */
export const BriefingScreen = ({
  profile,
  onProfile,
}: {
  profile?: string
  onProfile: (profile: string) => void
}) => {
  const t = useT()
  const theme = useTheme()
  const active = profile ?? DEFAULT_PROFILE
  const { data, isLoading, isError } = useBriefing(active)
  const { data: profiles } = useBriefingProfiles()
  const template = profiles?.profiles.find((p) => p.id === active)?.template
  const mutedWords = useSyncExternalStore(
    subscribeMutedWords,
    getMutedWords,
    getMutedWords,
  )
  // "Since yesterday": today's stories against the previous day's build,
  // fetched only when the reader asks.
  const [sinceYesterday, setSinceYesterday] = useState(false)
  const { data: history } = useBriefingHistory(active, sinceYesterday)
  const diff = useMemo(() => {
    if (!data || !history) return null
    const yesterday = dayBefore(history.days, briefingDayOf(data.builtAt))
    return { yesterday, ...diffBriefings(data.items, yesterday?.items ?? null) }
  }, [data, history])
  const groups = useMemo(() => {
    if (!data) return []
    const items = sinceYesterday && diff ? diff.fresh : data.items
    return groupByCategory(filterBriefing(items, mutedWords))
  }, [data, diff, mutedWords, sinceYesterday])
  const lines = useMemo(
    () =>
      groups.flatMap((group) => [
        group.category,
        ...group.items.map((item) => item.title),
      ]),
    [groups],
  )
  const [speaking, setSpeaking] = useState(false)
  useEffect(() => () => stopSpeaking(), [])
  const push = usePushSubscription(active)
  return (
    <ScrollView
      contentContainerStyle={{ paddingBottom: theme.spacing['spacing-48'] }}
    >
      <Box padding="spacing-16" gap="spacing-24">
        <Box gap="spacing-4">
          <Text variant="title">
            {t('news.briefing.profile', {
              name: profileName(active, template),
            })}
          </Text>
          {data ? (
            <Text variant="caption" color="subtext">
              {t('news.briefing.built')}{' '}
              {timeAgo(data.builtAt, undefined, 'en')}
            </Text>
          ) : null}
        </Box>

        {profiles && profiles.profiles.length > 1 ? (
          <Box flexDirection="row" flexWrap="wrap" gap="spacing-8">
            {profiles.profiles.map((p) => (
              <Touchable key={p.id} onPress={() => onProfile(p.id)}>
                <Box
                  paddingVertical="spacing-4"
                  paddingHorizontal="spacing-12"
                  borderRadius="border-radius-8"
                  backgroundColor={p.id === active ? 'card' : undefined}
                  borderWidth={1}
                  borderColor="border"
                >
                  <Text
                    variant="caption"
                    color={p.id === active ? 'text' : 'subtext'}
                  >
                    {profileName(p.id, p.template)}
                  </Text>
                </Box>
              </Touchable>
            ))}
          </Box>
        ) : null}

        {data ? (
          <Box flexDirection="row" flexWrap="wrap" gap="spacing-8">
            <Pill
              active={sinceYesterday}
              label={
                sinceYesterday
                  ? t('news.briefing.everything')
                  : t('news.briefing.sinceYesterday')
              }
              onPress={() => setSinceYesterday((was) => !was)}
            />
            {lines.length > 0 ? (
              <Pill
                active={speaking}
                label={
                  speaking
                    ? t('news.briefing.stopListening')
                    : t('news.briefing.listen')
                }
                onPress={() => {
                  if (getSpeakingSnapshot()) {
                    stopSpeaking()
                    setSpeaking(false)
                  } else {
                    speakHeadlines(lines, 'en')
                    setSpeaking(true)
                  }
                }}
              />
            ) : null}
            <Pill
              active={push.chosen}
              disabled={push.busy}
              label={
                push.chosen
                  ? t('news.briefing.notifyOn')
                  : t('news.briefing.notify')
              }
              onPress={() => void push.toggle()}
            />
          </Box>
        ) : null}
        {sinceYesterday && diff ? (
          <Text variant="caption" color="subtext">
            {diff.yesterday === null
              ? t('news.briefing.firstDay')
              : diff.fresh.length === 0
                ? t('news.briefing.nothingNew')
                : t('news.briefing.freshCount', { count: diff.fresh.length })}
          </Text>
        ) : null}

        {isLoading ? (
          <ActivityIndicator size="large" color={theme.colors.subtext} />
        ) : null}
        {isError || (!isLoading && !sinceYesterday && groups.length === 0) ? (
          <Text variant="body" color="subtext">
            {t('news.briefing.empty')}
          </Text>
        ) : null}

        {groups.map((group) => (
          <Box key={group.category} gap="spacing-8">
            <Text variant="caption" color="subtext">
              {group.category.toUpperCase()}
            </Text>
            {group.items.map((item) => {
              const { lead, others } = coverage(item)
              return (
                <Touchable
                  key={item.clusterId}
                  onPress={() => openExternalUrl(item.url)}
                >
                  <Box
                    flexDirection="row"
                    gap="spacing-8"
                    paddingVertical="spacing-4"
                  >
                    <Text
                      variant="caption"
                      color={
                        scoreTier(item.score) === 'top' ? 'text' : 'subtext'
                      }
                    >
                      {typeof item.score === 'number'
                        ? String(item.score)
                        : '·'}
                    </Text>
                    <Box flex={1} gap="spacing-4">
                      <Text variant="body">{item.title}</Text>
                      <Text variant="caption" color="subtext">
                        {others > 0
                          ? `${t('news.card.outlets', { count: others + 1 })} · ${t('news.card.firstBy', { source: lead })}`
                          : lead}
                      </Text>
                      {item.why ? (
                        <Text variant="caption" color="subtext">
                          {item.why}
                        </Text>
                      ) : null}
                    </Box>
                  </Box>
                </Touchable>
              )
            })}
          </Box>
        ))}
      </Box>
    </ScrollView>
  )
}
