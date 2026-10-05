import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useBriefing, useBriefingProfiles } from '@/hooks/outception/news'
import { useT } from '@/providers/translate'
import { openExternalUrl } from '@/utils/news'
import { getMutedWords, subscribeMutedWords } from '@/utils/prefs'
import { getTranslations } from '@outception-com/i18n'
import {
  coverage,
  filterBriefing,
  groupByCategory,
  scoreTier,
  timeAgo,
} from '@outception-com/news-core'
import { useMemo, useSyncExternalStore } from 'react'
import { ActivityIndicator, ScrollView } from 'react-native'

const DEFAULT_PROFILE = 'news-junkie'

/** The profile's display name: the Starter it was built from. */
const profileName = (profile: string, template?: string): string => {
  const names = getTranslations().news.templates.names as Record<string, string>
  return names[template ?? profile] ?? names[profile] ?? profile
}

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
  const groups = useMemo(
    () => (data ? groupByCategory(filterBriefing(data.items, mutedWords)) : []),
    [data, mutedWords],
  )
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

        {isLoading ? (
          <ActivityIndicator size="large" color={theme.colors.subtext} />
        ) : null}
        {isError || (!isLoading && groups.length === 0) ? (
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
