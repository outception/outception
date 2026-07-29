import { LegalOverlay } from '@/components/Legal/LegalOverlay'
import { TermsContent } from '@/components/Legal/TermsContent'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Terms of Service',
  description: 'The terms that govern your use of Outception.',
}

export default function TermsPage() {
  return (
    <LegalOverlay>
      <TermsContent />
    </LegalOverlay>
  )
}
