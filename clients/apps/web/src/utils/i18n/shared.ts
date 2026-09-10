// Cookie the middleware sets from Cloudflare's CF-IPCountry, so client
// components can resolve the reader's country (and flag) after hydration.
export const GEO_COUNTRY_COOKIE = 'oc-geo-country'

function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]+)`))
  if (!match) return null
  try {
    return decodeURIComponent(match[1])
  } catch {
    // A malformed %-sequence (only reachable if a cookie is hand-edited) must
    // not throw - this runs during render via getClientCountry.
    return match[1]
  }
}

/** The reader's detected country (Cloudflare CF-IPCountry, mirrored into the
 * geo cookie by the proxy) as an ISO-3166 alpha-2 code, for seeding their
 * national cards and showing their country's flag. Client-only - returns null
 * during SSR or without the cookie. */
export function getClientCountry(): string | null {
  const country = readCookie(GEO_COUNTRY_COOKIE)
  return country ? country.trim().toUpperCase() : null
}
