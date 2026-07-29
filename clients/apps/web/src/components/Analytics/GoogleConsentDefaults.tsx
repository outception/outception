import { EU_COUNTRY_CODES } from '@/components/Privacy/countries'

const CONSENT_REGIONS = JSON.stringify(Array.from(new Set(EU_COUNTRY_CODES)))

/**
 * Google Consent Mode v2 defaults. Must render BEFORE any Google tag (gtag.js,
 * AdSense) so the tags boot in the right consent state: everything denied in
 * the regions where the cookie banner is shown (Google applies the `region`
 * list via its own geo detection, matching the banner's server-side gating),
 * granted everywhere else. A "yes" stored by a previous visit (same
 * `cookie_consent` localStorage key the banner writes) is replayed
 * synchronously so returning readers keep full measurement without waiting for
 * React to mount; live accept/decline updates are sent by
 * ConsentedGoogleAnalytics. `wait_for_update` holds the tag's first hits
 * briefly so that replay wins the race.
 */
export function GoogleConsentDefaults() {
  const script = `(function(){window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('consent','default',{ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied',analytics_storage:'denied',wait_for_update:500,region:${CONSENT_REGIONS}});gtag('consent','default',{ad_storage:'granted',ad_user_data:'granted',ad_personalization:'granted',analytics_storage:'granted'});gtag('set','ads_data_redaction',true);gtag('set','url_passthrough',true);try{if(localStorage.getItem('cookie_consent')==='yes'){gtag('consent','update',{ad_storage:'granted',ad_user_data:'granted',ad_personalization:'granted',analytics_storage:'granted'});}}catch(e){}})();`
  return (
    <script
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: script }}
    />
  )
}
