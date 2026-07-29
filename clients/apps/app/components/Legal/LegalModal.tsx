import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useT } from '@/providers/LocaleProvider'
import { useTheme } from '@/design-system/useTheme'
import { useTone } from '@/design-system/toneStore'
import MaterialIcons from '@expo/vector-icons/MaterialIcons'
import type { ReactNode } from 'react'
import { Modal, ScrollView, StyleSheet } from 'react-native'

/** An in-app legal document (Privacy / Terms) shown as a popup over the wall:
 * a dimmed scrim, tap-outside or the ✕ to dismiss, and the body scrolling inside
 * the card. The mobile analogue of the web LegalDialog. */
export const LegalModal = ({
  visible,
  title,
  onClose,
  children,
}: {
  visible: boolean
  title: string
  onClose: () => void
  children: ReactNode
}) => {
  const theme = useTheme()
  const t = useT()
  const tone = useTone()
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent
      navigationBarTranslucent
      onRequestClose={onClose}
    >
      <Box
        flex={1}
        justifyContent="center"
        alignItems="center"
        paddingHorizontal="spacing-16"
      >
        <Touchable
          onPress={onClose}
          feedback="none"
          style={StyleSheet.absoluteFill}
        >
          {/* Dimmed scrim behind the card; a plain overlay black, not a token. */}
          <Box
            style={[
              StyleSheet.absoluteFill,
              { backgroundColor: tone === 'dark' ? '#000000AA' : '#00000073' },
            ]}
          />
        </Touchable>
        <Box
          backgroundColor="card"
          borderRadius="border-radius-16"
          padding="spacing-16"
          style={{ width: '100%', maxHeight: '85%' }}
        >
          <Box
            flexDirection="row"
            alignItems="center"
            justifyContent="space-between"
            paddingBottom="spacing-12"
          >
            <Text variant="title">{title}</Text>
            <Touchable onPress={onClose} accessibilityLabel={t('errors.close')}>
              <MaterialIcons
                name="close"
                size={22}
                color={theme.colors.subtext}
              />
            </Touchable>
          </Box>
          <ScrollView showsVerticalScrollIndicator={false}>
            {children}
          </ScrollView>
        </Box>
      </Box>
    </Modal>
  )
}
