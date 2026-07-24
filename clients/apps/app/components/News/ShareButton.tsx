import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useLocale, useT } from '@/providers/LocaleProvider'
import { shareCardUrl } from '@/utils/news'
import MaterialIcons from '@expo/vector-icons/MaterialIcons'
import { Platform, Share } from 'react-native'

/** Share a single card via the OS share sheet (every installed app — WhatsApp,
 * X, Telegram, Messenger, Mail, …). Shares a web link that opens the wall on
 * this exact source in the reader's language, so the recipient sees the same
 * card and gets the rich link preview. An oval pill with a label; mirrors the
 * web card. */
export const ShareButton = ({
  source,
}: {
  source: { id: string; name: string }
}) => {
  const locale = useLocale()
  const t = useT()
  const theme = useTheme()

  const onPress = async () => {
    const url = shareCardUrl(source.id, locale)
    const message = t('news.share.text', { source: source.name })
    try {
      await Share.share(
        Platform.OS === 'ios'
          ? { message, url }
          : { message: `${message} ${url}` },
      )
    } catch {
      // user dismissed the share sheet
    }
  }

  return (
    <Touchable onPress={onPress} accessibilityLabel={t('news.share.label')}>
      <Box
        flexDirection="row"
        alignItems="center"
        gap="spacing-4"
        paddingVertical="spacing-4"
        paddingHorizontal="spacing-12"
        borderRadius="border-radius-8"
        borderWidth={1}
        borderColor="border"
      >
        <MaterialIcons name="share" size={14} color={theme.colors.subtext} />
        <Text variant="caption" color="subtext">
          {t('news.share.label')}
        </Text>
      </Box>
    </Touchable>
  )
}
