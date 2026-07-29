import { Box } from '@/components/Shared/Box'
import { Input } from '@/components/Shared/Input'
import { LocaleFlag } from '@/components/Shared/LocaleFlag'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useLocale, useT } from '@/providers/LocaleProvider'
import { getFlagSnapshot, subscribeFlag } from '@/utils/locale'
import { LOCALE_NAMES } from '@outception-com/i18n'
import { deviceCountryLoose } from '@/utils/weather'
import { useState, useSyncExternalStore } from 'react'
import { asSupported, enFlag, FLAGS, LanguageRows } from './LanguagePicker'

/** A settings row that expands to the supported-UI-languages list (shared with
 * the wall's language dialog via LanguageRows). Picking one overrides the
 * device-detected locale (persisted), and every `useT` consumer re-renders. */
export const LanguageSetting = ({
  onPicked,
}: { onPicked?: () => void } = {}) => {
  const t = useT()
  const active = asSupported(useLocale())
  const [open, setOpen] = useState(false)
  // Web's picker is a searchable command dialog; without a filter this list is
  // 52 rows to scroll on a phone.
  const [filter, setFilter] = useState('')
  // The English flag the reader picked (persisted), so the collapsed row keeps
  // showing e.g. the Irish flag for "English (Ireland)".
  const flagCountry = useSyncExternalStore(
    subscribeFlag,
    getFlagSnapshot,
    getFlagSnapshot,
  )
  // Detected region before the US default, matching app/index.tsx and the web.
  const activeEnglishCountry = flagCountry ?? deviceCountryLoose() ?? 'US'

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
            <LocaleFlag
              locale={active}
              emoji={
                active === 'en' ? enFlag(activeEnglishCountry) : FLAGS[active]
              }
            />
            <Text variant="body" color="subtext">
              {LOCALE_NAMES[active]}
            </Text>
          </Box>
        </Box>
      </Touchable>

      {open ? (
        <Box gap="spacing-4" paddingBottom="spacing-8">
          <Box paddingHorizontal="spacing-4" paddingBottom="spacing-4">
            <Input
              value={filter}
              onChangeText={setFilter}
              placeholder={t('news.mobile.filterLanguages')}
              autoCapitalize="none"
              autoCorrect={false}
            />
          </Box>
          <LanguageRows
            filter={filter}
            onPicked={() => {
              onPicked?.()
              setFilter('')
              setOpen(false)
            }}
          />
        </Box>
      ) : null}
    </Box>
  )
}
