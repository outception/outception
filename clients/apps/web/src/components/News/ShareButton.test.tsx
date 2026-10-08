import { describe, expect, it } from 'vitest'
import { parseShareLink } from '@outception-com/news-core'
import { shareLinkFor } from './ShareButton'

describe('shareLinkFor', () => {
  it('keeps the lead in the query and carries the deck, theme and time', () => {
    localStorage.setItem('news.wallTheme', 'tide')
    localStorage.setItem('news.wallLook', 'noir')
    const link = shareLinkFor(
      'bbc-world',
      ['bbc-world', 'nytimes'],
      1_700_000_000_000,
    )
    expect(link.startsWith('/?card=bbc-world#')).toBe(true)
    const [search, hash] = link.slice(1).split('#')
    const state = parseShareLink({ search, hash: `#${hash}` })
    expect(state).toMatchObject({
      lead: 'bbc-world',
      cards: ['bbc-world', 'nytimes'],
      edition: 'tide',
      look: 'noir',
      at: 1_700_000_000,
    })
  })

  it('drops the deck for a single card and the look when plain', () => {
    localStorage.removeItem('news.wallTheme')
    localStorage.removeItem('news.wallLook')
    const state = parseShareLink({
      hash: `#${shareLinkFor('x', ['x']).split('#')[1]}`,
    })
    expect(state.cards).toEqual([])
    expect(state.look).toBeNull()
    expect(state.edition).toBe('midnight')
  })
})
