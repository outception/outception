'use client'

import { useT } from '@/providers/locale'
import { X } from 'lucide-react'
import { useNewsColumn } from './NewsColumnContext'

/** The one action a card offers: Unfollow. Clicking removes the source from
 * the wall on every tab (and un-stars it) until it's re-followed from the
 * "More" palette — the palette is where sources are added.
 *
 * Rendered only on "Your deck" (see NewsSourceCard): Trending browses the
 * whole roster and its cards carry no curation action, so hiding a source
 * from Trending means following-then-unfollowing or just not following it.
 * Where it renders, it's always visible on every input device.
 *
 * Plain button: the hairline ghost-capsule look isn't expressible with
 * Orbit Button's variants — AGENTS.md escape hatch. */
export const FollowButton = ({ sourceId }: { sourceId: string }) => {
  const { hideSource } = useNewsColumn()
  const t = useT()

  return (
    <button
      type="button"
      className="ghost-pill"
      onClick={() => hideSource(sourceId)}
      aria-label={t('news.follow.unfollow')}
      title={t('news.follow.unfollow')}
      style={{ padding: 7 }}
    >
      <X size={15} aria-hidden />
    </button>
  )
}
