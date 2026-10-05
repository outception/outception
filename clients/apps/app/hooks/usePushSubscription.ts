import { useOutceptionClient } from '@/providers/OutceptionClientProvider'
import { newsApi } from '@/utils/news'
import { pushProfiles } from '@/utils/prefs'
import { devicePushToken } from '@/utils/push'
import { useCallback, useState, useSyncExternalStore } from 'react'

/** The morning push switch for one profile: asks the device once, hands
 * the token to the server, and remembers the choice per profile. */
export const usePushSubscription = (profile: string) => {
  const { outception } = useOutceptionClient()
  const chosen = useSyncExternalStore(
    pushProfiles.subscribe,
    pushProfiles.get,
    pushProfiles.get,
  ).includes(profile)
  const [busy, setBusy] = useState(false)
  const toggle = useCallback(async () => {
    setBusy(true)
    try {
      const token = await devicePushToken()
      if (!token) return
      if (chosen) {
        await newsApi(outception).unsubscribePush(profile, token)
        pushProfiles.remove(profile)
      } else {
        await newsApi(outception).subscribePush(profile, token)
        pushProfiles.add(profile)
      }
    } catch {
      // The server or the push service said no; the switch stays as it was.
    } finally {
      setBusy(false)
    }
  }, [chosen, outception, profile])
  return { chosen, busy, toggle }
}
