import { Box } from '@/components/Shared/Box'
import { GlassDialog } from '@/components/Shared/GlassDialog'
import { Input } from '@/components/Shared/Input'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import {
  asSupported,
  filterPickerRows,
  LanguageRow,
  pickerRowKey,
} from '@/components/Settings/LanguagePicker'
import { useTheme } from '@/design-system/useTheme'
import { useLocale, useT } from '@/providers/LocaleProvider'
import {
  getFlagSnapshot,
  setLocaleOverride,
  subscribeFlag,
} from '@/utils/locale'
import { deviceCountryLoose } from '@/utils/weather'
import type { SupportedLocale } from '@outception-com/i18n'
import MaterialIcons from '@expo/vector-icons/MaterialIcons'
import { FlashList } from '@shopify/flash-list'
import { useCallback, useState, useSyncExternalStore } from 'react'
import { StyleSheet } from 'react-native'

/**
 * The language picker as a frosted modal card over the wall, mirroring the
 * web's language dialog: it opens straight onto the pinned filter input and
 * the language list (no intermediate step), the wall stays visible (blurred)
 * behind the card, and tapping outside — or the ✕ — dismisses it.
 */
export const LanguageSheet = ({
  visible,
  onClose,
}: {
  visible: boolean
  onClose: () => void
}) => {
  const theme = useTheme()
  const t = useT()
  const [filter, setFilter] = useState('')
  const active = asSupported(useLocale())
  // The English flag the reader picked (persisted), so e.g. "English (Ireland)"
  // stays checked. Detected region before the US default, matching the web.
  const flagCountry = useSyncExternalStore(
    subscribeFlag,
    getFlagSnapshot,
    getFlagSnapshot,
  )
  const activeEnglishCountry = flagCountry ?? deviceCountryLoose() ?? 'US'

  const close = () => {
    setFilter('')
    onClose()
  }

  const choose = useCallback(
    (locale: SupportedLocale, country?: string) => {
      setLocaleOverride(locale, country)
      setFilter('')
      onClose()
    },
    [onClose],
  )

  const rows = filterPickerRows(filter)

  return (
    <GlassDialog visible={visible} onClose={close}>
      {/* Pinned above the list, like the web's sticky paper-search-header:
          a borderless command-palette input over a hairline rule. */}
      <Box
        flexDirection="row"
        alignItems="center"
        gap="spacing-8"
        paddingHorizontal="spacing-16"
        paddingVertical="spacing-4"
        style={{
          borderBottomWidth: StyleSheet.hairlineWidth,
          borderBottomColor: theme.colors.border,
        }}
      >
        <MaterialIcons name="search" size={18} color={theme.colors.subtext} />
        <Input
          value={filter}
          onChangeText={setFilter}
          placeholder={t('news.language.placeholder')}
          autoCapitalize="none"
          autoCorrect={false}
          style={{
            flex: 1,
            borderWidth: 0,
            backgroundColor: 'transparent',
            paddingHorizontal: 0,
          }}
        />
        <Touchable onPress={close} accessibilityLabel={t('errors.close')}>
          <MaterialIcons name="close" size={22} color={theme.colors.text} />
        </Touchable>
      </Box>
      {/* Virtualized (was a ScrollView mounting all ~58 rows in the open
          tap's frame): only the visible screenful mounts, so the dialog
          appears without a long frame. */}
      <Box flex={1}>
        {rows.length === 0 ? (
          <Box paddingVertical="spacing-12" paddingHorizontal="spacing-12">
            <Text variant="caption" color="subtext">
              {t('news.mobile.noLanguages')}
            </Text>
          </Box>
        ) : (
          <FlashList
            data={rows}
            keyExtractor={pickerRowKey}
            extraData={`${active}|${activeEnglishCountry}`}
            renderItem={({ item }) => (
              <LanguageRow
                row={item}
                active={active}
                activeEnglishCountry={activeEnglishCountry}
                onChoose={choose}
              />
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
    </GlassDialog>
  )
}
