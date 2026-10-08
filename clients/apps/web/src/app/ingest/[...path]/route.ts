import type { NextRequest } from 'next/server'

/** PostHog reverse proxy with the cookie tap closed.
 *
 * posthog-js calls same-origin `/ingest/*`, so the browser attaches every
 * cookie for our host - including the session cookie. The old Next rewrite
 * forwarded the request verbatim, which handed those cookies to a third
 * party on every analytics beacon. This handler forwards the same traffic
 * minus credentials.
 */

const API_HOST = 'https://eu.i.posthog.com'

// The endpoints the client uses with external loading off: events, the
// remote config, and nothing else. Anything else is not ours to relay.
const ALLOWED: Record<string, readonly string[]> = {
  e: ['POST'],
  i: ['POST'],
  batch: ['POST'],
  decide: ['POST'],
  flags: ['POST'],
  array: ['GET'],
}

// The request headers the counter needs, and nothing else: no cookies or
// credentials, no hop-by-hop headers (the runtime's fetch refuses some of
// them outright), and no referrer, which can carry a query string. The
// forwarded-for address is the reader's, pinned by the edge; the counter
// turns it into a country and keeps no address.
const FORWARD = [
  'accept',
  'accept-language',
  'content-type',
  'origin',
  'user-agent',
  'x-forwarded-for',
]

// Events are small; anything larger is not the counter talking.
const MAX_BODY_BYTES = 1_000_000

// Hop-by-hop and connection-specific headers must not be replayed: fetch
// already decompressed the body, so a passed-through content-encoding would
// make the browser try to re-decompress plain bytes.
const STRIP_RESPONSE = new Set([
  // No cookies on our origin from the counter: it runs without them.
  'set-cookie',
  'content-encoding',
  'content-length',
  'transfer-encoding',
  'connection',
])

const proxy = async (request: NextRequest, path: string[]) => {
  const endpoint = path[0] ?? ''
  // Own keys only: a path like /ingest/constructor must not find an
  // inherited property.
  const methods = Object.hasOwn(ALLOWED, endpoint) ? ALLOWED[endpoint] : null
  if (!methods?.includes(request.method)) {
    return new Response(null, { status: 404 })
  }
  const search = new URL(request.url).search
  const target = `${API_HOST}/${path.map(encodeURIComponent).join('/')}${search}`

  const headers = new Headers()
  for (const name of FORWARD) {
    const value = request.headers.get(name)
    if (value) headers.set(name, value)
  }
  let body: ArrayBuffer | undefined
  if (request.method !== 'GET') {
    body = await request.arrayBuffer()
    if (body.byteLength > MAX_BODY_BYTES) {
      return new Response(null, { status: 413 })
    }
  }

  let response: Response
  try {
    response = await fetch(target, {
      method: request.method,
      headers,
      body,
      redirect: 'manual',
    })
  } catch {
    // The counter is unreachable: a quiet failure for a fire-and-forget
    // beacon, not an error page.
    return new Response(null, { status: 502 })
  }

  const responseHeaders = new Headers()
  response.headers.forEach((value, key) => {
    if (!STRIP_RESPONSE.has(key.toLowerCase())) {
      responseHeaders.append(key, value)
    }
  })
  return new Response(response.body, {
    status: response.status,
    headers: responseHeaders,
  })
}

type Context = { params: Promise<{ path: string[] }> }

export const GET = async (request: NextRequest, context: Context) =>
  proxy(request, (await context.params).path)
export const POST = async (request: NextRequest, context: Context) =>
  proxy(request, (await context.params).path)
