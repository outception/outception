import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { InlineSummary } from './InlineSummary'

const ARTICLE = 'https://news.example.com/story'

const sse = (...events: object[]) =>
  new Response(events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join(''), {
    headers: { 'content-type': 'text/event-stream' },
  })

const answer = (available: boolean, stream: Response) =>
  vi.fn(async (input: RequestInfo | URL) =>
    String(input).includes('/summary/available')
      ? Response.json({ available })
      : stream,
  )

describe('InlineSummary', () => {
  let open: ReturnType<typeof vi.fn>
  beforeEach(() => {
    open = vi.fn()
    vi.stubGlobal('open', open)
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  const fullArticle = () =>
    screen.findByRole('link', {
      name: 'Full article',
    }) as Promise<HTMLAnchorElement>

  it('never leaves the page when no summary can be had', async () => {
    vi.stubGlobal('fetch', answer(false, sse({ error: 'unavailable' })))
    render(<InlineSummary url={ARTICLE} sourceName="Example" />)
    const link = await fullArticle()
    expect(link.href).toBe(ARTICLE)
    expect(screen.getByText(/No summary is available/)).toBeTruthy()
    expect(open).not.toHaveBeenCalled()
  })

  it('says so when the summary fails after loading', async () => {
    vi.stubGlobal('fetch', answer(true, sse({ error: 'unavailable' })))
    render(<InlineSummary url={ARTICLE} sourceName="Example" />)
    await fullArticle()
    expect(screen.getByText(/No summary is available/)).toBeTruthy()
    expect(open).not.toHaveBeenCalled()
  })

  it('answers a video link at once, without asking the server', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    render(
      <InlineSummary url="https://www.youtube.com/watch?v=x" sourceName="Y" />,
    )
    await fullArticle()
    expect(fetch).not.toHaveBeenCalled()
    expect(open).not.toHaveBeenCalled()
  })

  it('shows the summary with the article link under it', async () => {
    vi.stubGlobal(
      'fetch',
      answer(true, sse({ delta: 'A short summary.' }, { done: true })),
    )
    render(<InlineSummary url={ARTICLE} sourceName="Example" />)
    await waitFor(() =>
      expect(screen.getByText('A short summary.')).toBeTruthy(),
    )
    expect((await fullArticle()).href).toBe(ARTICLE)
  })
})
