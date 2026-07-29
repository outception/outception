import { Box } from '@/components/Shared/Box'
import { Input } from '@/components/Shared/Input'
import { NewsSearchResults } from './NewsSearchResults'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useNewsSources } from '@/hooks/outception/news'
import type { NewsSourceMeta } from '@/hooks/outception/news'
import { useT } from '@/providers/LocaleProvider'
import {
  followAll,
  getFocusedSnapshot,
  subscribeFocused,
  unfollowAll,
  setActiveTemplates,
} from '@/utils/focusedSources'
import { KICKER_STYLE } from './newsStyles'
import { RosterRow } from './RosterRow'
import { TemplateGallery } from './TemplateGallery'
import { TopicChips } from './TopicChips'
import MaterialIcons from '@expo/vector-icons/MaterialIcons'
import { NEWS_TOPIC_GROUPS } from '@outception-com/i18n'
import { FlashList } from '@shopify/flash-list'
import * as Haptics from 'expo-haptics'
import {
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react'
import { StyleSheet } from 'react-native'

type SourceEntry = { source: NewsSourceMeta; haystack: string }

/** The full source roster: search the whole catalogue (~250 sources), narrow by
 * topic, and star sources into your deck without needing to type. Rendered
 * inside a GlassDialog card, mirroring the web "Sources" palette dialog;
 * following is device-local (no login). The source list is virtualized
 * (FlashList) so opening the roster only mounts on-screen rows; a query that
 * matches no source name falls through to a headline search. */
export const SourceRoster = ({
  onClose,
  autoFocusSearch,
}: {
  onClose?: () => void
  autoFocusSearch?: boolean
}) => {
  const theme = useTheme()
  const t = useT()
  const { data: sources } = useNewsSources()
  const [query, setQuery] = useState('')
  const [topics, setTopics] = useState<string[]>([])
  // Starter decks are the default view, matching the web dialog — except when
  // the sheet was opened straight into search (quick action), where the reader
  // came to type.
  const [templatesOpen, setTemplatesOpen] = useState(!autoFocusSearch)
  // Select/deselect-all are ACTIONS, not toggles like the chips — without a
  // moment of button feedback the only reaction is stars flipping in the list,
  // which is easy to miss. Flash the pressed button in the accent for a beat.
  const [flash, setFlash] = useState<'select' | 'deselect' | null>(null)
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(
    () => () => {
      if (flashTimer.current) clearTimeout(flashTimer.current)
    },
    [],
  )
  const flashAction = (which: 'select' | 'deselect') => {
    void Haptics.selectionAsync()
    setFlash(which)
    if (flashTimer.current) clearTimeout(flashTimer.current)
    flashTimer.current = setTimeout(() => setFlash(null), 400)
  }
  const focused = useSyncExternalStore(
    subscribeFocused,
    getFocusedSnapshot,
    getFocusedSnapshot,
  )
  const followedSet = useMemo(() => new Set(focused), [focused])

  const presentColumns = useMemo(() => {
    const present = new Set<string>()
    for (const s of sources ?? []) if (s.column) present.add(s.column)
    return present
  }, [sources])

  // A selected chip means its whole group of columns; sub-topic chips
  // contribute single columns (see TopicChips).
  const selectedColumns = useMemo(() => {
    const set = new Set<string>()
    for (const id of topics) {
      const group = NEWS_TOPIC_GROUPS.find((g) => g.id === id)
      if (group) for (const c of group.columns) set.add(c)
      else set.add(id)
    }
    return set
  }, [topics])

  // Precompute each source's lowercased search text once (the catalogue holds
  // thousands of sources); rebuilding it per keystroke is what froze the input.
  const index = useMemo<SourceEntry[]>(
    () =>
      (sources ?? [])
        .filter((s) => !s.redirect)
        .map((s) => {
          const base = `${s.name} ${s.title ?? ''} ${s.id}`.toLowerCase()
          // Collapsed variant so one-word queries match spaced/punctuated
          // names: "laliga" → "La Liga", "seriea" → "Serie A".
          return {
            source: s,
            haystack: `${base} ${base.replace(/[^a-z0-9]/g, '')}`,
          }
        }),
    [sources],
  )

  // Defer the query that drives filtering so typing stays responsive: the heavy
  // filter runs at a lower priority and the keystroke repaints the input first.
  const deferredQuery = useDeferredValue(query)
  const results = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase()
    const out: NewsSourceMeta[] = []
    for (const { source, haystack } of index) {
      if (
        topics.length &&
        (!source.column || !selectedColumns.has(source.column))
      )
        continue
      if (q && !haystack.includes(q)) continue
      out.push(source)
    }
    return out
  }, [index, deferredQuery, topics, selectedColumns])

  const ids = useMemo(() => results.map((s) => s.id), [results])
  // Fall through to the server-side headline search only when no topic chip is
  // active: that search is catalogue-wide, so honouring it under an active
  // filter would show results the chip says are excluded.
  const showHeadlineSearch =
    results.length === 0 &&
    topics.length === 0 &&
    deferredQuery.trim().length >= 2

  // The web's `rule-hairline`: sections of the palette separated by thin ink
  // rules rather than free-floating gaps.
  const hairline = {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: theme.colors.border,
  }

  return (
    <Box flex={1}>
      {/* Borderless command-palette input (web: CommandInput inside the sticky
          paper-search-header), not a boxed form field. */}
      <Box
        flexDirection="row"
        alignItems="center"
        gap="spacing-8"
        paddingHorizontal="spacing-16"
        paddingVertical="spacing-4"
        style={hairline}
      >
        <MaterialIcons name="search" size={18} color={theme.colors.subtext} />
        <Input
          value={query}
          // Typing means the reader wants the list, not the gallery — leave
          // the Starters view so results are visible immediately.
          onChangeText={(text) => {
            setQuery(text)
            if (text) setTemplatesOpen(false)
          }}
          placeholder={t('news.search.placeholder')}
          autoFocus={autoFocusSearch}
          autoCapitalize="none"
          autoCorrect={false}
          style={{
            flex: 1,
            borderWidth: 0,
            backgroundColor: 'transparent',
            paddingHorizontal: 0,
          }}
        />
        {onClose ? (
          <Touchable onPress={onClose} accessibilityLabel={t('errors.close')}>
            <MaterialIcons name="close" size={22} color={theme.colors.text} />
          </Touchable>
        ) : null}
      </Box>

      {/* Group chips with auto-expanding sub-topics (web: flex-wrap grid). */}
      <TopicChips
        present={presentColumns}
        topics={topics}
        // Templates and topic filters are exclusive modes: picking a topic
        // leaves the gallery, opening the gallery clears the filter.
        onChange={(next) => {
          setTemplatesOpen(false)
          setTopics(next)
        }}
        rowStyle={hairline}
        templatesActive={templatesOpen}
        onToggleTemplates={() => {
          setTemplatesOpen((v) => !v)
          setTopics([])
        }}
      />

      {/* Hidden during the headline fallthrough: `results` is empty there, so
          these would be no-ops sitting above the search's own identical pair. */}
      {templatesOpen || showHeadlineSearch ? null : (
        <Box
          flexDirection="row"
          alignItems="center"
          gap="spacing-16"
          paddingHorizontal="spacing-16"
          paddingVertical="spacing-6"
          style={hairline}
        >
          <Touchable
            onPress={() => {
              flashAction('select')
              followAll(ids)
            }}
            disabled={ids.length === 0}
          >
            <Box
              paddingVertical="spacing-4"
              paddingHorizontal="spacing-10"
              borderRadius="border-radius-999"
              backgroundColor={flash === 'select' ? 'primary' : undefined}
            >
              <Text
                variant="caption"
                color={flash === 'select' ? 'monochromeInverted' : 'subtext'}
                style={{ opacity: ids.length === 0 ? 0.4 : 1 }}
              >
                {t('news.search.selectAll')}
              </Text>
            </Box>
          </Touchable>
          <Touchable
            onPress={() => {
              flashAction('deselect')
              unfollowAll(ids)
              // On the unfiltered view this empties the whole deck, so the
              // template toggles must reset with it.
              if (topics.length === 0) setActiveTemplates([])
            }}
            disabled={ids.length === 0}
          >
            <Box
              paddingVertical="spacing-4"
              paddingHorizontal="spacing-10"
              borderRadius="border-radius-999"
              backgroundColor={flash === 'deselect' ? 'primary' : undefined}
            >
              <Text
                variant="caption"
                color={flash === 'deselect' ? 'monochromeInverted' : 'subtext'}
                style={{ opacity: ids.length === 0 ? 0.4 : 1 }}
              >
                {t('news.search.deselectAll')}
              </Text>
            </Box>
          </Touchable>
          <Box flex={1} alignItems="flex-end">
            <Text color="subtext" style={KICKER_STYLE}>
              {ids.length}
            </Text>
          </Box>
        </Box>
      )}

      {showHeadlineSearch ? (
        // No source matched the name, so fall through to the server-side
        // headline search — the reader is probably looking for a story, not a
        // publication. (Web's dialog only matches source names; this is the one
        // place mobile is deliberately ahead.)
        <NewsSearchResults query={deferredQuery} />
      ) : templatesOpen ? (
        <TemplateGallery sources={sources ?? []} open={templatesOpen} />
      ) : results.length === 0 ? (
        <Box padding="spacing-16">
          <Text variant="caption" color="subtext">
            {t('news.search.empty')}
          </Text>
        </Box>
      ) : (
        <FlashList
          data={results}
          extraData={followedSet}
          keyExtractor={(s) => s.id}
          // FlashList v2 anchors the scroll position by default
          // (maintainVisibleContentPosition), which leaves a blank strip at
          // the top of the viewport after fast scrolls in this fixed-height
          // card. The roster list never prepends rows, so anchoring buys
          // nothing — disable it.
          maintainVisibleContentPosition={{ disabled: true }}
          renderItem={({ item }) => (
            <RosterRow source={item} followed={followedSet.has(item.id)} />
          )}
          contentContainerStyle={{
            paddingHorizontal: theme.spacing['spacing-8'],
            paddingTop: theme.spacing['spacing-4'],
            paddingBottom: theme.spacing['spacing-16'],
          }}
          keyboardShouldPersistTaps="handled"
        />
      )}
    </Box>
  )
}
