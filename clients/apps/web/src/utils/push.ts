/** The browser side of the morning push: one subscription per browser,
 * handed to the server with the profile it is for. Nothing here identifies
 * the reader beyond the push endpoint itself. */

export const pushSupported = (): boolean =>
  typeof window !== 'undefined' &&
  'serviceWorker' in navigator &&
  'PushManager' in window &&
  'Notification' in window

/** A VAPID public key, as served (URL-safe base64), in the shape the push
 * manager takes. */
export const applicationServerKey = (key: string): Uint8Array => {
  const padded = key + '='.repeat((4 - (key.length % 4)) % 4)
  const binary = atob(padded.replace(/-/g, '+').replace(/_/g, '/'))
  const out = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) out[i] = binary.charCodeAt(i)
  return out
}

export interface BrowserSubscription {
  endpoint: string
  keys: { p256dh: string; auth: string }
}

const toBody = (sub: PushSubscription): BrowserSubscription | null => {
  const json = sub.toJSON()
  const p256dh = json.keys?.p256dh
  const auth = json.keys?.auth
  if (!json.endpoint || !p256dh || !auth) return null
  return { endpoint: json.endpoint, keys: { p256dh, auth } }
}

/** The browser's current subscription, if it has one. */
export const currentSubscription =
  async (): Promise<BrowserSubscription | null> => {
    if (!pushSupported()) return null
    const registration = await navigator.serviceWorker.ready
    const sub = await registration.pushManager.getSubscription()
    return sub ? toBody(sub) : null
  }

/** Ask for permission and subscribe this browser. Null when the reader said
 * no or the browser cannot. */
export const subscribeBrowser = async (
  publicKey: string,
): Promise<BrowserSubscription | null> => {
  if (!pushSupported()) return null
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return null
  const registration = await navigator.serviceWorker.ready
  const existing = await registration.pushManager.getSubscription()
  const sub =
    existing ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: applicationServerKey(publicKey) as BufferSource,
    }))
  return toBody(sub)
}

/** Drop the browser's subscription once no profile wants it. */
export const unsubscribeBrowser = async (): Promise<void> => {
  if (!pushSupported()) return
  const registration = await navigator.serviceWorker.ready
  const sub = await registration.pushManager.getSubscription()
  if (sub) await sub.unsubscribe()
}
