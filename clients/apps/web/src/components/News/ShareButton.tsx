'use client'

import { useLocale, useT } from '@/providers/locale'
import type { NewsSourceMeta } from '@/utils/news'
import { Check, Share2 } from 'lucide-react'
import { useState } from 'react'

/** Share a single card. Builds a link that opens the wall on this exact source
 * in the sharer's language (`?card=<id>&lang=<locale>`), so the recipient sees
 * the card exactly as it was shared — with a rich preview (see the landing
 * page's per-card OpenGraph image).
 *
 * Uses the Web Share API (the OS share sheet lists every installed app —
 * WhatsApp, X, Telegram, Messenger, email, …) and falls back to copying the
 * link where that API isn't available (most desktop browsers).
 *
 * Plain button to match FollowButton's hairline ghost-capsule (AGENTS.md
 * tailwind escape hatch — not expressible with Orbit Button variants). */
export const ShareButton = ({ source }: { source: NewsSourceMeta }) => {
  const locale = useLocale()
  const t = useT()
  const [copied, setCopied] = useState(false)

  const onShare = async () => {
    const url = `${window.location.origin}/?card=${encodeURIComponent(
      source.id,
    )}&lang=${encodeURIComponent(locale)}`
    const text = t('news.share.text', { source: source.name })

    if (navigator.share) {
      try {
        await navigator.share({ title: source.name, text, url })
        return
      } catch {
        // user dismissed the share sheet, or it failed — fall through to copy
      }
    }
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      // clipboard blocked — nothing more we can do without a URL surface
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
