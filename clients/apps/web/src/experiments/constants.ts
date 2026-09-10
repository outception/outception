export const DISTINCT_ID_COOKIE = 'outception_distinct_id'
export const DISTINCT_ID_HEADER = 'x-outception-distinct-id'
export const COOKIE_MAX_AGE = 60 * 60 * 24 * 365 // 1 year
// Mirrors the `cookie_consent` localStorage value so the proxy (which only
// sees cookies) knows whether a persistent distinct id may be set.
export const CONSENT_COOKIE = 'cookie_consent'
