import type { Middleware } from '@outception-com/client'
import {
  getRefresherAccessToken,
  noteRequestSucceeded,
  hasRefreshToken,
  isAccessTokenStale,
  refreshAccessToken,
} from './refresher'

const isOAuthEndpoint = (url: string): boolean =>
  url.includes('/v1/oauth2/token') || url.includes('/v1/oauth2/revoke')

// Bodies of in-flight requests, kept so a 401 retry can rebuild the request.
// By the time onResponse runs the original body stream has been consumed, so
// `new Request(request)` either throws "Already read" on Hermes or produces a
// body-less request that the server rejects as a 422.
const pendingBodies = new WeakMap<Request, ArrayBuffer>()

const hasBody = (request: Request): boolean =>
  request.method !== 'GET' && request.method !== 'HEAD'

export const refreshMiddleware: Middleware = {
  onRequest: async ({ request }) => {
    if (isOAuthEndpoint(request.url)) return

    if (hasBody(request)) {
      try {
        pendingBodies.set(request, await request.clone().arrayBuffer())
      } catch {
        // Unclonable body (a stream) - the retry below falls back to no body.
      }
    }

    if (hasRefreshToken() && isAccessTokenStale()) {
      const newAccessToken = await refreshAccessToken()
      if (!newAccessToken) return

      const next = new Request(request)
      next.headers.set('Authorization', `Bearer ${newAccessToken}`)
      return next
    }

    const latestToken = getRefresherAccessToken()
    if (!latestToken) return

    const expected = `Bearer ${latestToken}`
    if (request.headers.get('Authorization') !== expected) {
      const next = new Request(request)
      next.headers.set('Authorization', expected)
      return next
    }
  },

  onResponse: async ({ request, response, options }) => {
    // Any non-error response proves connectivity, which retires the transient
    // marker so a later real auth failure isn't misread as a network blip.
    if (response.ok) noteRequestSucceeded()
    if (response.status !== 401) return
    if (isOAuthEndpoint(request.url)) return
    if (!hasRefreshToken()) return

    const newAccessToken = await refreshAccessToken()
    if (!newAccessToken) return

    const headers = new Headers(request.headers)
    headers.set('Authorization', `Bearer ${newAccessToken}`)
    const body = pendingBodies.get(request)
    const retry = new Request(request.url, {
      method: request.method,
      headers,
      body: hasBody(request) && body ? body : undefined,
      credentials: request.credentials,
      redirect: request.redirect,
    })
    return await options.fetch(retry)
  },
}
