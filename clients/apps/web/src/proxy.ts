import { schemas } from '@outception-com/client'
import { nanoid } from 'nanoid'
import { RequestCookiesAdapter } from 'next/dist/server/web/spec-extension/adapters/request-cookies'
import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'
import { COOKIE_MAX_AGE, DISTINCT_ID_COOKIE } from './experiments/constants'
import { createServerSideAPI } from './utils/client'
import { GEO_COUNTRY_COOKIE } from './utils/i18n/shared'

const OUTCEPTION_AUTH_COOKIE_KEY =
  process.env.OUTCEPTION_AUTH_COOKIE_KEY || 'outception_session'

const AUTHENTICATED_ROUTES = [
  new RegExp('^/start(/.*)?$'),
  new RegExp('^/dashboard(/.*)?$'),
  new RegExp('^/settings(/.*)?$'),
  new RegExp('^/oauth2(/.*)?$'),
  new RegExp('^/to(/.*)?$'),
  // The engineering handbook contains internal ops procedures — require login.
  new RegExp('^/handbook(/.*)?$'),
]

const getOrCreateDistinctId = (
  request: NextRequest,
): { id: string; isNew: boolean } => {
  const existing = request.cookies.get(DISTINCT_ID_COOKIE)?.value
  if (existing) {
    return { id: existing, isNew: false }
  }
  return { id: `anon_${nanoid()}`, isNew: true }
}

const isForwardedRoute = (request: NextRequest): boolean => {
  if (request.nextUrl.pathname.startsWith('/ingest/')) {
    return true
  }

  return false
}

const requiresAuthentication = (request: NextRequest): boolean => {
  if (isForwardedRoute(request)) {
    return false
  }

  return AUTHENTICATED_ROUTES.some((route) =>
    route.test(request.nextUrl.pathname),
  )
}

const getLoginResponse = (request: NextRequest): NextResponse => {
  const redirectURL = request.nextUrl.clone()
  redirectURL.pathname = '/auth'
  redirectURL.search = ''
  const returnTo = `${request.nextUrl.pathname}${request.nextUrl.search}`
  redirectURL.searchParams.set('return_to', returnTo)
  return NextResponse.redirect(redirectURL)
}

export async function proxy(request: NextRequest) {
  // Do not run middleware for forwarded routes — the `config.matcher`
  // behavior below doesn't appear to be working consistently with Vercel
  // rewrites
  if (isForwardedRoute(request)) {
    return NextResponse.next()
  }

  let user: schemas['UserRead'] | undefined = undefined

  if (request.cookies.has(OUTCEPTION_AUTH_COOKIE_KEY)) {
    const api = await createServerSideAPI(
      request.headers,
      RequestCookiesAdapter.seal(request.cookies),
    )
    const { data, response } = await api.GET('/v1/users/me', {
      cache: 'no-cache',
    })

    // A 429 means resolving the session was rate-limited upstream (the session
    // cookie is being counted in the API's `pending_auth` bucket). We can't
    // determine the user, so we proceed as anonymous rather than turning a
    // transient rate-limit into a hard 500 for the user. It's still logged so
    // we keep visibility on how often this happens.
    if (response.status === 429) {
      console.error(
        `Rate limited while fetching authenticated user: status=429, headers=${JSON.stringify(Object.fromEntries(response.headers.entries()))}`,
      )
    } else if (!response.ok && response.status !== 401) {
      console.error(
        `Error response: status=${response.status}, headers=${JSON.stringify(Object.fromEntries(response.headers.entries()))}`,
      )
      throw new Error(
        'Unexpected response status while fetching authenticated user',
      )
    }

    user = data
  }

  if (requiresAuthentication(request) && !user) {
    return getLoginResponse(request)
  }

  const { id: distinctId, isNew: isNewDistinctId } =
    getOrCreateDistinctId(request)

  // Build the downstream *request* headers (what Server Components read via
  // `headers()`). Strip any client-supplied x-outception-* first so a forged
  // `x-outception-user` header can't impersonate a user, then set the values we
  // derived from the backend-validated session. Using `request.headers` (not
  // response headers) is what actually forwards these to Server Components.
  const requestHeaders = new Headers(request.headers)
  requestHeaders.delete('x-outception-user')
  requestHeaders.delete('x-outception-distinct-id')
  requestHeaders.set('x-outception-distinct-id', distinctId)
  if (user) {
    requestHeaders.set(
      'x-outception-user',
      Buffer.from(JSON.stringify(user)).toString('base64'),
    )
  }

  const response = NextResponse.next({ request: { headers: requestHeaders } })

  if (isNewDistinctId) {
    response.cookies.set(DISTINCT_ID_COOKIE, distinctId, {
      maxAge: COOKIE_MAX_AGE,
      httpOnly: false,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
    })
  }

  // Surface the reader's country to the client via a readable cookie, so the
  // landing shell can resolve the country locale in the browser (see
  // resolveClientLocale). Runs per request even for static pages because
  // middleware always executes.
  // Real visitors: Cloudflare's CF-IPCountry (the deployment sits behind
  // Cloudflare, which injects this header on every proxied request). Locally
  // (no Cloudflare) a `?geo=XX` query param simulates a country so the flag +
  // weather can be tested; it's inert in production because CF-IPCountry is
  // always present there and takes precedence.
  const geoOverride = request.nextUrl.searchParams.get('geo')
  const country =
    request.headers.get('cf-ipcountry') ??
    (geoOverride && /^[A-Za-z]{2}$/.test(geoOverride)
      ? geoOverride.toUpperCase()
      : null)
  if (country && request.cookies.get(GEO_COUNTRY_COOKIE)?.value !== country) {
    response.cookies.set(GEO_COUNTRY_COOKIE, country, {
      maxAge: COOKIE_MAX_AGE,
      httpOnly: false,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
    })
  }

  return response
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - fonts (static font files)
     * - ingest (Posthog)
     * - monitoring (Sentry)
     * - assets (static asset files)
     * - _next (Next.js internals: static files, image optimization, data)
     * - favicon.ico, sitemap.xml, robots.txt (metadata files)
     */
    '/((?!api|fonts|ingest|monitoring|assets|_next|favicon.ico|sitemap.xml|robots.txt).*)',
  ],
}
