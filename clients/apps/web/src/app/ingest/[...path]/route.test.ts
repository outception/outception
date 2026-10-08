import { NextRequest } from 'next/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { GET, POST } from './route'

const context = (path: string[]) => ({ params: Promise.resolve({ path }) })

describe('visit counter proxy', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('relays an event without our cookies and returns no cookies or encoding', async () => {
    const upstream = vi.fn(
      async () =>
        new Response('{"status":1}', {
          status: 200,
          headers: {
            'content-type': 'application/json',
            'content-encoding': 'gzip',
            'set-cookie': 'tracker=1',
          },
        }),
    )
    vi.stubGlobal('fetch', upstream)
    const request = new NextRequest('http://localhost:3000/ingest/e/?ip=0', {
      method: 'POST',
      body: '{}',
      headers: {
        cookie: 'outception_session=secret',
        'x-outception-user': 'forged',
        referer: 'https://outception.com/auth/email-otp?email=a@example.com',
        'x-forwarded-for': '203.0.113.9',
        'user-agent': 'Mozilla/5.0',
      },
    })
    const response = await POST(request, context(['e', '']))
    expect(response.status).toBe(200)
    expect(response.headers.get('set-cookie')).toBeNull()
    expect(response.headers.get('content-encoding')).toBeNull()
    const [target, init] = upstream.mock.calls[0] as unknown as [
      string,
      RequestInit,
    ]
    expect(target.startsWith('https://')).toBe(true)
    const sent = new Headers(init.headers)
    expect(sent.get('cookie')).toBeNull()
    expect(sent.get('x-outception-user')).toBeNull()
    expect(sent.get('referer')).toBeNull()
    // The country comes from the reader's address, not the server's.
    expect(sent.get('x-forwarded-for')).toBe('203.0.113.9')
    expect(sent.get('user-agent')).toBe('Mozilla/5.0')
  })

  it('answers quietly when the counter is unreachable or the body is huge', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('fetch failed')
      }),
    )
    const down = await POST(
      new NextRequest('http://localhost:3000/ingest/e/', {
        method: 'POST',
        body: '{}',
      }),
      context(['e', '']),
    )
    expect(down.status).toBe(502)
    const huge = await POST(
      new NextRequest('http://localhost:3000/ingest/e/', {
        method: 'POST',
        body: 'x'.repeat(1_000_001),
      }),
      context(['e', '']),
    )
    expect(huge.status).toBe(413)
  })

  it('never finds an inherited name in the allowlist', async () => {
    const upstream = vi.fn()
    vi.stubGlobal('fetch', upstream)
    const response = await POST(
      new NextRequest('http://localhost:3000/ingest/constructor', {
        method: 'POST',
        body: '{}',
      }),
      context(['constructor']),
    )
    expect(response.status).toBe(404)
    expect(upstream).not.toHaveBeenCalled()
  })

  it('refuses paths and methods the counter does not use', async () => {
    const upstream = vi.fn()
    vi.stubGlobal('fetch', upstream)
    const get = await GET(
      new NextRequest('http://localhost:3000/ingest/e/'),
      context(['e']),
    )
    expect(get.status).toBe(404)
    const other = await POST(
      new NextRequest('http://localhost:3000/ingest/api/projects', {
        method: 'POST',
        body: '{}',
      }),
      context(['api', 'projects']),
    )
    expect(other.status).toBe(404)
    expect(upstream).not.toHaveBeenCalled()
  })
})
