import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { ACCOUNTS_ENABLED } from './features'

describe('the accounts switch', () => {
  it('is mirrored exactly in the build config', () => {
    // next.config.mjs cannot import from src/, so it carries a copy; the
    // copy drives the session-cookie redirect, and a stale copy sends a
    // reader with a cookie round / and /start without end.
    const config = readFileSync(
      join(__dirname, '..', '..', 'next.config.mjs'),
      'utf8',
    )
    const match = /^const ACCOUNTS_ENABLED = (true|false)$/m.exec(config)
    expect(match?.[1]).toBe(String(ACCOUNTS_ENABLED))
  })
})
