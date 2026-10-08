import { describe, expect, it } from 'vitest'
import { buildCSP, mintNonce } from './csp'

describe('buildCSP', () => {
  it('allows scripts by nonce, never by unsafe-inline', () => {
    const csp = buildCSP({ nonce: 'abc', pathname: '/' })
    const script = csp.split('; ').find((d) => d.startsWith('script-src'))
    expect(script).toContain("'nonce-abc'")
    expect(script).toContain("'strict-dynamic'")
    expect(script).not.toContain("'unsafe-inline'")
  })

  it('keeps the inline allowance for the precached offline page only', () => {
    const script = buildCSP({ nonce: 'abc', pathname: '/offline.html' })
      .split('; ')
      .find((d) => d.startsWith('script-src'))
    expect(script).toContain("'unsafe-inline'")
    expect(script).not.toContain('nonce')
  })

  it('leaves form-action off the authorize page', () => {
    expect(buildCSP({ nonce: 'abc', pathname: '/' })).toContain('form-action')
    expect(
      buildCSP({ nonce: 'abc', pathname: '/oauth2/authorize' }),
    ).not.toContain('form-action')
    expect(buildCSP({ nonce: 'abc', pathname: '/oauth2-help' })).toContain(
      'form-action',
    )
  })

  it('always denies framing and plugins', () => {
    const csp = buildCSP({ nonce: 'abc', pathname: '/launches' })
    expect(csp).toContain("frame-ancestors 'none'")
    expect(csp).toContain("object-src 'none'")
  })
})

describe('mintNonce', () => {
  it('is fresh every time and base64', () => {
    const a = mintNonce()
    const b = mintNonce()
    expect(a).not.toEqual(b)
    expect(a).toMatch(/^[A-Za-z0-9+/]+=*$/)
  })
})
