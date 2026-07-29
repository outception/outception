import { requestTrackingPermissionsAsync } from 'expo-tracking-transparency'
import { AppState, Platform } from 'react-native'
import mobileAds, { AdsConsent, TestIds } from 'react-native-google-mobile-ads'

// Ad unit ids: Google's official TEST ids in dev (work with no AdMob account),
// real ids from EXPO_PUBLIC_ADMOB_* env vars in production. Ad unit ids are
// public identifiers, safe to ship in the client.
export const bannerAdUnitId = __DEV__
  ? TestIds.BANNER
  : Platform.select({
      ios: process.env.EXPO_PUBLIC_ADMOB_BANNER_IOS,
      android: process.env.EXPO_PUBLIC_ADMOB_BANNER_ANDROID,
    }) || TestIds.BANNER

let started = false

// The banner mounts as soon as the deck renders, which is well before this
// module has finished the consent → ATT → initialize() chain. A BannerAd that
// loads before the SDK is up fails and never retries, so the first session —
// the most valuable one — shows an empty slot. Publish readiness instead.
let adsReady = false
const readyListeners = new Set<() => void>()

export const subscribeAdsReady = (listener: () => void): (() => void) => {
  readyListeners.add(listener)
  return () => {
    readyListeners.delete(listener)
  }
}

export const getAdsReadySnapshot = (): boolean => adsReady

/** Resolve once the app is foreground-active (immediately if it already is). */
const whenActive = (): Promise<void> =>
  AppState.currentState === 'active'
    ? Promise.resolve()
    : new Promise((resolve) => {
        const sub = AppState.addEventListener('change', (state) => {
          if (state === 'active') {
            sub.remove()
            resolve()
          }
        })
      })

/**
 * Gather EEA/UK consent (Google UMP), request iOS App Tracking Transparency,
 * then start the Mobile Ads SDK. Every step is guarded so a consent/ATT/SDK
 * failure can never crash the app — worst case we serve non-personalized ads
 * or none. Call once at app start.
 */
export async function initializeAds(): Promise<void> {
  if (started) return
  started = true
  try {
    // Same foreground requirement as ATT below: a consent form presented with
    // no resumed activity / view controller silently fails, and we'd then
    // initialize the SDK and serve ads to an EEA reader with no consent on
    // record. Wait for `active` before asking for anything.
    await whenActive()
    await AdsConsent.requestInfoUpdate()
    await AdsConsent.loadAndShowConsentFormIfRequired()
  } catch {
    // Consent flow failed → the SDK serves non-personalized ads.
  }
  if (Platform.OS === 'ios') {
    try {
      // iOS silently returns `denied` — without ever showing the prompt — if
      // the app isn't foreground-active. This runs from a root effect that
      // fires behind the splash, so wait for `active` first. App Review checks
      // that the prompt actually appears.
      await whenActive()
      await requestTrackingPermissionsAsync()
    } catch {
      // ATT denied/unavailable → non-personalized ads.
    }
  }
  try {
    await mobileAds().initialize()
    adsReady = true
    for (const listener of readyListeners) listener()
  } catch {
    started = false
  }
}

/**
 * Show the UMP privacy options form so a reader can change or withdraw ad
 * consent. Google requires a persistent entry point wherever
 * `privacyOptionsRequirementStatus` is `required` (EEA/UK).
 */
export async function showAdPrivacyOptions(): Promise<void> {
  try {
    await AdsConsent.showPrivacyOptionsForm()
  } catch {
    // Form unavailable — nothing to change.
  }
}

/** Whether this reader is in a region that requires the privacy-options entry. */
export async function adPrivacyOptionsRequired(): Promise<boolean> {
  try {
    const info = await AdsConsent.getConsentInfo()
    return info.privacyOptionsRequirementStatus === 'REQUIRED'
  } catch {
    return false
  }
}
