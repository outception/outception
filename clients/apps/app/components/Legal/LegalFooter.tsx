import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useT } from '@/providers/LocaleProvider'

export type LegalDoc = 'privacy' | 'terms'

/** The wall's legal footer: copyright · Privacy · Terms. The documents open in
 * LegalModal (a GlassDialog card), which — like the other glass sheets — must
 * mount outside the SafeAreaView, so the home screen owns the open state and
 * this row only reports the tap. */
export const LegalFooter = ({
  onOpen,
}: {
  onOpen: (doc: LegalDoc) => void
}) => {
  const t = useT()
  return (
    <Box
      flexDirection="row"
      justifyContent="center"
      alignItems="center"
      gap="spacing-8"
      paddingVertical="spacing-16"
      paddingHorizontal="spacing-24"
      flexWrap="wrap"
    >
      <Text variant="caption" color="pageEndText">
        {t('news.footer')}
      </Text>
      <Text variant="caption" color="pageEndText">
        ·
      </Text>
      <Touchable onPress={() => onOpen('privacy')}>
        <Text variant="caption" color="pageEndText">
          {t('news.privacy')}
        </Text>
      </Touchable>
      <Text variant="caption" color="pageEndText">
        ·
      </Text>
      <Touchable onPress={() => onOpen('terms')}>
        <Text variant="caption" color="pageEndText">
          {t('news.terms')}
        </Text>
      </Touchable>
    </Box>
  )
}
