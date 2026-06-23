import { Box } from '@/components/Shared/Box'
import { Input } from '@/components/Shared/Input'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useNewsSources } from '@/hooks/polar/news'
import { useSession } from '@/providers/SessionProvider'
import { useMemo, useState } from 'react'
import { ActivityIndicator, ScrollView } from 'react-native'
import { FollowingFeed } from './FollowingFeed'
import { NewsSearchResults } from './NewsSearchResults'
import { NewsSourceCard } from './NewsSourceCard'

const MAX_CARDS = 12

/** The public news feed: pick a topic, see its sources' headlines, with paid
 * promotions woven in per topic. */
export const NewsFeed = () => {
  const theme = useTheme()
  const { data: sources, isLoading } = useNewsSources()
  const { session } = useSession()
  const [column, setColumn] = useState<string | null>(null)
  const [following, setFollowing] = useState(false)
  const [query, setQuery] = useState('')
  const searching = query.trim().length >= 2

  const columns = useMemo(() => {
    const set = new Set<string>()
    for (const s of sources ?? []) {
      if (s.column) set.add(s.column)
    }
    return Array.from(set).sort()
  }, [sources])

  const visible = useMemo(() => {
    const list = (sources ?? []).filter((s) => !s.redirect)
    const filtered = column ? list.filter((s) => s.column === column) : list
    return filtered.slice(0, MAX_CARDS)
  }, [sources, column])

  return (
    <Box flex={1} gap="spacing-16">
      <Box paddingHorizontal="spacing-16" paddingTop="spacing-8">
        <Input
          value={query}
          onChangeText={setQuery}
          placeholder="Search headlines and sources…"
          autoCapitalize="none"
          autoCorrect={false}
        />
      </Box>

      {searching ? (
        <NewsSearchResults query={query} />
      ) : (
        <>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{
              gap: theme.spacing['spacing-8'],
              paddingHorizontal: theme.spacing['spacing-16'],
            }}
          >
            <TopicChip
              label="All"
              active={!following && column === null}
              onPress={() => {
                setFollowing(false)
                setColumn(null)
              }}
            />
            {session ? (
              <TopicChip
                label="★ Following"
                active={following}
                onPress={() => {
                  setFollowing(true)
                  setColumn(null)
                }}
              />
            ) : null}
            {columns.map((c) => (
              <TopicChip
                key={c}
                label={c}
                active={!following && column === c}
                onPress={() => {
                  setFollowing(false)
                  setColumn(c)
                }}
              />
            ))}
          </ScrollView>

          {following ? (
            <FollowingFeed />
          ) : isLoading ? (
            <Box flex={1} justifyContent="center" alignItems="center">
              <ActivityIndicator />
            </Box>
          ) : (
            <ScrollView
              contentContainerStyle={{
                gap: theme.spacing['spacing-16'],
                padding: theme.spacing['spacing-16'],
              }}
            >
              {visible.map((source) => (
                <NewsSourceCard key={source.id} source={source} />
              ))}
            </ScrollView>
          )}
        </>
      )}
    </Box>
  )
}

const TopicChip = ({
  label,
  active,
  onPress,
}: {
  label: string
  active: boolean
  onPress: () => void
}) => (
  <Touchable onPress={onPress}>
    <Box
      paddingVertical="spacing-6"
      paddingHorizontal="spacing-16"
      borderRadius="border-radius-999"
      backgroundColor={active ? 'primary' : 'card'}
    >
      <Text variant="caption" color={active ? 'monochromeInverted' : 'subtext'}>
        {label}
      </Text>
    </Box>
  </Touchable>
)
