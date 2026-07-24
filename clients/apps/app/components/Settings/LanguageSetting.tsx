import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useLocale, useT } from '@/providers/LocaleProvider'
import {
  getFlagSnapshot,
  setLocaleOverride,
  subscribeFlag,
  toSupportedLocale,
} from '@/utils/locale'
import {
  LOCALE_NAMES,
  SUPPORTED_LOCALES,
  type SupportedLocale,
} from '@outception-com/i18n'
import { useState, useSyncExternalStore } from 'react'

// English content is the same everywhere, but readers identify with their own
// country's flag — so English is offered under each of the main English-speaking
// flags. Every entry selects the `en` locale; only the flag differs.
const ENGLISH_VARIANTS: { country: string; flag: string; label: string }[] = [
  { country: 'US', flag: '🇺🇸', label: 'English (US)' },
  { country: 'GB', flag: '🇬🇧', label: 'English (UK)' },
  { country: 'IE', flag: '🇮🇪', label: 'English (Ireland)' },
  { country: 'AU', flag: '🇦🇺', label: 'English (Australia)' },
  { country: 'CA', flag: '🇨🇦', label: 'English (Canada)' },
  { country: 'NZ', flag: '🇳🇿', label: 'English (New Zealand)' },
]

type PickerRow =
  | { kind: 'en'; country: string; flag: string; label: string }
  | { kind: 'lang'; locale: SupportedLocale }

// Flag emoji render as flags on iOS and Android (unlike Windows desktop), so
// the mobile picker uses them directly. Each language maps to the country with
// the most speakers of it (Spanish → Mexico, Arabic → Egypt, etc.).
const FLAGS: Record<SupportedLocale, string> = {
  en: '🇺🇸',
  es: '🇲🇽',
  fr: '🇫🇷',
  de: '🇩🇪',
  it: '🇮🇹',
  pt: '🇧🇷',
  'pt-PT': '🇵🇹',
  nl: '🇳🇱',
  sv: '🇸🇪',
  pl: '🇵🇱',
  ru: '🇷🇺',
  uk: '🇺🇦',
  tr: '🇹🇷',
  ar: '🇪🇬',
  he: '🇮🇱',
  fa: '🇮🇷',
  hi: '🇮🇳',
  bn: '🇧🇩',
  ur: '🇵🇰',
  'zh-Hans': '🇨🇳',
  'zh-Hant': '🇹🇼',
  ja: '🇯🇵',
  ko: '🇰🇷',
  id: '🇮🇩',
  ms: '🇲🇾',
  tl: '🇵🇭',
  vi: '🇻🇳',
  th: '🇹🇭',
  cs: '🇨🇿',
  sk: '🇸🇰',
  sl: '🇸🇮',
  hu: '🇭🇺',
  ro: '🇷🇴',
  bg: '🇧🇬',
  sr: '🇷🇸',
  sq: '🇦🇱',
  el: '🇬🇷',
  da: '🇩🇰',
  nb: '🇳🇴',
  fi: '🇫🇮',
  et: '🇪🇪',
  lv: '🇱🇻',
  lt: '🇱🇹',
  ga: '🇮🇪',
  ca: '🇪🇸',
  eu: '🇪🇸',
  hr: '🇭🇷',
}

const asSupported = (locale: string): SupportedLocale =>
  (toSupportedLocale(locale) ?? 'en') as SupportedLocale

const PICKER_ROWS: PickerRow[] = [
  ...ENGLISH_VARIANTS.map((v) => ({ kind: 'en' as const, ...v })),
  ...(SUPPORTED_LOCALES as readonly SupportedLocale[])
    .filter((l) => l !== 'en')
    .map((locale) => ({ kind: 'lang' as const, locale })),
]

const enFlag = (country: string): string =>
  ENGLISH_VARIANTS.find((v) => v.country === country)?.flag ?? '🇺🇸'

/** A settings row that expands to a list of the supported UI languages, with
 * English offered under several English-speaking flags. Picking one overrides
 * the device-detected locale (persisted), and every `useT` consumer re-renders. */
export const LanguageSetting = () => {
  const t = useT()
  const active = asSupported(useLocale())
  const [open, setOpen] = useState(false)
  // The English flag the reader picked (persisted), so the collapsed row keeps
  // showing e.g. the Irish flag for "English (Ireland)".
  const flagCountry = useSyncExternalStore(
    subscribeFlag,
    getFlagSnapshot,
    getFlagSnapshot,
  )
  const activeEnglishCountry = flagCountry ?? 'US'

  const choose = (locale: SupportedLocale, country?: string) => {
    setLocaleOverride(locale, country)
    setOpen(false)
  }

  return (
    <Box>
      <Touchable onPress={() => setOpen((v) => !v)}>
        <Box
          flexDirection="row"
          alignItems="center"
          justifyContent="space-between"
          paddingVertical="spacing-12"
        >
          <Text variant="body">{t('news.mobile.language')}</Text>
          <Box flexDirection="row" alignItems="center" gap="spacing-8">
            <Text variant="body">
              {active === 'en' ? enFlag(activeEnglishCountry) : FLAGS[active]}
            </Text>
            <Text variant="body" color="subtext">
              {LOCALE_NAMES[active]}
            </Text>
          </Box>
        </Box>
      </Touchable>

      {open ? (
        <Box gap="spacing-4" paddingBottom="spacing-8">
          {PICKER_ROWS.map((row) => {
            const isEn = row.kind === 'en'
            const locale: SupportedLocale = isEn ? 'en' : row.locale
            const label = isEn ? row.label : LOCALE_NAMES[locale]
            const flag = isEn ? row.flag : FLAGS[locale]
            const checked = isEn
              ? active === 'en' && row.country === activeEnglishCountry
              : locale === active
            return (
              <Touchable
                key={isEn ? `en-${row.country}` : locale}
                onPress={() => choose(locale, isEn ? row.country : undefined)}
              >
                <Box
                  flexDirection="row"
                  alignItems="center"
                  gap="spacing-8"
                  paddingVertical="spacing-8"
                  paddingHorizontal="spacing-12"
                  borderRadius="border-radius-12"
                  backgroundColor={checked ? 'card' : undefined}
                >
                  <Text variant="body">{flag}</Text>
                  <Text variant="body">{label}</Text>
                </Box>
              </Touchable>
            )
          })}
        </Box>
      ) : null}
    </Box>
  )
}
