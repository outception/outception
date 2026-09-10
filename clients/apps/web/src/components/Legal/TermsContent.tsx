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

/** The Terms of Service body - shared by the /terms route and the landing
 * page's popup dialog. A client component, like the privacy policy. */
export const TermsContent = () => {
  const t = useT()
  const locale = useLocale()
  return (
    <Box flexDirection="column" rowGap="2xl">
      <LegalHeader
        title={t('legal.terms.title')}
        lastUpdated={t('legal.lastUpdated', { date: EFFECTIVE_DATE })}
        prevails={locale === DEFAULT_LOCALE ? null : t('legal.englishPrevails')}
      />

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
