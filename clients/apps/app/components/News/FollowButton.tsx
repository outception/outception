import { Box } from '@/components/Shared/Box'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useT } from '@/providers/LocaleProvider'
import { removeFocus } from '@/utils/focusedSources'
import { hideSource } from '@/utils/hiddenSources'
import MaterialIcons from '@expo/vector-icons/MaterialIcons'

/** The one curation action a card offers: Unfollow. Removes the source from the
 * deck on this device (device-local, no login) — dropping it from the followed
 * set and hiding it from the wall. Sources are re-added from search. Icon-only
 * hairline chip to keep the header uncluttered; mirrors the web card. */
export const FollowButton = ({ sourceId }: { sourceId: string }) => {
  const t = useT()
  const theme = useTheme()

  const onPress = () => {
    removeFocus(sourceId)
    hideSource(sourceId)
  }

  return (
    <Touchable onPress={onPress} accessibilityLabel={t('news.follow.unfollow')}>
      <Box
        padding="spacing-8"
        borderRadius="border-radius-8"
        borderWidth={1}
        borderColor="border"
      >
        <MaterialIcons name="close" size={16} color={theme.colors.subtext} />
      </Box>
    </Touchable>
  )
}
