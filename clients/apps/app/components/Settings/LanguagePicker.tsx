import { Box } from '@/components/Shared/Box'
import { LocaleFlag } from '@/components/Shared/LocaleFlag'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { KICKER_STYLE } from '@/components/News/newsStyles'
import { useTheme } from '@/design-system/useTheme'
import MaterialIcons from '@expo/vector-icons/MaterialIcons'
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
import { deviceCountryLoose } from '@/utils/weather'
import { memo, useSyncExternalStore } from 'react'

// English content is the same everywhere, but readers identify with their own
// country's flag - so English is offered under each of the main English-speaking
// flags. Every entry selects the `en` locale; only the flag differs.
const ENGLISH_VARIANTS: { country: string; flag: string; label: string }[] = [
  { country: 'US', flag: '🇺🇸', label: 'English (US)' },
  { country: 'GB', flag: '🇬🇧', label: 'English (UK)' },
  { country: 'IE', flag: '🇮🇪', label: 'English (Ireland)' },
  { country: 'AU', flag: '🇦🇺', label: 'English (Australia)' },
  { country: 'CA', flag: '🇨🇦', label: 'English (Canada)' },
  { country: 'NZ', flag: '🇳🇿', label: 'English (New Zealand)' },
]

export type PickerRow =
  | { kind: 'en'; country: string; flag: string; label: string }
  | { kind: 'lang'; locale: SupportedLocale }

// Flag emoji render as flags on iOS and Android (unlike Windows desktop), so
// the mobile picker uses them directly. Each language maps to the country most
// conventionally associated with it - its country of origin where one exists
// (Spanish → Spain, Portuguese stays Brazil-first with pt-PT alongside).
export const FLAGS: Record<SupportedLocale, string> = {
  en: '🇺🇸',
  es: '🇪🇸',
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

export const asSupported = (locale: string): SupportedLocale =>
  (toSupportedLocale(locale) ?? 'en') as SupportedLocale

const PICKER_ROWS: PickerRow[] = [
  ...ENGLISH_VARIANTS.map((v) => ({ kind: 'en' as const, ...v })),
  ...(SUPPORTED_LOCALES as readonly SupportedLocale[])
    .filter((l) => l !== 'en')
    .map((locale) => ({ kind: 'lang' as const, locale })),
]

/** The flag for an English-speaking region. Unlisted regions (a German phone
 * running English, say) get a globe rather than a US flag, which would state
 * something untrue about the reader. */
export const enFlag = (country: string): string =>
  ENGLISH_VARIANTS.find((v) => v.country === country)?.flag ?? '🌐'

/** The picker rows matching `filter` (name or code), unfiltered when blank. */
export const filterPickerRows = (filter: string): PickerRow[] => {
  const needle = filter.trim().toLowerCase()
  if (!needle) return PICKER_ROWS
  return PICKER_ROWS.filter((row) => {
    const label =
      row.kind === 'en'
        ? row.label
        : LOCALE_NAMES[row.locale as SupportedLocale]
    const code = row.kind === 'en' ? `en-${row.country}` : row.locale
    return (
      label.toLowerCase().includes(needle) ||
      code.toLowerCase().includes(needle)
    )
  })
}

export const pickerRowKey = (row: PickerRow): string =>
  row.kind === 'en' ? `en-${row.country}` : row.locale

/** One picker row. Memoized so a virtualized list can recycle it and a
 * selection change only re-renders the rows whose checkmark flips. */
export const LanguageRow = memo(function LanguageRow({
  row,
  active,
  activeEnglishCountry,
  onChoose,
}: {
  row: PickerRow
  active: SupportedLocale
  activeEnglishCountry: string
  onChoose: (locale: SupportedLocale, country?: string) => void
}) {
  const theme = useTheme()
  const isEn = row.kind === 'en'
  const locale: SupportedLocale = isEn ? 'en' : row.locale
  const label = isEn ? row.label : LOCALE_NAMES[locale]
  const flag = isEn ? row.flag : FLAGS[locale]
  const code = isEn ? row.country : locale
  const checked = isEn
    ? active === 'en' &&
      row.country.toUpperCase() === activeEnglishCountry.toUpperCase()
    : locale === active
  return (
    <Touchable onPress={() => onChoose(locale, isEn ? row.country : undefined)}>
      <Box
        flexDirection="row"
        alignItems="center"
        gap="spacing-8"
        paddingVertical="spacing-8"
        paddingHorizontal="spacing-12"
        borderRadius="border-radius-12"
      >
        <LocaleFlag locale={locale} emoji={flag} />
        <Text variant="body">{label}</Text>
        {/* Web: the locale code as an uppercase micro-kicker, and a
            right-aligned check on the active row (no fill). */}
        <Text color="subtext" style={KICKER_STYLE}>
          {code}
        </Text>
        <Box flex={1} alignItems="flex-end">
          {checked ? (
            <MaterialIcons name="check" size={16} color={theme.colors.text} />
          ) : null}
        </Box>
      </Box>
    </Touchable>
  )
})

/** The picker's row list, filtered by `filter`: every supported UI language,
 * with English offered under several English-speaking flags. Picking one
 * overrides the device-detected locale (persisted) and every `useT` consumer
 * re-renders. Shared by the language dialog (sheet) and the settings row -
 * scrolling is the caller's concern. */
export const LanguageRows = ({
  filter,
  onPicked,
}: {
  filter: string
  onPicked?: () => void
}) => {
  const t = useT()
  const active = asSupported(useLocale())
  // The English flag the reader picked (persisted), so e.g. "English (Ireland)"
  // stays checked. Detected region before the US default, matching the web.
  const flagCountry = useSyncExternalStore(
    subscribeFlag,
    getFlagSnapshot,
    getFlagSnapshot,
  )
  const activeEnglishCountry = flagCountry ?? deviceCountryLoose() ?? 'US'

  const choose = (locale: SupportedLocale, country?: string) => {
    setLocaleOverride(locale, country)
    onPicked?.()
  }

  const rows = filterPickerRows(filter)

  if (rows.length === 0) {
    return (
      <Box paddingVertical="spacing-12" paddingHorizontal="spacing-12">
        <Text variant="caption" color="subtext">
          {t('news.mobile.noLanguages')}
        </Text>
      </Box>
    )
  }

  return (
    <>
      {rows.map((row) => (
        <LanguageRow
          key={pickerRowKey(row)}
          row={row}
          active={active}
          activeEnglishCountry={activeEnglishCountry}
          onChoose={choose}
        />
      ))}
    </>
  )
}
