import { Box } from '@/components/Shared/Box'
import { Input } from '@/components/Shared/Input'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useDefaultDeck, useNewsSources } from '@/hooks/outception/news'
import type { NewsSourceMeta } from '@/hooks/outception/news'
import { useT } from '@/providers/LocaleProvider'
import {
  getEverFollowedSnapshot,
  getFocusedSnapshot,
  setSeedDeck,
  subscribeFocused,
} from '@/utils/focusedSources'
import { getFailedSnapshot, subscribeFailed } from '@/utils/failedSources'
import { getHiddenSnapshot, subscribeHidden } from '@/utils/hiddenSources'
import { WEATHER_SOURCE_ID, WEATHER_SOURCE_META } from '@/utils/weather'
import { NEWS_COLUMN_KEYS } from '@outception-com/i18n'
import { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { ActivityIndicator, ScrollView } from 'react-native'
import { NewsDeck } from './NewsDeck'
import { NewsSearchResults } from './NewsSearchResults'

/** The public news feed: your device-local deck ("Your deck" — followed or, for
 * a fresh visitor, seeded with the curated default deck), a topic filter to
 * browse a column, and search. Following is anonymous (no login). Mirrors the
 * web wall. */
export const NewsFeed = () => {
  const theme = useTheme()
  const t = useT()
  const { data: sources, isLoading: sourcesLoading } = useNewsSources()
  const [column, setColumn] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const focused = useSyncExternalStore(
    subscribeFocused,
    getFocusedSnapshot,
    getFocusedSnapshot,
  )
  const everFollowed = useSyncExternalStore(
    subscribeFocused,
    getEverFollowedSnapshot,
    getEverFollowedSnapshot,
  )
  const hidden = useSyncExternalStore(
    subscribeHidden,
    getHiddenSnapshot,
    getHiddenSnapshot,
  )
  const failed = useSyncExternalStore(
    subscribeFailed,
    getFailedSnapshot,
    getFailedSnapshot,
  )
  const searching = query.trim().length >= 2

  // Seed the curated default deck only for a fresh visitor (never followed)
  // viewing their whole deck (no column filter).
  const seeding = column === null && focused.length === 0 && !everFollowed
  const { data: defaultDeckIds, isLoading: defaultDeckLoading } =
    useDefaultDeck(seeding)

  // Register the seed so the first follow promotes it into the followed set
  // (see focusedSources.toggleFocus) instead of collapsing the deck to one card.
  useEffect(() => {
    setSeedDeck(defaultDeckIds ?? [])
  }, [defaultDeckIds])

  const columns = useMemo(() => {
    const set = new Set<string>()
    for (const s of sources ?? []) {
      if (s.column) set.add(s.column)
    }
    return Array.from(set).sort()
  }, [sources])

  const visible = useMemo<NewsSourceMeta[]>(() => {
    const hiddenSet = new Set(hidden)
    const failedSet = new Set(failed)
    const list = (sources ?? []).filter(
      (s) => !s.redirect && !hiddenSet.has(s.id) && !failedSet.has(s.id),
    )
    const byId = new Map(list.map((s) => [s.id, s]))
    if (!hiddenSet.has(WEATHER_SOURCE_ID)) {
      byId.set(WEATHER_SOURCE_ID, WEATHER_SOURCE_META)
    }
    let deck: NewsSourceMeta[]
    if (column) {
      deck = list.filter((s) => s.column === column)
    } else {
      // Your deck: the followed set wins; a fresh visitor is seeded; a curator
      // who emptied their deck gets an empty wall.
      let ids: readonly string[]
      if (focused.length > 0) ids = focused
      else if (seeding) ids = defaultDeckIds ?? []
      else ids = []
      deck = ids
        .map((id) => byId.get(id))
        .filter((s): s is NewsSourceMeta => Boolean(s))
    }
    // Weather is a utility card, not news — keep it at the END of the deck.
    const weather = deck.filter((s) => s.id === WEATHER_SOURCE_ID)
    const news = deck.filter((s) => s.id !== WEATHER_SOURCE_ID)
    return [...news, ...weather]
  }, [sources, column, hidden, failed, focused, seeding, defaultDeckIds])

  const isLoading = sourcesLoading || (seeding && defaultDeckLoading)

  return (
    <Box flex={1} gap="spacing-16">
      <Box paddingHorizontal="spacing-16" paddingTop="spacing-8">
        <Input
          value={query}
          onChangeText={setQuery}
          placeholder={t('news.mobile.searchPlaceholder')}
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
              label={t('news.mobile.filterAll')}
              active={column === null}
              onPress={() => setColumn(null)}
            />
            {columns.map((c) => (
              <TopicChip
                key={c}
                label={
                  c in NEWS_COLUMN_KEYS
                    ? t(NEWS_COLUMN_KEYS[c as keyof typeof NEWS_COLUMN_KEYS])
                    : c
                }
                active={column === c}
                onPress={() => setColumn(c)}
              />
            ))}
          </ScrollView>

          {isLoading ? (
            <Box flex={1} justifyContent="center" alignItems="center">
              <ActivityIndicator />
            </Box>
          ) : visible.length === 0 ? (
            <Box
              flex={1}
              justifyContent="center"
              alignItems="center"
              padding="spacing-32"
              gap="spacing-8"
            >
              <Text
                variant="body"
                color="subtext"
                style={{ textAlign: 'center' }}
              >
                {t('news.mobile.deckEmpty')}
              </Text>
            </Box>
          ) : (
            // Key by column so each topic's deck is its own instance: switching
            // chips restores that column's saved position instead of reusing the
            // previous column's card index.
            <NewsDeck
              key={column ?? 'all'}
              sources={visible}
              storageKey={column ?? 'all'}
            />
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
