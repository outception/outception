import LogoIcon from '@/components/Brand/logos/LogoIcon'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit'
import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Terms of Service',
  description: 'The terms that govern your use of Outception.',
}

const EFFECTIVE_DATE = '22 July 2026'
const CONTACT_EMAIL = 'hello@outception.com'

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
    <Text variant="heading-xs" as="h2">
      {title}
    </Text>
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

export default function TermsPage() {
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
                Terms of Service
              </Text>
              <Text variant="caption" color="disabled">
                Last updated: {EFFECTIVE_DATE}
              </Text>
            </Box>
          </Box>

          <P>
            These terms govern your use of Outception (“we”, “us”) — a website
            and mobile app that aggregates headlines from public news sources
            and links you out to the original publishers. By using Outception,
            you agree to these terms. If you do not agree, please do not use the
            service. We are based in Ireland.
          </P>

          <Section title="The service">
            <P>
              Outception is a live news wall. We collect and display headlines
              and links from third-party sources, organised by topic, and send
              you to the publisher’s own site or app to read the full story. We
              do not host, author, or claim ownership of that content. Reading
              the wall is free and requires no account. The service is supported
              by advertising.
            </P>
          </Section>

          <Section title="Accounts">
            <P>
              An account is optional. If you create one (including via sign-in
              with Google, Microsoft, or Apple), you are responsible for keeping
              your credentials secure and for activity under your account. You
              may stop using your account at any time.
            </P>
          </Section>

          <Section title="Acceptable use">
            <P>You agree not to:</P>
            <Box as="ul" flexDirection="column" rowGap="s">
              <Bullet>
                use the service in a way that breaks any law or infringes
                someone else’s rights;
              </Bullet>
              <Bullet>
                attempt to disrupt, overload, or gain unauthorised access to the
                service or its infrastructure;
              </Bullet>
              <Bullet>
                scrape, resell, or systematically copy the service or its
                aggregated content except through any API we expressly provide,
                subject to its terms;
              </Bullet>
              <Bullet>
                interfere with or attempt to circumvent advertising or security
                features.
              </Bullet>
            </Box>
          </Section>

          <Section title="Third-party content and links">
            <P>
              Headlines, article text, images, and trademarks shown on the wall
              belong to their respective publishers and rights holders. Links to
              third-party sites are provided for convenience; we are not
              responsible for the content, accuracy, or practices of those
              sites, and your use of them is governed by their own terms.
            </P>
          </Section>

          <Section title="Advertising">
            <P>
              Outception is free to read and supported by ads served through
              Google (AdMob on mobile, AdSense on the web). Ad content is
              controlled by the ad networks and their advertisers, not by us.
              How advertising data is handled is described in our{' '}
              <Link href="/privacy" style={{ textDecoration: 'underline' }}>
                Privacy Policy
              </Link>
              .
            </P>
          </Section>

          <Section title="Our intellectual property">
            <P>
              The Outception name, logo, design, and software are ours or our
              licensors’ and are protected by intellectual-property laws. These
              terms grant you a limited, personal, non-exclusive, revocable
              licence to use the service; they do not transfer any ownership.
              The application source is released separately under the Apache
              License 2.0 as stated in the project repository.
            </P>
          </Section>

          <Section title="Disclaimers">
            <P>
              The service is provided “as is” and “as available”, without
              warranties of any kind, whether express or implied, including
              fitness for a particular purpose and non-infringement. We do not
              warrant that headlines are complete, accurate, current, or
              available without interruption.
            </P>
          </Section>

          <Section title="Limitation of liability">
            <P>
              To the fullest extent permitted by law, Outception is not liable
              for any indirect, incidental, or consequential damages, or for
              loss of data, profits, or goodwill, arising from your use of or
              inability to use the service. Nothing in these terms limits
              liability that cannot be limited under applicable law.
            </P>
          </Section>

          <Section title="Changes">
            <P>
              We may update the service or these terms from time to time. When
              we make material changes, we will update the “last updated” date
              above. Continuing to use Outception after changes take effect
              means you accept the revised terms.
            </P>
          </Section>

          <Section title="Governing law">
            <P>
              These terms are governed by the laws of Ireland, and the courts of
              Ireland have jurisdiction over any dispute, without prejudice to
              any mandatory consumer-protection rights you have where you live.
            </P>
          </Section>

          <Section title="Contact">
            <P>Questions about these terms? Email us at {CONTACT_EMAIL}.</P>
          </Section>
        </Box>
      </div>
    </Box>
  )
}
