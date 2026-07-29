import AsyncStorage from '@react-native-async-storage/async-storage'
import * as Updates from 'expo-updates'
import { Platform } from 'react-native'

/** Store-update discovery for the banner (UpdateBanner): readers on an old
 * binary don't auto-update, so the wall tells them a newer version exists.
 * The store itself is the version source — Apple's lookup API reports what is
 * actually live, so nothing needs bumping at release time and the banner
 * appears on old installs the moment a release goes live. The installed side
 * is `Updates.runtimeVersion` (the NATIVE binary version): the JS bundle's
 * own version lies after an OTA update. */

const LOOKUP_URL =
  'https://itunes.apple.com/lookup?bundleId=com.outception.Outception'
const STORE_URL = 'https://apps.apple.com/app/id6793827093'
const CACHE_KEY = 'news:store-version:v1'
const DISMISS_KEY = 'news:store-version-dismissed:v1'
// Short: a long cache pins "you're current" across a release, so phones that
// checked just before a version went live wouldn't hear about it until the
// next day. One tiny lookup per hour at most.
const CACHE_MS = 60 * 60 * 1000
const LOOKUP_TIMEOUT_MS = 6000

export type StoreUpdate = { version: string; url: string }

/** True when `latest` is a strictly newer dotted version than `installed`. */
export const isNewerVersion = (latest: string, installed: string): boolean => {
  const a = latest.split('.').map((n) => parseInt(n, 10))
  const b = installed.split('.').map((n) => parseInt(n, 10))
  if (a.some(Number.isNaN) || b.some(Number.isNaN)) return false
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const x = a[i] ?? 0
    const y = b[i] ?? 0
    if (x !== y) return x > y
  }
  return false
}

const storeVersion = async (): Promise<string | null> => {
  try {
    const cached = await AsyncStorage.getItem(CACHE_KEY)
    if (cached) {
      const { version, at } = JSON.parse(cached) as {
        version: string
        at: number
      }
      if (Date.now() - at < CACHE_MS) return version
    }
  } catch {
    // Malformed cache entry: fall through to a fresh lookup.
  }
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), LOOKUP_TIMEOUT_MS)
  try {
    const response = await fetch(LOOKUP_URL, { signal: controller.signal })
    const data = (await response.json()) as {
      results?: { version?: string }[]
    }
    const version = data.results?.[0]?.version
    if (!version) return null
    await AsyncStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ version, at: Date.now() }),
    )
    return version
  } catch {
    return null
  } finally {
    clearTimeout(timer)
  }
}

/** The update the banner should offer, or null (up to date, dismissed,
 * Android — no Play listing yet — or dev client without a runtime). */
export const checkForStoreUpdate = async (): Promise<StoreUpdate | null> => {
  if (Platform.OS !== 'ios') return null
  const installed = Updates.runtimeVersion
  if (!installed) return null
  const latest = await storeVersion()
  if (!latest || !isNewerVersion(latest, installed)) return null
  if ((await AsyncStorage.getItem(DISMISS_KEY)) === latest) return null
  return { version: latest, url: STORE_URL }
}

/** Hide the banner for this store version; it returns for the next release. */
export const dismissStoreUpdate = (version: string): void => {
  void AsyncStorage.setItem(DISMISS_KEY, version)
}
