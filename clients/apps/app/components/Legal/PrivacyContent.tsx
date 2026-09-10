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

const B = ({ children }: { children: ReactNode }) => (
  <Text variant="bodyMedium" color="text">
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
    <Text variant="bodyMedium" color="text">
      {title}
    </Text>
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

/** A bullet that opens with a bold term, e.g. "Preferences: the sources you
 * follow…". The label and the sentence are separate keys so a translator can
 * move the term without losing the bold, and so no locale has to reproduce
 * punctuation that belongs to the layout. */
const LabelledBullet = ({ label, body }: { label: string; body: string }) => (
  <Bullet>
    <B>{label}</B>
    {`: ${body}`}
  </Bullet>
)

/** The Privacy Policy body, shown in the in-app popup. Mirrors the web text.
 * Every sentence comes from the translation files, so a reader sees it in
 * their own language - with the English-prevails note the law needs. */
export const PrivacyContent = () => {
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

      <P>{t('legal.privacy.intro', { email: CONTACT_EMAIL })}</P>

      <Section title={t('legal.privacy.collect.title')}>
        <P>{t('legal.privacy.collect.lead')}</P>
        <LabelledBullet
          label={t('legal.privacy.collect.preferencesLabel')}
          body={t('legal.privacy.collect.preferences')}
        />
        <LabelledBullet
          label={t('legal.privacy.collect.deviceLabel')}
          body={t('legal.privacy.collect.device')}
        />
        <LabelledBullet
          label={t('legal.privacy.collect.locationLabel')}
          body={t('legal.privacy.collect.location')}
        />
        <LabelledBullet
          label={t('legal.privacy.collect.diagnosticsLabel')}
          body={t('legal.privacy.collect.diagnostics')}
        />
        <P>{t('legal.privacy.collect.noAccount')}</P>
      </Section>

      <Section title={t('legal.privacy.advertising.title')}>
        <P>{t('legal.privacy.advertising.body')}</P>
      </Section>

      <Section title={t('legal.privacy.analytics.title')}>
        <P>{t('legal.privacy.analytics.body')}</P>
      </Section>

      <Section title={t('legal.privacy.why.title')}>
        <LabelledBullet
          label={t('legal.privacy.why.consentLabel')}
          body={t('legal.privacy.why.consent')}
        />
        <LabelledBullet
          label={t('legal.privacy.why.legitimateLabel')}
          body={t('legal.privacy.why.legitimate')}
        />
      </Section>

      <Section title={t('legal.privacy.sharing.title')}>
        <P>{t('legal.privacy.sharing.body')}</P>
      </Section>

      <Section title={t('legal.privacy.retention.title')}>
        <P>{t('legal.privacy.retention.body', { email: CONTACT_EMAIL })}</P>
      </Section>

      <Section title={t('legal.privacy.changes.title')}>
        <P>{t('legal.privacy.changes.body')}</P>
      </Section>

      <Section title={t('legal.privacy.contact.title')}>
        <P>{t('legal.privacy.contact.body', { email: CONTACT_EMAIL })}</P>
      </Section>
    </Box>
  )
}
