'use client'

import { useT } from '@/providers/translate'
import { getWallLookSnapshot, getWallThemeSnapshot } from '@/utils/wallTheme'
import { buildShareLink, PLAIN_LOOK_ID } from '@outception-com/news-core'
import { Check, Share2 } from 'lucide-react'
import { useState } from 'react'
import { useNewsColumn } from './NewsColumnContext'

/** Share a card. The link opens the wall on this exact card (`?card=<id>`,
 * which keeps the rich unfurl) and carries what the sharer saw in the hash:
 * the deck, the edition and the look, and the moment it was copied.
 *
 * Uses the Web Share API (the OS share sheet lists every installed app -
 * WhatsApp, X, Telegram, Messenger, email, …) and falls back to copying the
 * link where that API isn't available (most desktop browsers).
 *
 * Plain button to match FollowButton's hairline ghost-capsule (AGENTS.md
 * tailwind escape hatch - not expressible with Orbit Button variants). */
export const shareLinkFor = (
  cardId: string,
  deck: readonly string[],
  now: number = Date.now(),
): string => {
  const look = getWallLookSnapshot().id
  return buildShareLink({
    lead: cardId,
    cards: deck.length > 1 ? deck : [],
    edition: getWallThemeSnapshot().id,
    look: look === PLAIN_LOOK_ID ? null : look,
    at: Math.floor(now / 1000),
  })
}

export const ShareButton = ({
  cardId,
  name,
}: {
  cardId: string
  name: string
}) => {
  const t = useT()
  const { deck } = useNewsColumn()
  const [copied, setCopied] = useState(false)

  const onShare = async () => {
    const url = `${window.location.origin}${shareLinkFor(cardId, deck)}`
    const text = t('news.share.text', { source: name })

    if (navigator.share) {
      try {
        await navigator.share({ title: name, text, url })
        return
      } catch {
        // user dismissed the share sheet, or it failed - fall through to copy
      }
    }
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      // clipboard blocked - nothing more we can do without a URL surface
    }
  }

  return (
    <button
      type="button"
      className="ghost-pill"
      onClick={onShare}
      aria-label={copied ? t('news.share.copied') : t('news.share.label')}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
    >
      {copied ? (
        <>
          <Check size={14} aria-hidden />
          {t('news.share.copied')}
        </>
      ) : (
        <>
          <Share2 size={14} aria-hidden />
          {t('news.share.label')}
        </>
      )}
    </button>
  )
}
