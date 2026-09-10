'use client'

import LogoIcon from '@/components/Brand/logos/LogoIcon'
import { useLocale, useT } from '@/providers/locale'
import { DEFAULT_LOCALE } from '@outception-com/i18n'
import { Text } from '@outception-com/orbit/Text'
import { Box } from '@outception-com/orbit/Box'
import Link from 'next/link'

const EFFECTIVE_DATE = '19 August 2026'
const CONTACT_EMAIL = 'hello@outception.com'

const P = ({ children }: { children: React.ReactNode }) => (
  <Text variant="body" as="p" color="muted">
    {children}
  </Text>
)

const H2 = ({ children }: { children: React.ReactNode }) => (
  <Text variant="heading-xs" as="h2">
    {children}
  </Text>
)

const Section = ({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) => (
  <Box as="section" flexDirection="column" rowGap="m">
    <H2>{title}</H2>
    {children}
  </Box>
)

const Bullet = ({ children }: { children: React.ReactNode }) => (
  <Box as="li" columnGap="s">
    <Text variant="body" color="disabled" aria-hidden>
      •
    </Text>
    <Text variant="body" as="span" color="muted">
      {children}
    </Text>
  </Box>
)

/** A bullet that opens with a bold term. Label and sentence are separate keys
 * so a translator can move the term without losing the emphasis, and so no
 * locale has to reproduce punctuation that belongs to the layout. */
const LabelledBullet = ({ label, body }: { label: string; body: string }) => (
  <Bullet>
    <strong>{label}</strong>
    {`: ${body}`}
  </Bullet>
)

/** Logo, title, date, and - away from English - the note that the English
 * text governs. */
const LegalHeader = ({
  title,
  lastUpdated,
  prevails,
}: {
  title: string
  lastUpdated: string
  prevails: string | null
}) => (
  <Box flexDirection="column" rowGap="l">
    <Link
      href="/"
      aria-label="Outception home"
      style={{ width: 'fit-content' }}
    >
      <LogoIcon size={48} className="text-black dark:text-white" />
    </Link>
    <Box flexDirection="column" rowGap="xs">
      <Text variant="heading-m" as="h1">
        {title}
      </Text>
      <Text variant="caption" color="disabled">
        {lastUpdated}
      </Text>
      {prevails ? (
        <Text variant="caption" color="disabled">
          {prevails}
        </Text>
      ) : null}
    </Box>
  </Box>
)

/** The Privacy Policy body - shared by the /privacy route and the landing
 * page's popup dialog. A client component because that dialog is one: every
 * sentence still comes from the translation files. */
export const PrivacyContent = () => {
  const t = useT()
  const locale = useLocale()
  return (
    <Box flexDirection="column" rowGap="2xl">
      <LegalHeader
        title={t('legal.privacy.title')}
        lastUpdated={t('legal.lastUpdated', { date: EFFECTIVE_DATE })}
        prevails={locale === DEFAULT_LOCALE ? null : t('legal.englishPrevails')}
      />

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
