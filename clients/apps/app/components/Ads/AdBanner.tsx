import { bannerAdUnitId } from '@/utils/ads'
import { BannerAd, BannerAdSize } from 'react-native-google-mobile-ads'

/**
 * Anchored adaptive banner. Shows Google test ads in dev builds and real
 * inventory in production once the ADMOB unit ids are configured. Ad-load
 * failures render nothing (the SDK handles it), so this never breaks layout.
 */
export const AdBanner = () => (
  <BannerAd
    unitId={bannerAdUnitId}
    size={BannerAdSize.ANCHORED_ADAPTIVE_BANNER}
  />
)
