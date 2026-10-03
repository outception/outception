import { Img, Section } from 'react-email'

const Header = () => (
  <Section>
    <div className="relative h-[48px]">
      <Img
        alt="Outception Logo"
        height="48"
        src="https://outception-public-assets.s3.us-east-2.amazonaws.com/emails/outception-logo-black-badge.png"
      />
    </div>
  </Section>
)

export default Header
