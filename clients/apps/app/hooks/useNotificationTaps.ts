import { notificationUrl } from '@/utils/push'
import * as Notifications from 'expo-notifications'
import { useRouter } from 'expo-router'
import { useEffect } from 'react'

/** A tapped morning push opens the briefing it carried, whether the app
 * was running or the tap launched it. */
export const useNotificationTaps = () => {
  const router = useRouter()
  useEffect(() => {
    const open = (response: Notifications.NotificationResponse | null) => {
      const url = response ? notificationUrl(response) : null
      if (url) router.push(url as never)
    }
    void Notifications.getLastNotificationResponseAsync().then(open)
    const sub = Notifications.addNotificationResponseReceivedListener(open)
    return () => sub.remove()
  }, [router])
}
