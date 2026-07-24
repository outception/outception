import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const sources = vi.fn()
const source = vi.fn()
const search = vi.fn()

vi.mock('@/utils/news', () => ({
  newsApi: {
    sources: (...args: unknown[]) => sources(...args),
    source: (...args: unknown[]) => source(...args),
    search: (...args: unknown[]) => search(...args),
  },
}))

import { useNewsSearch, useNewsSource, useNewsSources } from './news'

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

beforeEach(() => {
  sources.mockReset()
  source.mockReset()
  search.mockReset()
})

describe('useNewsSources', () => {
  it('fetches the source list', async () => {
    sources.mockResolvedValue([{ id: 'hackernews' }])
    const { result } = renderHook(() => useNewsSources(), {
      wrapper: makeWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([{ id: 'hackernews' }])
  })
})

describe('useNewsSource', () => {
  it('stays idle and does not fetch when id is null', () => {
    const { result } = renderHook(() => useNewsSource(null), {
      wrapper: makeWrapper(),
    })
    expect(result.current.fetchStatus).toBe('idle')
    expect(source).not.toHaveBeenCalled()
  })

  it('requests the source with latest=false and the given sort', async () => {
    source.mockResolvedValue({ id: 'hackernews' })
    const { result } = renderHook(() => useNewsSource('hackernews', 'top'), {
      wrapper: makeWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(source).toHaveBeenCalledWith('hackernews', false, 'top', undefined)
  })

  it('passes the reader locale so headlines come back translated', async () => {
    source.mockResolvedValue({ id: 'hackernews' })
    const { result } = renderHook(
      () => useNewsSource('hackernews', 'hot', 'de'),
      { wrapper: makeWrapper() },
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(source).toHaveBeenCalledWith('hackernews', false, 'hot', 'de')
  })
})

describe('useNewsSearch', () => {
  it('does not fetch for queries under 2 characters', () => {
    const { result } = renderHook(() => useNewsSearch('a'), {
      wrapper: makeWrapper(),
    })
    expect(result.current.fetchStatus).toBe('idle')
    expect(search).not.toHaveBeenCalled()
  })

  it('searches once the query is long enough', async () => {
    search.mockResolvedValue({ sources: [], items: [] })
    const { result } = renderHook(() => useNewsSearch('rust'), {
      wrapper: makeWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    // The hook supplies the reader's locale (default 'en' with no provider) so
    // foreign-language results come back translated.
    expect(search).toHaveBeenCalledWith('rust', 'en')
  })
})
