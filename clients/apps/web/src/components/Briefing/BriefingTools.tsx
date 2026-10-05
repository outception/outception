'use client'

import { pushStore, usePushProfiles } from '@/components/News/readerStores'
import { newsApi } from '@/utils/news'
import {
  currentSubscription,
  pushSupported,
  subscribeBrowser,
  unsubscribeBrowser,
} from '@/utils/push'
import {
  canSpeak,
  getSpeakingServerSnapshot,
  getSpeakingSnapshot,
  speakLines,
  stopSpeaking,
  subscribeSpeaking,
} from '@/utils/speech'
import { useT } from '@/providers/translate'
import { Box } from '@outception-com/orbit/Box'
import { useEffect, useState, useSyncExternalStore } from 'react'

const never = () => () => {}
const no = () => false

/** The morning push switch for one profile: asks the browser once, hands
 * the subscription to the server, and remembers the choice per profile.
 * Hidden until the server has keys or when the browser cannot push. */
export const NotifyButton = ({
  profile,
  publicKey,
}: {
  profile: string
  publicKey: string | null | undefined
}) => {
  const t = useT()
  const chosen = usePushProfiles().includes(profile)
  const [busy, setBusy] = useState(false)
  // Browser support is a fact about the client, read after hydration.
  const supported = useSyncExternalStore(never, pushSupported, no)
  if (!publicKey || !supported) return null
  const toggle = async () => {
    setBusy(true)
    try {
      if (chosen) {
        const sub = await currentSubscription()
        if (sub) await newsApi.unsubscribePush(profile, sub.endpoint)
        pushStore.remove(profile)
        if (pushStore.get().length === 0) await unsubscribeBrowser()
      } else {
        const sub = await subscribeBrowser(publicKey)
        if (!sub) return
        await newsApi.subscribePush(profile, { kind: 'web', ...sub })
        pushStore.add(profile)
      }
    } catch {
      // The server or the push service said no; the switch stays as it was.
    } finally {
      setBusy(false)
    }
  }
  return (
    <button
      type="button"
      className="ghost-pill"
      aria-pressed={chosen}
      data-active={chosen}
      disabled={busy}
      onClick={() => void toggle()}
    >
      {chosen ? t('news.briefing.notifyOn') : t('news.briefing.notify')}
    </button>
  )
}

/** Reads the whole briefing aloud, section by section, through the
 * browser's own voice. Unmounting stops it. */
export const ListenButton = ({ lines }: { lines: readonly string[] }) => {
  const t = useT()
  const speaking = useSyncExternalStore(
    subscribeSpeaking,
    getSpeakingSnapshot,
    getSpeakingServerSnapshot,
  )
  const supported = useSyncExternalStore(never, canSpeak, no)
  useEffect(() => () => stopSpeaking(), [])
  if (!supported || lines.length === 0) return null
  return (
    <button
      type="button"
      className="ghost-pill"
      aria-pressed={speaking}
      data-active={speaking}
      onClick={() => (speaking ? stopSpeaking() : speakLines(lines))}
    >
      {speaking ? t('news.briefing.stopListening') : t('news.briefing.listen')}
    </button>
  )
}

/** The row of tools above a briefing. */
export const BriefingTools = ({ children }: { children: React.ReactNode }) => (
  <Box as="nav" flexDirection="row" flexWrap="wrap" columnGap="s" rowGap="s">
    {children}
  </Box>
)
