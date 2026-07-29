import { LanguageSheet } from '@/components/News/LanguageSheet'
import { NavTab, NewsFeed, type FeedMode } from '@/components/News/NewsFeed'
import { SourceSearchSheet } from '@/components/News/SourceSearchSheet'
import { useTone } from '@/design-system/toneStore'
import { useTheme } from '@/design-system/useTheme'
import {
  asSupported,
  enFlag,
  FLAGS,
} from '@/components/Settings/LanguagePicker'
import { Box } from '@/components/Shared/Box'
import { LocaleFlag } from '@/components/Shared/LocaleFlag'
import { Text } from '@/components/Shared/Text'
import { SpinningLogo } from '@/components/Shared/SpinningLogo'
import { Touchable } from '@/components/Shared/Touchable'
import { cycleEdition } from '@/design-system/themeStore'
import { useLocale, useT } from '@/providers/LocaleProvider'
import { getFlagSnapshot, subscribeFlag } from '@/utils/locale'
import { deviceCountryLoose } from '@/utils/weather'
import { LegalFooter } from '@/components/Legal/LegalFooter'
import { useHomeQuickActions } from '@/hooks/useHomeQuickActions'
import { useLocalSearchParams } from 'expo-router'
import { useState, useSyncExternalStore } from 'react'
import { StatusBar } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

/** The short rule either side of the mark, matching the web header's
 * `rule-hairline` ornament — ink at ~7%, near-invisible, not the 16% card rule. */
const Hairline = () => {
  const theme = useTheme()
  return (
    <Box
      width={48}
      height={1}
      style={{ backgroundColor: theme.colors.borderFaint }}
    />
  )
}

export default function Home() {
  // Shared-card deep link (https://outception.com/?card=<id>) — land the
  // recipient on exactly the card that was shared, like the web wall does.
  const { card } = useLocalSearchParams<{ card?: string }>()
  const sharedCardId = typeof card === 'string' && card ? card : undefined
  const [mode, setMode] = useState<FeedMode>('deck')
  const [languageOpen, setLanguageOpen] = useState(false)
  const [searchFocus, setSearchFocus] = useState(false)
  useHomeQuickActions((target) => {
    if (target === 'deck') {
      setMode('deck')
      return
    }
    setMode('sources')
    setSearchFocus(target === 'search')
  })
  const tone = useTone()
  const t = useT()
  const active = asSupported(useLocale())
  const flagCountry = useSyncExternalStore(
    subscribeFlag,
    getFlagSnapshot,
    getFlagSnapshot,
  )
  // Fall back to the detected region before defaulting to US — matching the
  // web, which uses its IP-country before the same default. Without this an
  // Irish reader with no explicit picker choice always saw a US flag.
  const currentFlag =
    active === 'en'
      ? enFlag(flagCountry ?? deviceCountryLoose() ?? 'US')
      : FLAGS[active]

  return (
    <Box flex={1}>
      <SafeAreaView style={{ flex: 1 }} edges={['top', 'bottom']}>
        <StatusBar
          barStyle={tone === 'dark' ? 'light-content' : 'dark-content'}
        />
        {/* Mirrors the web header exactly: the segmented pill on top — carrying
          the language chip as its last item — and the mark centered beneath it
          between two hairlines. Nothing on the sides. */}
        <Box
          alignItems="center"
          gap="spacing-12"
          paddingHorizontal="spacing-16"
          paddingVertical="spacing-12"
        >
          {/* Web `.paper-input`: a crisp ink-30% ring over a faint ink-3% field
            tint — the header's anchor, a step stronger than ordinary rules. */}
          <Box
            flexDirection="row"
            alignItems="center"
            gap="spacing-4"
            padding="spacing-4"
            borderRadius="border-radius-10"
            borderWidth={1}
            borderColor="borderStrong"
            backgroundColor="inputTint"
          >
            <NavTab
              label={t('news.tabs.yourDeck')}
              active={mode === 'deck'}
              onPress={() => {
                setMode('deck')
                setSearchFocus(false)
              }}
            />
            <NavTab
              label={t('news.tabs.more')}
              active={mode === 'sources'}
              onPress={() => {
                setMode('sources')
                setSearchFocus(false)
              }}
            />
            {/* Language override (no login), the last item in the pill exactly as
              in the web navbar. Opens a sheet over the wall rather than pushing
              a screen — the web picker is a dialog, not a page. */}
            <Touchable
              onPress={() => setLanguageOpen(true)}
              accessibilityLabel={t('news.mobile.language')}
            >
              <Box
                flexDirection="row"
                alignItems="center"
                gap="spacing-4"
                paddingVertical="spacing-4"
                paddingHorizontal="spacing-12"
                borderRadius="border-radius-8"
              >
                <LocaleFlag locale={active} emoji={currentFlag} />
                <Text
                  variant="caption"
                  color="subtext"
                  style={{ textTransform: 'uppercase' }}
                >
                  {active}
                </Text>
              </Box>
            </Touchable>
          </Box>

          {/* Web drops the mark 32px below the pill on phones
            (LandingLayout `marginTop={{base:'2xl'}}`). */}
          <Box
            flexDirection="row"
            alignItems="center"
            gap="spacing-12"
            marginTop="spacing-32"
          >
            <Hairline />
            <SpinningLogo
              size={32}
              onPress={() => cycleEdition(tone)}
              accessibilityLabel={t('news.deck.changeEdition')}
            />
            <Hairline />
          </Box>
        </Box>
        <NewsFeed
          sharedCardId={sharedCardId}
          onBrowse={() => setMode('sources')}
        />
        <LegalFooter />
      </SafeAreaView>
      {/* OUTSIDE the SafeAreaView: Yoga insets absolute children to the
          padding box, so inside it the dialogs' scrim would leave un-dimmed
          wall strips under the status bar and home indicator. The sheets
          apply their own insets internally (GlassDialog's SafeAreaView). */}
      <SourceSearchSheet
        visible={mode === 'sources'}
        onClose={() => {
          setMode('deck')
          setSearchFocus(false)
        }}
        autoFocusSearch={searchFocus}
      />
      <LanguageSheet
        visible={languageOpen}
        onClose={() => setLanguageOpen(false)}
      />
    </Box>
  )
}
