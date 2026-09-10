import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { useLocale, useT } from '@/providers/LocaleProvider'
import { DEFAULT_LOCALE } from '@outception-com/i18n'
import type { ReactNode } from 'react'

const CONTACT_EMAIL = 'hello@outception.com'
const EFFECTIVE_DATE = '19 August 2026'

const P = ({ children }: { children: ReactNode }) => (
  <Text variant="body" color="subtext">
    {children}
  </Text>
)

const Section = ({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) => (
  <Box gap="spacing-8">
    <Text variant="subtitle">{title}</Text>
    {children}
  </Box>
)

const Bullet = ({ children }: { children: ReactNode }) => (
  <Box flexDirection="row" gap="spacing-8" alignItems="flex-start">
    <Text variant="body" color="subtext">
      •
    </Text>
    <Text variant="body" color="subtext" style={{ flex: 1 }}>
      {children}
    </Text>
  </Box>
)

/** The Terms of Service body, shown in the in-app popup. Mirrors the web text.
 * Every sentence comes from the translation files, so a reader sees it in
 * their own language - with the English-prevails note the law needs. */
export const TermsContent = () => {
  const t = useT()
  const locale = useLocale()
  return (
    <Box gap="spacing-16" paddingBottom="spacing-16">
      <Text variant="caption" color="subtext">
        {t('legal.lastUpdated', { date: EFFECTIVE_DATE })}
      </Text>
      {locale !== DEFAULT_LOCALE ? (
        <Text variant="caption" color="subtext">
          {t('legal.englishPrevails')}
        </Text>
      ) : null}

      <P>{t('legal.terms.intro')}</P>

      <Section title={t('legal.terms.service.title')}>
        <P>{t('legal.terms.service.body')}</P>
      </Section>

      <Section title={t('legal.terms.use.title')}>
        <P>{t('legal.terms.use.lead')}</P>
        <Bullet>{t('legal.terms.use.law')}</Bullet>
        <Bullet>{t('legal.terms.use.disrupt')}</Bullet>
        <Bullet>{t('legal.terms.use.scrape')}</Bullet>
        <Bullet>{t('legal.terms.use.security')}</Bullet>
      </Section>

      <Section title={t('legal.terms.thirdParty.title')}>
        <P>{t('legal.terms.thirdParty.body')}</P>
      </Section>

      <Section title={t('legal.terms.ip.title')}>
        <P>{t('legal.terms.ip.body')}</P>
      </Section>

      <Section title={t('legal.terms.disclaimers.title')}>
        <P>{t('legal.terms.disclaimers.body')}</P>
      </Section>

      <Section title={t('legal.terms.liability.title')}>
        <P>{t('legal.terms.liability.body')}</P>
      </Section>

      <Section title={t('legal.terms.changes.title')}>
        <P>{t('legal.terms.changes.body')}</P>
      </Section>

      <Section title={t('legal.terms.law.title')}>
        <P>{t('legal.terms.law.body')}</P>
      </Section>

      <Section title={t('legal.terms.contact.title')}>
        <P>{t('legal.terms.contact.body', { email: CONTACT_EMAIL })}</P>
      </Section>
    </Box>
  )
}
