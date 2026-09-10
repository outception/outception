import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useNewsTemplates } from '@/hooks/outception/news'
import type { NewsSourceMeta, NewsTemplate } from '@/hooks/outception/news'
import { useT } from '@/providers/LocaleProvider'
import {
  followAll,
  getActiveTemplatesSnapshot,
  replaceAll,
  setActiveTemplates,
  subscribeFocused,
  unfollowAll,
} from '@/utils/focusedSources'
import { KICKER_STYLE } from './newsStyles'
import { SourceBadge } from './SourceBadge'
import { TemplateActions } from './TemplateActions'
import MaterialIcons from '@expo/vector-icons/MaterialIcons'
import * as Haptics from 'expo-haptics'
import { useTheme } from '@/design-system/useTheme'
import { useCallback, useMemo, useSyncExternalStore } from 'react'
import type { StyleProp, ViewStyle } from 'react-native'
import { StyleSheet } from 'react-native'
import { FlashList } from '@shopify/flash-list'

const PREVIEW_BADGES = 6

const templateKey = (tpl: NewsTemplate) => tpl.id

// Explicit key maps keep t() fully typed against the locale schema - the API
// only ships template ids.
const NAME_KEYS = {
  developer: 'news.templates.names.developer',
  investor: 'news.templates.names.investor',
  'news-junkie': 'news.templates.names.news-junkie',
  'sports-fan': 'news.templates.names.sports-fan',
  'movie-buff': 'news.templates.names.movie-buff',
  'music-lover': 'news.templates.names.music-lover',
  gamer: 'news.templates.names.gamer',
  'science-nerd': 'news.templates.names.science-nerd',
  'foodie-traveler': 'news.templates.names.foodie-traveler',
  'comedy-fun': 'news.templates.names.comedy-fun',
  'fitness-buff': 'news.templates.names.fitness-buff',
  fashionista: 'news.templates.names.fashionista',
  petrolhead: 'news.templates.names.petrolhead',
  'crypto-trader': 'news.templates.names.crypto-trader',
  'space-explorer': 'news.templates.names.space-explorer',
  'ai-insider': 'news.templates.names.ai-insider',
  'true-crime': 'news.templates.names.true-crime',
  'history-buff': 'news.templates.names.history-buff',
  bookworm: 'news.templates.names.bookworm',
  'pop-culture': 'news.templates.names.pop-culture',
  'esports-fan': 'news.templates.names.esports-fan',
  outdoors: 'news.templates.names.outdoors',
  'anime-manga': 'news.templates.names.anime-manga',
  'football-fan': 'news.templates.names.football-fan',
  'cricket-fan': 'news.templates.names.cricket-fan',
  'fight-fan': 'news.templates.names.fight-fan',
  'deal-hunter': 'news.templates.names.deal-hunter',
  'personal-finance': 'news.templates.names.personal-finance',
  founder: 'news.templates.names.founder',
  'home-garden': 'news.templates.names.home-garden',
  photographer: 'news.templates.names.photographer',
  academia: 'news.templates.names.academia',
  researcher: 'news.templates.names.researcher',
  'clean-energy': 'news.templates.names.clean-energy',
  'my-country': 'news.templates.names.my-country',
} as const

const BLURB_KEYS = {
  developer: 'news.templates.blurbs.developer',
  investor: 'news.templates.blurbs.investor',
  'news-junkie': 'news.templates.blurbs.news-junkie',
  'sports-fan': 'news.templates.blurbs.sports-fan',
  'movie-buff': 'news.templates.blurbs.movie-buff',
  'music-lover': 'news.templates.blurbs.music-lover',
  gamer: 'news.templates.blurbs.gamer',
  'science-nerd': 'news.templates.blurbs.science-nerd',
  'foodie-traveler': 'news.templates.blurbs.foodie-traveler',
  'comedy-fun': 'news.templates.blurbs.comedy-fun',
  'fitness-buff': 'news.templates.blurbs.fitness-buff',
  fashionista: 'news.templates.blurbs.fashionista',
  petrolhead: 'news.templates.blurbs.petrolhead',
  'crypto-trader': 'news.templates.blurbs.crypto-trader',
  'space-explorer': 'news.templates.blurbs.space-explorer',
  'ai-insider': 'news.templates.blurbs.ai-insider',
  'true-crime': 'news.templates.blurbs.true-crime',
  'history-buff': 'news.templates.blurbs.history-buff',
  bookworm: 'news.templates.blurbs.bookworm',
  'pop-culture': 'news.templates.blurbs.pop-culture',
  'esports-fan': 'news.templates.blurbs.esports-fan',
  outdoors: 'news.templates.blurbs.outdoors',
  'anime-manga': 'news.templates.blurbs.anime-manga',
  'football-fan': 'news.templates.blurbs.football-fan',
  'cricket-fan': 'news.templates.blurbs.cricket-fan',
  'fight-fan': 'news.templates.blurbs.fight-fan',
  'deal-hunter': 'news.templates.blurbs.deal-hunter',
  'personal-finance': 'news.templates.blurbs.personal-finance',
  founder: 'news.templates.blurbs.founder',
  'home-garden': 'news.templates.blurbs.home-garden',
  photographer: 'news.templates.blurbs.photographer',
  academia: 'news.templates.blurbs.academia',
  researcher: 'news.templates.blurbs.researcher',
  'clean-energy': 'news.templates.blurbs.clean-energy',
  'my-country': 'news.templates.blurbs.my-country',
} as const

type TemplateId = keyof typeof NAME_KEYS

const TemplateCard = ({
  template,
  bySourceId,
  hairline,
  active,
  onToggle,
}: {
  template: NewsTemplate
  bySourceId: Map<string, NewsSourceMeta>
  hairline: StyleProp<ViewStyle>
  active: boolean
  onToggle: () => void
}) => {
  const t = useT()
  const theme = useTheme()
  const sources = template.sources
    .map((sid) => bySourceId.get(sid))
    .filter((s): s is NewsSourceMeta => Boolean(s))
  const nameKey = NAME_KEYS[template.id as TemplateId]
  const blurbKey = BLURB_KEYS[template.id as TemplateId]
  if (sources.length === 0 || !nameKey || !blurbKey) return null
  return (
    <Box
      gap="spacing-8"
      paddingHorizontal="spacing-16"
      paddingVertical="spacing-12"
      flexDirection="column"
      style={hairline}
    >
      <Box flexDirection="row" alignItems="center" gap="spacing-8">
        <Text variant="bodySerif">{t(nameKey)}</Text>
        <Box flexGrow={1} />
        <Text variant="caption" color="subtext" style={KICKER_STYLE}>
          {t('news.templates.sourceCount', { count: sources.length })}
        </Text>
      </Box>
      <Text variant="caption" color="subtext">
        {t(blurbKey)}
      </Text>
      <Box flexDirection="row" alignItems="center" gap="spacing-8">
        <Box flexDirection="row" alignItems="center" gap="spacing-4">
          {sources.slice(0, PREVIEW_BADGES).map((s) => (
            <SourceBadge
              key={s.id}
              id={s.id}
              name={s.name}
              logo={s.logo}
              size={22}
            />
          ))}
          {sources.length > PREVIEW_BADGES ? (
            <Text variant="caption" color="subtext" style={KICKER_STYLE}>
              +{sources.length - PREVIEW_BADGES}
            </Text>
          ) : null}
        </Box>
        <Box flexGrow={1} />
        <Touchable
          onPress={() => {
            void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium)
            onToggle()
          }}
        >
          <Box
            flexDirection="row"
            alignItems="center"
            gap="spacing-4"
            paddingVertical="spacing-6"
            paddingHorizontal="spacing-12"
            borderRadius="border-radius-6"
            backgroundColor="primaryStrong"
          >
            {active ? (
              <MaterialIcons
                name="check"
                size={14}
                color={theme.colors.onAccent}
              />
            ) : null}
            <Text variant="caption" color="onAccent">
              {active
                ? t('news.templates.inCards', { count: sources.length })
                : t('news.templates.followAll', { count: sources.length })}
            </Text>
          </Box>
        </Touchable>
      </Box>
    </Box>
  )
}

/** The Templates view inside the source roster: every persona bundle the
 * server resolved for this device's country. */
export const TemplateGallery = ({
  sources,
  open,
}: {
  sources: NewsSourceMeta[]
  open: boolean
}) => {
  const t = useT()
  const theme = useTheme()
  const { data } = useNewsTemplates(open)
  const active = useSyncExternalStore(
    subscribeFocused,
    getActiveTemplatesSnapshot,
    getActiveTemplatesSnapshot,
  )
  const bySourceId = useMemo(
    () => new Map(sources.map((s) => [s.id, s])),
    [sources],
  )
  const templates = useMemo(() => data?.templates ?? [], [data])
  // Only the card sets that can actually render. TemplateCard returns null for a
  // card set whose sources the roster doesn't know (or that has no name/blurb
  // key), and in a virtualized list that is a zero-height row the reader
  // scrolls through - and a row whose height the list still has to account
  // for. Filtering here keeps the data and what's on screen the same length.
  const visible = useMemo(
    () =>
      templates.filter(
        (tpl) =>
          NAME_KEYS[tpl.id as TemplateId] &&
          BLURB_KEYS[tpl.id as TemplateId] &&
          tpl.sources.some((sid) => bySourceId.has(sid)),
      ),
    [templates, bySourceId],
  )
  // Templates are combinable toggles: the FIRST one replaces the card set, extra
  // ones union in, and toggling one off removes its sources - except those a
  // still-active template also claims. Mirrors the web gallery.
  const toggle = useCallback(
    (template: NewsTemplate) => {
      if (active.includes(template.id)) {
        const remaining = active.filter((id) => id !== template.id)
        const kept = new Set(
          templates
            .filter((other) => remaining.includes(other.id))
            .flatMap((other) => other.sources),
        )
        unfollowAll(template.sources.filter((sid) => !kept.has(sid)))
        setActiveTemplates(remaining)
      } else {
        if (active.length === 0) replaceAll(template.sources)
        else followAll(template.sources)
        setActiveTemplates([...active, template.id])
      }
    },
    // Stable between toggles so the list's renderItem is too - a new identity
    // every render would re-render every mounted row.
    [active, templates],
  )
  // Union of every card set's resolvable sources - what "Select all" follows and
  // "Deselect all" unfollows, with the template toggles kept in sync.
  const allSourceIds = useMemo(
    () =>
      Array.from(new Set(templates.flatMap((tpl) => tpl.sources))).filter(
        (sid) => bySourceId.has(sid),
      ),
    [templates, bySourceId],
  )
  const hairline = {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: theme.colors.border,
  }
  // Virtualized, like the language sheet next door (which was the same
  // ScrollView mistake). Every card carries up to PREVIEW_BADGES remote
  // images, so mounting all ~35 committed ~600 views and up to 210 image
  // requests in a single frame - and this is the FIRST-LAUNCH screen, where
  // that frame already competes with the roster, card set and headline fetches.
  // Only the visible screenful mounts now.
  const renderItem = useCallback(
    ({ item }: { item: NewsTemplate }) => (
      <TemplateCard
        template={item}
        bySourceId={bySourceId}
        hairline={hairline}
        active={active.includes(item.id)}
        onToggle={() => toggle(item)}
      />
    ),
    // `hairline` is rebuilt each render; it is two static values off the
    // theme, so key the callback on what actually changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [bySourceId, active, toggle, theme.colors.border],
  )
  return (
    <FlashList
      data={visible}
      keyExtractor={templateKey}
      // Rows read `active`, which lives outside the row's own props.
      extraData={active.join(',')}
      renderItem={renderItem}
      ListHeaderComponent={
        <>
          <Box
            gap="spacing-2"
            paddingHorizontal="spacing-16"
            paddingVertical="spacing-8"
            flexDirection="column"
            style={hairline}
          >
            <Text variant="bodySerif">{t('news.templates.title')}</Text>
            <Text variant="caption" color="subtext">
              {t('news.templates.subtitle')}
            </Text>
          </Box>
          <TemplateActions
            hairline={hairline}
            count={allSourceIds.length}
            onSelectAll={() => {
              followAll(allSourceIds)
              setActiveTemplates(templates.map((tpl) => tpl.id))
            }}
            onDeselectAll={() => {
              unfollowAll(allSourceIds)
              setActiveTemplates([])
            }}
          />
        </>
      }
    />
  )
}
