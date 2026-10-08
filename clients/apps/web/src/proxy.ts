import { schemas } from '@outception-com/client'
import { RequestCookiesAdapter } from 'next/dist/server/web/spec-extension/adapters/request-cookies'
import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'
import { createServerSideAPI } from './utils/client'
import { buildCSP, mintNonce } from './utils/csp'
import { GEO_COUNTRY_COOKIE } from './utils/i18n/shared'

// A year: the geo country cookie is a convenience, not an identifier.
const COOKIE_MAX_AGE = 365 * 24 * 60 * 60

const OUTCEPTION_AUTH_COOKIE_KEY =
  process.env.OUTCEPTION_AUTH_COOKIE_KEY || 'outception_session'

const AUTHENTICATED_ROUTES = [
  new RegExp('^/start(/.*)?$'),
  new RegExp('^/account(/.*)?$'),
  new RegExp('^/launches/(new|mine|analytics)(/.*)?$'),
  new RegExp('^/launches/[^/]+/edit$'),
  new RegExp('^/settings(/.*)?$'),
  new RegExp('^/oauth2(/.*)?$'),
  new RegExp('^/to(/.*)?$'),
]

const requiresAuthentication = (request: NextRequest): boolean => {
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
  // The counter's client needs trailing-slash requests to reach /ingest
  // untouched (next.config skips the framework's redirect), so pages get the
  // canonical slashless redirect here: one URL per page, and the guarded
  // routes below match it.
  const { pathname } = request.nextUrl
  if (pathname.length > 1 && pathname.endsWith('/')) {
    // A plain URL: the framework's own URL object remembers the slash and
    // would put it back.
    const url = new URL(request.url)
    url.pathname = pathname.replace(/\/+$/, '') || '/'
    return NextResponse.redirect(url, 308)
  }

  let user: schemas['UserRead'] | undefined = undefined

  if (request.cookies.has(OUTCEPTION_AUTH_COOKIE_KEY)) {
    const api = await createServerSideAPI(
      request.headers,
      RequestCookiesAdapter.seal(request.cookies),
    )
    let data: schemas['UserRead'] | undefined
    let response: Response
    let unreachable = false
    try {
      ;({ data, response } = await api.GET('/v1/users/me', {
        cache: 'no-cache',
      }))
    } catch (error) {
      // The API is unreachable (the few seconds of a rolling deploy): render
      // anonymously, as the layout does, instead of a 500 for every reader
      // who holds a session cookie.
      console.error(`Could not reach the API to resolve the session: ${error}`)
      unreachable = true
      response = new Response(null, { status: 503 })
      data = undefined
    }

    // A 429 means resolving the session was rate-limited upstream (the session
    // cookie is being counted in the API's `pending_auth` bucket). We can't
    // determine the user, so we proceed as anonymous rather than turning a
    // transient rate-limit into a hard 500 for the user. It's still logged so
    // we keep visibility on how often this happens.
    if (response.status === 429) {
      console.error(
        `Rate limited while fetching authenticated user: status=429, headers=${JSON.stringify(Object.fromEntries(response.headers.entries()))}`,
      )
    } else if (unreachable) {
      // Already logged above; anonymous for this request.
    } else if ([502, 503, 504].includes(response.status)) {
      // The API or the edge in front of it is between containers: the same
      // short outage as above, answered with a status instead of a failure.
      console.error(
        `API unavailable while resolving the session: ${response.status}`,
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

  // Build the downstream *request* headers (what Server Components read via
  // `headers()`). Strip any client-supplied x-outception-* first so a forged
  // `x-outception-user` header can't impersonate a user, then set the values we
  // derived from the backend-validated session. Using `request.headers` (not
  // response headers) is what actually forwards these to Server Components.
  const requestHeaders = new Headers(request.headers)
  requestHeaders.delete('x-outception-user')
  requestHeaders.delete('x-nonce')
  if (user) {
    requestHeaders.set(
      'x-outception-user',
      Buffer.from(JSON.stringify(user)).toString('base64'),
    )
  }

  // One nonce per request: Next stamps its inline scripts with the nonce it
  // finds in the request's policy header, the layouts read x-nonce for ours,
  // and the response carries the same policy to the browser.
  const nonce = mintNonce()
  const csp = buildCSP({ nonce, pathname: request.nextUrl.pathname })
  requestHeaders.set('x-nonce', nonce)
  requestHeaders.set('content-security-policy', csp)

  const response = NextResponse.next({ request: { headers: requestHeaders } })
  response.headers.set('Content-Security-Policy', csp)

  // Surface the reader's country to the client via a readable cookie, so the
  // landing shell can resolve the country locale in the browser (see
  // resolveClientLocale). Runs per request even for static pages because
  // middleware always executes.
  // Real visitors: the edge's CF-IPCountry header (the deployment sits
  // behind the edge proxy, which injects it on every request). Locally
  // (no edge) a `?geo=XX` query param simulates a country so the flag +
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
     * - ingest (the visit counter's same-origin proxy)
     * - monitoring (Sentry)
     * - assets (static asset files)
     * - _next (Next.js internals: static files, image optimization, data)
     * - og (social card image generation - no session, and running the
     *   session lookup on every crawler unfurl is pure overhead)
     * - favicon.ico, sitemap.xml, robots.txt (metadata files)
     */
    // Segment-bounded: bare prefixes would also skip any future route that
    // merely starts with one of these names, and skipped routes keep the
    // client-forgeable identity header this middleware exists to strip.
    '/((?!(?:api|fonts|ingest|monitoring|assets|_next|og|favicon.ico|sitemap.xml|robots.txt)(?:/|$)).*)',
  ],
}
