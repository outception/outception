import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
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

/** The Privacy Policy body, shown in the in-app popup. Mirrors the web text. */
export const PrivacyContent = () => (
  <Box gap="spacing-16" paddingBottom="spacing-16">
    <Text variant="caption" color="subtext">
      Last updated: {EFFECTIVE_DATE}
    </Text>

    <P>
      Outception (“we”, “us”) operates the Outception news wall - a website and
      mobile app that aggregates headlines from public news sources and links
      you out to the original publishers. This policy explains what personal
      data we process, why, and the choices you have. It is written for
      compliance with the EU/UK General Data Protection Regulation (GDPR). We
      are based in Ireland; for privacy questions contact us at {CONTACT_EMAIL}.
    </P>

    <Section title="Data we collect">
      <P>We collect the following, depending on how you use Outception:</P>
      <Bullet>
        <B>Preferences</B>: the news sources you follow and your deck, theme,
        and language settings. These are stored on your device.
      </Bullet>
      <Bullet>
        <B>Device &amp; usage data</B>: IP address, device and app type, app
        version, and a randomly-generated identifier used to distinguish
        sessions. We derive an approximate country from your IP to set your
        language and show local weather.
      </Bullet>
      <Bullet>
        <B>Precise location</B>: only if you grant location permission, and only
        to fetch weather for your area. You can deny or revoke this at any time
        in your device settings.
      </Bullet>
      <Bullet>
        <B>Diagnostics</B>: crash reports and error logs to keep the service
        working.
      </Bullet>
      <P>
        Outception works without an account - we do not offer sign-in, ask for
        payment information, or knowingly collect data from children under 16.
      </P>
    </Section>

    <Section title="Advertising">
      <P>
        Outception does not serve advertising and does not use advertising
        networks, ad cookies, or device advertising identifiers.
      </P>
    </Section>

    <Section title="Analytics">
      <P>
        To understand how Outception is used and improve it, we use
        product-analytics and error-monitoring tools that may set identifiers
        and process usage and device data on our behalf: PostHog and Sentry.
      </P>
    </Section>

    <Section title="Why we process your data">
      <Bullet>
        <B>Consent</B> - for analytics and precise location.
      </Bullet>
      <Bullet>
        <B>Legitimate interests</B> - to keep the service secure, functional,
        and free.
      </Bullet>
    </Section>

    <Section title="Sharing your data">
      <P>
        We do not sell your personal data. We share it only with the service
        providers that make Outception work - our EU hosting provider, Google
        (analytics), PostHog, and Sentry - each acting under contract. When you
        tap a headline you leave Outception for the publisher’s own site, which
        has its own privacy practices we don’t control.
      </P>
    </Section>

    <Section title="Retention & your rights">
      <P>
        Because Outception works without an account, your preferences stay on
        your device - clear them any time in your app settings. Under the GDPR
        you can request access to, correction, or deletion of any personal data
        our providers process, object to or restrict processing, withdraw
        consent, and request a copy. Contact us at {CONTACT_EMAIL}. You may also
        complain to your local data-protection authority (in Ireland, the Data
        Protection Commission).
      </P>
    </Section>

    <Section title="Changes">
      <P>
        We may update this policy from time to time. We’ll revise the “last
        updated” date above and, for material changes, provide a more prominent
        notice.
      </P>
    </Section>

    <Section title="Contact">
      <P>Questions about this policy? Email {CONTACT_EMAIL}.</P>
    </Section>
  </Box>
)
