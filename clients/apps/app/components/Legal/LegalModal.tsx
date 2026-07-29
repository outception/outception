import { Box } from '@/components/Shared/Box'
import { GlassDialog } from '@/components/Shared/GlassDialog'
import { Touchable } from '@/components/Shared/Touchable'
import { useT } from '@/providers/LocaleProvider'
import { useTheme } from '@/design-system/useTheme'
import MaterialIcons from '@expo/vector-icons/MaterialIcons'
import type { ReactNode } from 'react'
import { ScrollView } from 'react-native'

/** An in-app legal document (Privacy / Terms) as a frosted card over the wall —
 * the same GlassDialog surface as the search and language sheets (and the
 * mobile analogue of the web LegalDialog): tap-outside or the ✕ dismisses, the
 * body scrolls inside the card. Like GlassDialog's other consumers this must
 * mount OUTSIDE the SafeAreaView (see app/index.tsx) so the scrim reaches the
 * screen edges. The title isn't rendered as a visible heading — the document
 * body opens with its own — but it still names the dialog for screen readers. */
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
  return (
    <GlassDialog visible={visible} onClose={onClose}>
      <Box flex={1} accessibilityLabel={title}>
        <Box
          flexDirection="row"
          justifyContent="flex-end"
          paddingHorizontal="spacing-16"
          paddingTop="spacing-12"
        >
          <Touchable onPress={onClose} accessibilityLabel={t('errors.close')}>
            <MaterialIcons name="close" size={22} color={theme.colors.text} />
          </Touchable>
        </Box>
        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{
            paddingHorizontal: theme.spacing['spacing-16'],
            paddingBottom: theme.spacing['spacing-16'],
          }}
        >
          {children}
        </ScrollView>
      </Box>
    </GlassDialog>
  )
}
