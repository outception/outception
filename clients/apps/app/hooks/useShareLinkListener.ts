import { applyShareAddress } from '@/utils/shareLinks'
import * as Linking from 'expo-linking'
import { useRouter } from 'expo-router'
import { useEffect, useRef } from 'react'

/**
 * The root-level link listener: the router never exposes an address's
 * fragment, so share links are read here from the raw address, the shared
 * parser applies theme, cards and story, and the lead card is opened on the
 * wall. Runs for the launch address and for every address while open.
 */
export const useShareLinkListener = (): void => {
  const router = useRouter()
  const handled = useRef<string | null>(null)
  useEffect(() => {
    const open = (url: string | null) => {
      if (!url || handled.current === url) return
      handled.current = url
      const lead = applyShareAddress(url)
      if (lead) router.replace({ pathname: '/', params: { card: lead } })
    }
    void Linking.getInitialURL()
      .then(open)
      .catch(() => {})
    const subscription = Linking.addEventListener('url', (event) =>
      open(event.url),
    )
    return () => subscription.remove()
  }, [router])
}
