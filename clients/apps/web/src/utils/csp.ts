// The Content Security Policy, built per request in the proxy so every
// inline script carries a one-time nonce instead of the page allowing any
// inline script ('unsafe-inline'). Next reads the nonce from the request's
// policy header and stamps its own inline scripts with it; ours get it from
// the x-nonce request header.
//
// Image hosts, by where the wall gets them: the API for product logos and
// media; account avatars (social login, gravatar); the catalog's publisher
// logos (a script CDN, the wiki uploads and commons, the favicon service,
// the flag CDN); and the hosts the table providers pass through from their
// upstreams (coin logos, finance logos, sports crests). A browser walk over
// the deck and the pages records no violation against this list.
const ENVIRONMENT = process.env.NEXT_PUBLIC_ENVIRONMENT || 'development'
const API_URL = process.env.NEXT_PUBLIC_API_URL || ''

const IMAGE_HOSTS = [
  'https://www.gravatar.com',
  'https://lh3.googleusercontent.com',
  'https://avatars.githubusercontent.com',
  'https://upload.wikimedia.org',
  'https://commons.wikimedia.org',
  'https://cdn.jsdelivr.net',
  'https://flagcdn.com',
  'https://*.gstatic.com',
  'https://static.finnhub.io',
  'https://static2.finnhub.io',
  'https://coin-images.coingecko.com',
  'https://assets.coingecko.com',
  'https://crests.football-data.org',
  'https://a.espncdn.com',
].join(' ')

/** The offline page is precached by the service worker and served from
 * that cache with the headers it was stored with: a nonce minted for one
 * request would never match the page's inline script later, so that one
 * page keeps the inline allowance. */
const INLINE_PAGES = new Set(['/offline.html'])

export const buildCSP = ({
  nonce,
  pathname,
}: {
  nonce: string
  pathname: string
}): string => {
  const scriptSources = INLINE_PAGES.has(pathname)
    ? "'self' 'unsafe-inline'"
    : `'self' 'nonce-${nonce}' 'strict-dynamic'`
  const directives = [
    "default-src 'self'",
    `connect-src 'self' ${API_URL}`,
    "frame-src 'self'",
    `script-src ${scriptSources}${ENVIRONMENT === 'development' ? " 'unsafe-eval'" : ''}`,
    "style-src 'self' 'unsafe-inline'",
    `img-src 'self' blob: data: ${API_URL} ${IMAGE_HOSTS}`,
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
  ]
  // Don't add form-action to the OAuth2 authorize page, as it blocks the
  // OAuth2 redirection (a ten-year-old debate about whether to block
  // redirects with form-action: https://github.com/w3c/webappsec-csp/issues/8).
  if (!/^\/oauth2(\/|$)/.test(pathname)) {
    directives.push(`form-action 'self' ${API_URL} outception:`)
  }
  if (ENVIRONMENT !== 'development') {
    directives.push('upgrade-insecure-requests')
  }
  return directives.join('; ')
}

/** 128 random bits, base64: one per request. */
export const mintNonce = (): string => {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return btoa(String.fromCharCode(...bytes))
}
