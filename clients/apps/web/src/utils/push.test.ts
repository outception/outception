import { describe, expect, it } from 'vitest'
import { applicationServerKey } from './push'

describe('applicationServerKey', () => {
  it('decodes URL-safe base64 without padding', () => {
    const key = applicationServerKey('BA-_')
    expect(Array.from(key)).toEqual([4, 15, 191])
    expect(applicationServerKey('').length).toBe(0)
  })
})
