import { GameStrip } from '@/components/News/GameStrip'
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
import {
  getGamePlayingSnapshot,
  subscribeGamePlaying,
} from '@/utils/gamePlaying'
import {
  getFlagSnapshot,
  setLocaleOverride,
  subscribeFlag,
  toSupportedLocale,
} from '@/utils/locale'
import { deviceCountryLoose } from '@/utils/weather'
import { LegalFooter, type LegalDoc } from '@/components/Legal/LegalFooter'
import { LegalModal } from '@/components/Legal/LegalModal'
import { PrivacyContent } from '@/components/Legal/PrivacyContent'
import { TermsContent } from '@/components/Legal/TermsContent'
import { UpdateBanner } from '@/components/Shared/UpdateBanner'
import { useHomeQuickActions } from '@/hooks/useHomeQuickActions'
import { useLocalSearchParams } from 'expo-router'
import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { StatusBar } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

/** The short rule either side of the mark, matching the web header's
 * `rule-hairline` ornament. The web paints ink at 7-8% ALPHA over the page
 * (color-mix(... transparent)), so the line reads as "the background, slightly
 * shaded" on any gradient. A premixed opaque color (the old borderFaint) was
 * mixed against the flat base tone and rendered as a black bar wherever the
 * page gradient is lighter than the base. */
const Hairline = () => {
  const theme = useTheme()
  return (
    <Box
      width={48}
      height={1}
      style={{ backgroundColor: `${theme.colors['foreground-regular']}14` }}
    />
  )
}

export default function Home() {
  // Shared-card deep link (https://outception.com/?card=<id>&lang=<locale>) —
  // land the recipient on exactly the card that was shared, like the web wall.
  const { card, lang } = useLocalSearchParams<{
    card?: string
    lang?: string
  }>()
  const sharedCardId = typeof card === 'string' && card ? card : undefined
  const active = asSupported(useLocale())
  // The link also carries the sharer's language (web ranks a shared ?lang
  // above every other locale signal). Apply it through the same override the
  // language picker uses, so an explicit pick later simply overwrites it —
  // which is why it must apply AT MOST ONCE: the param survives re-mounts,
  // and re-applying it would clobber that later pick. A ?lang already equal
  // to the active locale is a no-op and is skipped outright.
  const sharedLang = typeof lang === 'string' ? toSupportedLocale(lang) : null
  const sharedLangApplied = useRef(false)
  useEffect(() => {
    if (!sharedLang || sharedLangApplied.current) return
    // Armed even when the link's language already matches: skipping without
    // arming left the ref false, so the reader's FIRST manual pick re-fired
    // this effect (active changed) and reverted them to the sharer's language.
    sharedLangApplied.current = true
    if (sharedLang !== active) setLocaleOverride(sharedLang)
  }, [sharedLang, active])
  const [mode, setMode] = useState<FeedMode>('deck')
  const [languageOpen, setLanguageOpen] = useState(false)
  const [legalOpen, setLegalOpen] = useState<LegalDoc | null>(null)
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
  const flagCountry = useSyncExternalStore(
    subscribeFlag,
    getFlagSnapshot,
    getFlagSnapshot,
  )
  // While a game is being played the gem ornament steps aside — the header
  // shrinks and the card rides up (web WallOrnament returns null during play).
  const gamePlaying = useSyncExternalStore(
    subscribeGamePlaying,
    getGamePlayingSnapshot,
    getGamePlayingSnapshot,
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
            {/* Web (NewsNavTabs): "Your deck" keeps the raised pill
              PERMANENTLY — the Sources sheet is a palette over the deck, not
              a place you navigate to — and "More" stays a plain ghost label. */}
            <NavTab
              label={t('news.tabs.yourDeck')}
              active
              onPress={() => {
                setMode('deck')
                setSearchFocus(false)
              }}
            />
            <NavTab
              label={t('news.tabs.more')}
              active={false}
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
            (LandingLayout `marginTop={{base:'2xl'}}`). During play it steps
            aside entirely (web WallOrnament) so the game card rides up. */}
          {gamePlaying ? null : (
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
          )}
        </Box>
        {/* The live game's controls + clue live on the wall between the
          header and the deck, not inside the card (web GameNoteBar) — they
          take the slot the gem vacates during play. Renders nothing at all
          when no game is publishing, so the deck never shifts. */}
        <GameStrip />
        <NewsFeed
          sharedCardId={sharedCardId}
          onBrowse={() => setMode('sources')}
        />
        <LegalFooter onOpen={setLegalOpen} />
        {/* The store-update nudge floats over the wall's bottom edge, the
          app twin of the web cookie notice. Inside the SafeAreaView (its own
          bottom offset adds the inset) but before the sheets, so an open
          dialog covers it. */}
        <UpdateBanner />
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
      <LegalModal
        visible={legalOpen === 'privacy'}
        title="Privacy Policy"
        onClose={() => setLegalOpen(null)}
      >
        <PrivacyContent />
      </LegalModal>
      <LegalModal
        visible={legalOpen === 'terms'}
        title="Terms of Service"
        onClose={() => setLegalOpen(null)}
      >
        <TermsContent />
      </LegalModal>
    </Box>
  )
}
