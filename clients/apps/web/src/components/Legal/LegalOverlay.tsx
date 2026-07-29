'use client'

import { Box } from '@outception-com/orbit/Box'
import { useRouter } from 'next/navigation'
import { useEffect, type ReactNode } from 'react'

/** Wraps a legal page (Privacy / Terms) so it dismisses like the wall's dialogs:
 * clicking the backdrop outside the card - or pressing Escape - returns to the
 * wall, rather than the logo being the only way out. Clicks inside the card are
 * stopped so they don't close it. */
export const LegalOverlay = ({ children }: { children: ReactNode }) => {
  const router = useRouter()

  useEffect(() => {
    const close = () =>
      window.history.length > 1 ? router.back() : router.push('/')
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [router])

  const close = () =>
    window.history.length > 1 ? router.back() : router.push('/')

  return (
    <Box
      as="main"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      paddingHorizontal="l"
      paddingVertical="3xl"
      onClick={close}
    >
      <div
        className="paper-panel w-full max-w-[760px] rounded-2xl p-6 md:p-12"
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </div>
    </Box>
  )
}
