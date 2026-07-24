import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const forecast = vi.fn()

vi.mock('@/utils/weather', () => ({
  weatherApi: {
    forecast: (...args: unknown[]) => forecast(...args),
  },
}))

import { useWeather } from './weather'

const makeWrapper = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  Wrapper.displayName = 'TestQueryWrapper'
  return Wrapper
}

// Simulate the reader denying / geolocation being unavailable so the country
// cookie is the only possible signal.
const denyGeolocation = () => {
  vi.stubGlobal('navigator', {
    geolocation: {
      getCurrentPosition: (_ok: unknown, err: () => void) => err(),
    },
  })
}

const setGeoCookie = (country: string | null) => {
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    get: () => (country ? `oc-geo-country=${country}` : ''),
  })
}

beforeEach(() => forecast.mockReset())
afterEach(() => vi.unstubAllGlobals())

describe('useWeather', () => {
  it('stays disabled (no fetch) when there is no location signal', async () => {
    denyGeolocation()
    setGeoCookie(null) // no precise location AND no IP country
    const { result } = renderHook(() => useWeather(), {
      wrapper: makeWrapper(),
    })
    // Let the resolve effect run; the query must never fire.
    await waitFor(() => expect(result.current.fetchStatus).toBe('idle'))
    expect(forecast).not.toHaveBeenCalled()
    expect(result.current.data).toBeUndefined()
  })

  it('fetches by IP country when geolocation is denied but the cookie is set', async () => {
    denyGeolocation()
    setGeoCookie('IE')
    forecast.mockResolvedValue({ location: 'Dublin' })
    const { result } = renderHook(() => useWeather(), {
      wrapper: makeWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(forecast).toHaveBeenCalledWith({ country: 'IE' })
  })
})
