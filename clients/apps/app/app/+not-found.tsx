import { Redirect } from 'expo-router'

/**
 * Send unknown routes to the wall rather than expo-router's `Unmatched` debug
 * screen. The Android intent filter claims an applink path that has no route,
 * so without this a verified deep link opened the app on a "this screen does
 * not exist" page.
 */
export default function NotFound() {
  return <Redirect href="/" />
}
