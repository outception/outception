import { requestTrackingPermissionsAsync } from 'expo-tracking-transparency'
import { Platform } from 'react-native'
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
    await AdsConsent.requestInfoUpdate()
    await AdsConsent.loadAndShowConsentFormIfRequired()
  } catch {
    // Consent flow failed → the SDK serves non-personalized ads.
  }
  if (Platform.OS === 'ios') {
    try {
      await requestTrackingPermissionsAsync()
    } catch {
      // ATT denied/unavailable → non-personalized ads.
    }
  }
  try {
    await mobileAds().initialize()
  } catch {
    started = false
  }
}
