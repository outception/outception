import LogoIcon from '@/components/Brand/logos/LogoIcon'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit'
import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description: 'How Outception collects, uses, and protects your data.',
}

const EFFECTIVE_DATE = '22 July 2026'
const CONTACT_EMAIL = 'hello@outception.com'

const H2 = ({ children }: { children: React.ReactNode }) => (
  <Text variant="heading-xs" as="h2">
    {children}
  </Text>
)

const P = ({ children }: { children: React.ReactNode }) => (
  <Text variant="body" as="p" color="muted">
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

export default function PrivacyPage() {
  return (
    <Box
      as="main"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      paddingHorizontal="l"
      paddingVertical="3xl"
    >
      <div className="paper-panel w-full max-w-[760px] rounded-2xl p-6 md:p-12">
        <Box flexDirection="column" rowGap="2xl">
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
                Privacy Policy
              </Text>
              <Text variant="caption" color="disabled">
                Last updated: {EFFECTIVE_DATE}
              </Text>
            </Box>
          </Box>

          <P>
            Outception (“we”, “us”) operates the Outception news wall — a
            website and mobile app that aggregates headlines from public news
            sources and links you out to the original publishers. This policy
            explains what personal data we process, why, and the choices you
            have. It is written for compliance with the EU/UK General Data
            Protection Regulation (GDPR). We are based in Ireland; for privacy
            questions contact us at {CONTACT_EMAIL}.
          </P>

          <Section title="Data we collect">
            <P>
              We collect the following, depending on how you use Outception:
            </P>
            <Box as="ul" flexDirection="column" rowGap="s">
              <Bullet>
                <strong>Account data</strong> (only if you sign in): your email
                address, and — if you use “Sign in with Google/Microsoft/Apple”
                — the name, email, and avatar those providers share, plus the
                authentication tokens needed to keep you signed in.
              </Bullet>
              <Bullet>
                <strong>Preferences</strong>: the news sources you follow and
                your deck, theme, and language settings. These are stored on
                your device and, if you are signed in, associated with your
                account.
              </Bullet>
              <Bullet>
                <strong>Device &amp; usage data</strong>: IP address, device and
                browser type, app version, and a randomly-generated identifier
                used to distinguish sessions. We derive an approximate country
                from your IP to set your language and show local weather.
              </Bullet>
              <Bullet>
                <strong>Precise location</strong>: only if you grant location
                permission, and only to fetch weather for your area. You can
                deny or revoke this at any time in your device settings.
              </Bullet>
              <Bullet>
                <strong>Diagnostics</strong>: crash reports and error logs to
                keep the service working.
              </Bullet>
            </Box>
            <P>
              We do not ask for payment information, and we do not knowingly
              collect data from children under 16.
            </P>
          </Section>

          <Section title="Advertising">
            <P>
              Outception is free and supported by ads. We use{' '}
              <strong>Google AdMob</strong> in our mobile apps and{' '}
              <strong>Google AdSense</strong> on the website. These Google
              services may use cookies and device advertising identifiers to
              serve and measure ads, including personalized ads where you have
              consented.
            </P>
            <Box as="ul" flexDirection="column" rowGap="s">
              <Bullet>
                In the EU/UK, we show a consent prompt (Google’s Consent
                Management Platform / User Messaging Platform) before
                personalized ads are served. If you decline, you still see ads,
                but non-personalized ones.
              </Bullet>
              <Bullet>
                On iOS, we show Apple’s App Tracking Transparency prompt;
                tracking for personalized ads only occurs if you allow it.
              </Bullet>
              <Bullet>
                You can learn about and control Google’s use of advertising data
                at google.com/settings/ads and how Google uses data at
                google.com/policies/privacy/partners.
              </Bullet>
            </Box>
          </Section>

          <Section title="Analytics">
            <P>
              To understand how Outception is used and improve it, we use
              product-analytics and error-monitoring tools, which may set
              cookies or identifiers and process usage and device data on our
              behalf: PostHog (product analytics), Google Analytics (website),
              and Sentry (error monitoring).
            </P>
          </Section>

          <Section title="Cookies &amp; similar technologies">
            <P>
              We use a small number of cookies and local storage entries: a
              session cookie to keep you signed in, a non-identifying analytics
              identifier, and an approximate-country value for localization. Our
              advertising and analytics partners set their own cookies as
              described above. You can clear cookies and local storage in your
              browser at any time.
            </P>
          </Section>

          <Section title="Why we process your data (legal bases)">
            <Box as="ul" flexDirection="column" rowGap="s">
              <Bullet>
                <strong>Consent</strong> — for personalized advertising,
                analytics, and precise location.
              </Bullet>
              <Bullet>
                <strong>Contract</strong> — to provide your account and keep you
                signed in.
              </Bullet>
              <Bullet>
                <strong>Legitimate interests</strong> — to keep the service
                secure, functional, and free (including non-personalized ads).
              </Bullet>
            </Box>
          </Section>

          <Section title="Sharing your data">
            <P>
              We do not sell your personal data. We share it only with the
              service providers that make Outception work — our hosting provider
              (located in the EU), Google (advertising and analytics), PostHog,
              and Sentry — each acting under contract. When you tap a headline
              you leave Outception for the publisher’s own site, which has its
              own privacy practices we don’t control.
            </P>
          </Section>

          <Section title="International transfers">
            <P>
              Some providers (such as Google) may process data outside the
              EU/UK. Where they do, transfers are covered by appropriate
              safeguards such as the EU Standard Contractual Clauses.
            </P>
          </Section>

          <Section title="Retention">
            <P>
              We keep account data for as long as you have an account, and
              delete it when you delete your account. Diagnostic and analytics
              data are retained for a limited period. Advertising and analytics
              partners retain data according to their own policies.
            </P>
          </Section>

          <Section title="Your rights">
            <P>
              Under the GDPR you can request access to, correction, or deletion
              of your personal data, object to or restrict certain processing,
              withdraw consent, and request a copy of your data. You can delete
              your account (and its data) from the app’s account settings, or
              contact us at {CONTACT_EMAIL}. You also have the right to complain
              to your local data-protection authority (in Ireland, the Data
              Protection Commission).
            </P>
          </Section>

          <Section title="Changes to this policy">
            <P>
              We may update this policy from time to time. We’ll revise the
              “last updated” date above and, for material changes, provide a
              more prominent notice.
            </P>
          </Section>

          <Section title="Contact">
            <P>Questions about this policy? Email {CONTACT_EMAIL}.</P>
          </Section>
        </Box>
      </div>
    </Box>
  )
}
