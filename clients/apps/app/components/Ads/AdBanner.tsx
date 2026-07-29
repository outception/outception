import {
  bannerAdUnitId,
  getAdsReadySnapshot,
  subscribeAdsReady,
} from '@/utils/ads'
import { useSyncExternalStore } from 'react'
import { BannerAd, BannerAdSize } from 'react-native-google-mobile-ads'

/**
 * Compact fixed-size banner (320×50), transparent around the creative — it
 * sits chrome-less in the foot of the deck so an unfilled or still-loading
 * slot is invisible. Ad-load failures render nothing (the SDK handles it),
 * so this never breaks layout.
 *
 * Held back until the Ads SDK has initialized: BannerAd fires its request on
 * mount and doesn't retry, so mounting early means a blank slot for the whole
 * first session.
 */
export const AdBanner = () => {
  const ready = useSyncExternalStore(
    subscribeAdsReady,
    getAdsReadySnapshot,
    getAdsReadySnapshot,
  )
  if (!ready) return null
  return <BannerAd unitId={bannerAdUnitId} size={BannerAdSize.BANNER} />
}
