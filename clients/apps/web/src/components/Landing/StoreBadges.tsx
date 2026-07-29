'use client'

import { useT } from '@/providers/locale'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@outception-com/ui/components/ui/dialog'
import { useState } from 'react'
import { AndroidBetaSteps } from './AndroidBeta'

const APP_STORE_URL = 'https://apps.apple.com/app/id6793827093'

const AppleGlyph = () => (
  <svg
    viewBox="0 0 24 24"
    width={15}
    height={15}
    fill="currentColor"
    aria-hidden
  >
    <path d="M17.05 12.53c-.03-2.5 2.04-3.7 2.13-3.76-1.16-1.7-2.97-1.93-3.61-1.96-1.54-.16-3 .9-3.78.9-.78 0-1.98-.88-3.26-.86-1.68.03-3.22.97-4.08 2.47-1.74 3.01-.44 7.47 1.25 9.91.83 1.2 1.81 2.54 3.1 2.49 1.25-.05 1.72-.8 3.22-.8 1.5 0 1.93.8 3.25.78 1.34-.03 2.19-1.22 3.01-2.42.95-1.39 1.34-2.73 1.36-2.8-.03-.02-2.6-1-2.63-3.95zM14.56 4.9c.69-.83 1.15-1.99 1.02-3.15-.99.04-2.18.66-2.89 1.49-.63.73-1.19 1.91-1.04 3.04 1.1.09 2.23-.56 2.91-1.38z" />
  </svg>
)

const PlayGlyph = () => (
  <svg
    viewBox="0 0 24 24"
    width={14}
    height={14}
    fill="currentColor"
    aria-hidden
  >
    <path d="M4 3.6v16.8c0 .5.55.82.98.55l13.3-8.4a.65.65 0 0 0 0-1.1L4.98 3.05A.65.65 0 0 0 4 3.6zm12.1 6.06-2.68 1.68-8.3-8.3 10.98 6.62zm0 4.68L5.12 20.96l8.3-8.3 2.68 1.68z" />
  </svg>
)

/** Footer store badges: "Available now on" + App Store / Google Play.
 * Google Play opens a coming-soon card. The App Store badge redirects phones
 * straight to the listing (touch device - the reader can install right
 * there); desktops get a card with a QR code to scan instead. */
export const StoreBadges = () => {
  const t = useT()
  const [dialog, setDialog] = useState<'qr' | 'android' | null>(null)

  const onAppStore = () => {
    if (window.matchMedia('(pointer: coarse)').matches) {
      window.location.href = APP_STORE_URL
      return
    }
    setDialog('qr')
  }

  return (
    <Box
      alignItems="center"
      columnGap="s"
      flexWrap="wrap"
      justifyContent="center"
    >
      {/* Micro-kicker + compact pills: the strip must cost the card as
          little height as possible (it shares the sheet with headlines). */}
      <span className="meta-kicker">{t('news.stores.available')}</span>
      <button
        type="button"
        className="ghost-pill store-pill"
        onClick={onAppStore}
      >
        <AppleGlyph />
        {t('news.stores.appStore')}
      </button>
      <button
        type="button"
        className="ghost-pill store-pill"
        onClick={() => setDialog('android')}
      >
        <PlayGlyph />
        {t('news.stores.googlePlay')}
      </button>

      <Dialog
        open={dialog !== null}
        onOpenChange={(o) => !o && setDialog(null)}
      >
        <DialogContent className="paper-search w-full max-w-sm rounded-2xl border-0 p-8 text-black dark:text-white">
          <DialogTitle className="sr-only">
            {dialog === 'qr'
              ? t('news.stores.qrTitle')
              : t('news.stores.betaTitle')}
          </DialogTitle>
          {dialog === 'qr' ? (
            <Box flexDirection="column" alignItems="center" rowGap="l">
              <Text variant="heading-xs" as="h3">
                {t('news.stores.qrTitle')}
              </Text>
              {/* Plain div: the sheet must stay literally white in BOTH
                  themes for the code to scan - tokens would flip it dark. */}
              <div
                style={{
                  backgroundColor: '#fff',
                  borderRadius: 12,
                  padding: 12,
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src="/qr-appstore.svg"
                  alt={t('news.stores.qrTitle')}
                  width={208}
                  height={208}
                  style={{ display: 'block' }}
                />
              </div>
              <Text variant="caption" color="muted">
                {t('news.stores.qrHint')}
              </Text>
            </Box>
          ) : (
            /* Closed beta running: the tap that used to dead-end at "coming
               soon" now recruits the tapper straight into the test. */
            <AndroidBetaSteps />
          )}
        </DialogContent>
      </Dialog>
    </Box>
  )
}
