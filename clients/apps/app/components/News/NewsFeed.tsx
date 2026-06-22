import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useNewsSources } from '@/hooks/polar/news'
import { useMemo, useState } from 'react'
import { ActivityIndicator, ScrollView } from 'react-native'
import { NewsSourceCard } from './NewsSourceCard'

const MAX_CARDS = 12

/** The public news feed: pick a topic, see its sources' headlines, with paid
 * promotions woven in per topic. */
export const NewsFeed = () => {
  const theme = useTheme()
  const { data: sources, isLoading } = useNewsSources()
  const [column, setColumn] = useState<string | null>(null)

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

  if (isLoading) {
    return (
      <Box flex={1} justifyContent="center" alignItems="center">
        <ActivityIndicator />
      </Box>
    )
  }

  return (
    <Box flex={1} gap="spacing-16">
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
          active={column === null}
          onPress={() => setColumn(null)}
        />
        {columns.map((c) => (
          <TopicChip
            key={c}
            label={c}
            active={column === c}
            onPress={() => setColumn(c)}
          />
        ))}
      </ScrollView>

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
