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

/** The Terms of Service body, shown in the in-app popup. Mirrors the web text. */
export const TermsContent = () => (
  <Box gap="spacing-16" paddingBottom="spacing-16">
    <Text variant="caption" color="subtext">
      Last updated: {EFFECTIVE_DATE}
    </Text>

    <P>
      These terms govern your use of Outception (“we”, “us”) — a website and
      mobile app that aggregates headlines from public news sources and links
      you out to the original publishers. By using Outception, you agree to
      these terms. If you do not agree, please do not use the service. We are
      based in Ireland.
    </P>

    <Section title="The service">
      <P>
        Outception is a live news wall. We collect and display headlines and
        links from third-party sources, organised by topic, and send you to the
        publisher’s own site or app to read the full story. We do not host,
        author, or claim ownership of that content. Reading the wall is free and
        requires no account.
      </P>
    </Section>

    <Section title="Acceptable use">
      <P>You agree not to:</P>
      <Bullet>
        use the service in a way that breaks any law or infringes someone else’s
        rights;
      </Bullet>
      <Bullet>
        attempt to disrupt, overload, or gain unauthorised access to the service
        or its infrastructure;
      </Bullet>
      <Bullet>
        scrape, resell, or systematically copy the service or its aggregated
        content except through an API we expressly provide, subject to its
        terms;
      </Bullet>
      <Bullet>
        interfere with or attempt to circumvent security features.
      </Bullet>
    </Section>

    <Section title="Third-party content and links">
      <P>
        Headlines, article text, images, and trademarks shown on the wall belong
        to their respective publishers and rights holders. Links to third-party
        sites are provided for convenience; we are not responsible for the
        content, accuracy, or practices of those sites, and your use of them is
        governed by their own terms.
      </P>
    </Section>

    <Section title="Our intellectual property">
      <P>
        The Outception name, logo, design, and software are ours or our
        licensors’ and are protected by intellectual-property laws. These terms
        grant you a limited, personal, non-exclusive, revocable licence to use
        the service; they do not transfer any ownership. The application source
        is released separately under the Apache License 2.0 as stated in the
        project repository.
      </P>
    </Section>

    <Section title="Disclaimers">
      <P>
        The service is provided “as is” and “as available”, without warranties
        of any kind, whether express or implied, including fitness for a
        particular purpose and non-infringement. We do not warrant that
        headlines are complete, accurate, current, or available without
        interruption.
      </P>
    </Section>

    <Section title="Limitation of liability">
      <P>
        To the fullest extent permitted by law, Outception is not liable for any
        indirect, incidental, or consequential damages, or for loss of data,
        profits, or goodwill, arising from your use of or inability to use the
        service. Nothing in these terms limits liability that cannot be limited
        under applicable law.
      </P>
    </Section>

    <Section title="Changes">
      <P>
        We may update the service or these terms from time to time. When we make
        material changes, we will update the “last updated” date above.
        Continuing to use Outception after changes take effect means you accept
        the revised terms.
      </P>
    </Section>

    <Section title="Governing law">
      <P>
        These terms are governed by the laws of Ireland, and the courts of
        Ireland have jurisdiction over any dispute, without prejudice to any
        mandatory consumer-protection rights you have where you live.
      </P>
    </Section>

    <Section title="Contact">
      <P>Questions about these terms? Email us at {CONTACT_EMAIL}.</P>
    </Section>
  </Box>
)
