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
const ASSET_HOST = 'https://eu-assets.i.posthog.com'

// Hop-by-hop and connection-specific headers must not be replayed: fetch
// already decompressed the body, so a passed-through content-encoding would
// make the browser try to re-decompress plain bytes.
const STRIP_RESPONSE = new Set([
  'content-encoding',
  'content-length',
  'transfer-encoding',
  'connection',
])

const proxy = async (request: NextRequest, path: string[]) => {
  const upstream = path[0] === 'static' ? ASSET_HOST : API_HOST
  const search = new URL(request.url).search
  const target = `${upstream}/${path.map(encodeURIComponent).join('/')}${search}`

  const headers = new Headers(request.headers)
  headers.delete('cookie')
  headers.delete('authorization')
  headers.delete('host')

  const response = await fetch(target, {
    method: request.method,
    headers,
    body: request.body,
    redirect: 'manual',
    // Streaming request bodies require half duplex; types lag the runtime.
    // @ts-expect-error -- duplex is real but not in the lib types yet
    duplex: 'half',
  })

  const responseHeaders = new Headers()
  response.headers.forEach((value, key) => {
    if (!STRIP_RESPONSE.has(key.toLowerCase())) {
      // append, not set: repeated headers (Set-Cookie) must not collapse.
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
export const OPTIONS = async (request: NextRequest, context: Context) =>
  proxy(request, (await context.params).path)
