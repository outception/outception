import { LegalOverlay } from '@/components/Legal/LegalOverlay'
import { PrivacyContent } from '@/components/Legal/PrivacyContent'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description: 'How Outception collects, uses, and protects your data.',
}

export default function PrivacyPage() {
  return (
    <LegalOverlay>
      <PrivacyContent />
    </LegalOverlay>
  )
}
