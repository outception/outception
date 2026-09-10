import { CardHand } from '@/components/News/CardHand'
import type { Metadata } from 'next'

// Its own route while this is being judged, so the landing wall people
// actually read is untouched. The cards here ARE real cards, so unlike the
// canvas this replaced there is nothing lost to a screen reader - `noindex`
// is only to keep two pages of the same headlines out of search.
export const metadata: Metadata = {
  title: 'Hand',
  robots: { index: false, follow: false },
}

export default function SpiralPage() {
  return (
    <main className="flex w-full flex-col items-center gap-4 px-4 py-6">
      <CardHand />
      <p className="text-xs text-neutral-500 dark:text-neutral-400">
        Pick a card to pull it out of the hand.
      </p>
    </main>
  )
}
