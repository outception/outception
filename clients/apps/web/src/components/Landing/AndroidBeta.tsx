'use client'

import { useT } from '@/providers/locale'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@outception-com/ui/components/ui/dialog'
import { useEffect, useState } from 'react'

const GROUP_URL = 'https://groups.google.com/g/outception-testers'
const OPT_IN_URL =
  'https://play.google.com/apps/testing/com.outception.Outception'
const STORE_URL =
  'https://play.google.com/store/apps/details?id=com.outception.Outception'

/** The closed-beta join steps - shared by the Play badge's dialog and the
 * Android visitor banner. Each step is a real link: the group first, the
 * tester opt-in second, the store last (which Play only serves to opted-in
 * accounts, hence the note). */
export const AndroidBetaSteps = () => {
  const t = useT()
  const steps: Array<[string, string]> = [
    [GROUP_URL, t('news.stores.betaStep1')],
    [OPT_IN_URL, t('news.stores.betaStep2')],
    [STORE_URL, t('news.stores.betaStep3')],
  ]
  return (
    <Box flexDirection="column" rowGap="m">
      <Text variant="heading-xs" as="h3">
        {t('news.stores.betaTitle')}
      </Text>
      <Text variant="caption" color="muted">
        {t('news.stores.betaBody')}
      </Text>
      <Box as="ol" flexDirection="column" rowGap="s">
        {steps.map(([href, label], i) => (
          <Box as="li" key={href} columnGap="s" alignItems="center">
            <span className="rank-numeral">{i + 1}</span>
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="headline-link underline underline-offset-2"
            >
              {label}
            </a>
          </Box>
        ))}
      </Box>
      <Text variant="caption" color="muted">
        {t('news.stores.betaStep3Note')} {t('news.stores.betaAsk')}
      </Text>
    </Box>
  )
}

const DISMISS_KEY = 'news:android-beta-banner:v1'

/** A slim strip shown to ANDROID visitors only, recruiting them into the
 * closed test - the one audience guaranteed to want the app, which is
 * exactly the engaged-tester pool Google's production review demands.
 * Dismissible for good; invisible everywhere else. */
export const AndroidBetaBanner = () => {
  const t = useT()
  const [show, setShow] = useState(false)
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (!/android/i.test(navigator.userAgent)) return
    try {
      if (localStorage.getItem(DISMISS_KEY)) return
    } catch {
      // Storage blocked: show it; worst case the dismissal doesn't stick.
    }
    // Deferred a tick (not set synchronously in the effect) so revealing the
    // banner doesn't cascade into the wall's first render.
    const id = setTimeout(() => setShow(true), 0)
    return () => clearTimeout(id)
  }, [])
  if (!show) return null
  const dismiss = () => {
    setShow(false)
    try {
      localStorage.setItem(DISMISS_KEY, '1')
    } catch {
      // Best effort.
    }
  }
  return (
    <>
      <Box
        flexDirection="row"
        alignItems="center"
        justifyContent="center"
        columnGap="s"
        paddingVertical="xs"
        paddingHorizontal="m"
      >
        <span className="meta-kicker">{t('news.androidBeta.banner')}</span>
        <button
          type="button"
          className="ghost-pill store-pill"
          onClick={() => setOpen(true)}
        >
          {t('news.androidBeta.cta')}
        </button>
        <button
          type="button"
          aria-label={t('news.androidBeta.dismiss')}
          onClick={dismiss}
          className="cursor-pointer opacity-50 hover:opacity-100"
        >
          ✕
        </button>
      </Box>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="paper-search w-full max-w-sm rounded-2xl border-0 p-8 text-black dark:text-white">
          <DialogTitle className="sr-only">
            {t('news.stores.betaTitle')}
          </DialogTitle>
          <AndroidBetaSteps />
        </DialogContent>
      </Dialog>
    </>
  )
}
