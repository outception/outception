/** The app side of the morning push: the device's push token, handed to
 * the server with the profile it is for. The token is the only identity. */

import Constants from 'expo-constants'
import * as Notifications from 'expo-notifications'
import { Platform } from 'react-native'

/** Show a push as a banner even while the app is open. */
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
})

const projectId = (): string | undefined =>
  (Constants.expoConfig?.extra as { eas?: { projectId?: string } } | undefined)
    ?.eas?.projectId

/** Ask for permission and read the device token. Null when the reader said
 * no or the device cannot. */
export const devicePushToken = async (): Promise<string | null> => {
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('briefing', {
      name: 'Morning briefing',
      importance: Notifications.AndroidImportance.DEFAULT,
    })
  }
  const current = await Notifications.getPermissionsAsync()
  const granted = current.granted
    ? true
    : (await Notifications.requestPermissionsAsync()).granted
  if (!granted) return null
  try {
    const id = projectId()
    const token = await Notifications.getExpoPushTokenAsync(
      id ? { projectId: id } : undefined,
    )
    return token.data
  } catch {
    return null
  }
}

/** The page a tapped notification asked for, from its payload. */
export const notificationUrl = (
  response: Notifications.NotificationResponse,
): string | null => {
  const data = response.notification.request.content.data as
    | { url?: unknown }
    | undefined
  return typeof data?.url === 'string' && data.url.startsWith('/')
    ? data.url
    : null
}
