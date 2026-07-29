import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useT } from '@/providers/LocaleProvider'
import { useState } from 'react'
import { LegalModal } from './LegalModal'
import { PrivacyContent } from './PrivacyContent'
import { TermsContent } from './TermsContent'

type LegalDoc = 'privacy' | 'terms' | null

/** The wall's legal footer: copyright · Privacy · Terms, where Privacy and Terms
 * open in-app popups over the wall (the mobile analogue of the web footer). */
export const LegalFooter = () => {
  const t = useT()
  const [open, setOpen] = useState<LegalDoc>(null)
  const close = () => setOpen(null)
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
      <Touchable onPress={() => setOpen('privacy')}>
        <Text variant="caption" color="pageEndText">
          {t('news.privacy')}
        </Text>
      </Touchable>
      <Text variant="caption" color="pageEndText">
        ·
      </Text>
      <Touchable onPress={() => setOpen('terms')}>
        <Text variant="caption" color="pageEndText">
          {t('news.terms')}
        </Text>
      </Touchable>

      <LegalModal
        visible={open === 'privacy'}
        title="Privacy Policy"
        onClose={close}
      >
        <PrivacyContent />
      </LegalModal>
      <LegalModal
        visible={open === 'terms'}
        title="Terms of Service"
        onClose={close}
      >
        <TermsContent />
      </LegalModal>
    </Box>
  )
}
