import { describe, expect, it } from 'vitest'
import { findFirstErrorMessage } from './errors'

describe('findFirstErrorMessage', () => {
  it('finds message in flat error object', () => {
    const errors = { name: { type: 'required', message: 'Name is required' } }
    expect(findFirstErrorMessage(errors)).toBe('Name is required')
  })

  it('finds message in nested array field errors', () => {
    const errors = {
      prices: [
        {
          price_amount: {
            type: 'minimum_price',
            message: 'Amount must be at least $0.50',
          },
        },
      ],
    }
    expect(findFirstErrorMessage(errors)).toBe('Amount must be at least $0.50')
  })

  it('finds message in deeply nested errors', () => {
    const errors = {
      prices: [
        undefined,
        {
          price_amount: {
            type: 'minimum_price',
            message: 'Amount must be at least ₹60.00',
          },
        },
      ],
    }
    expect(findFirstErrorMessage(errors)).toBe('Amount must be at least ₹60.00')
  })

  it('returns undefined for empty object', () => {
    expect(findFirstErrorMessage({})).toBeUndefined()
  })

  it('returns undefined for null/undefined', () => {
    expect(findFirstErrorMessage(null)).toBeUndefined()
    expect(findFirstErrorMessage(undefined)).toBeUndefined()
  })

  it('ignores non-string message values', () => {
    const errors = { field: { type: 'required', message: 42 } }
    expect(findFirstErrorMessage(errors)).toBeUndefined()
  })
})
