import * as WebBrowser from 'expo-web-browser'

const WEB_URL =
  process.env.EXPO_PUBLIC_OUTCEPTION_WEB_URL ?? 'http://127.0.0.1:3000'

// Promotions are a paid digital service. App Store / Play Store policy forbids
// charging for that in-app outside their billing systems, so the purchase
// happens on the web: tapping "Promote" hands the user off to the web promote
// flow in their browser rather than composing and paying natively.
export const PROMOTE_WEB_URL = `${WEB_URL}/promote`

export const openPromoteOnWeb = (): Promise<WebBrowser.WebBrowserResult> =>
  WebBrowser.openBrowserAsync(PROMOTE_WEB_URL)
