import { Box } from '@/components/Shared/Box'
import { GlassDialog } from '@/components/Shared/GlassDialog'
import { Input } from '@/components/Shared/Input'
import { Touchable } from '@/components/Shared/Touchable'
import { LanguageRows } from '@/components/Settings/LanguagePicker'
import { useTheme } from '@/design-system/useTheme'
import { useT } from '@/providers/LocaleProvider'
import MaterialIcons from '@expo/vector-icons/MaterialIcons'
import { useState } from 'react'
import { ScrollView, StyleSheet } from 'react-native'

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

  const close = () => {
    setFilter('')
    onClose()
  }

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
      <ScrollView
        contentContainerStyle={{
          paddingHorizontal: theme.spacing['spacing-8'],
          paddingTop: theme.spacing['spacing-4'],
          paddingBottom: theme.spacing['spacing-16'],
        }}
        keyboardShouldPersistTaps="handled"
      >
        <LanguageRows filter={filter} onPicked={close} />
      </ScrollView>
    </GlassDialog>
  )
}
