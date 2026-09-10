import { describe, expect, it } from 'vitest'
import { buildTiles } from './wallTiles'

const src = (id: string, n: number) => ({
  id,
  items: Array.from({ length: n }, (_, i) => ({
    id: `${id}-${i}`,
    title: `${id} headline ${i}`,
    url: `https://example.test/${id}/${i}`,
  })),
})

const meta = (id: string) => ({
  id,
  name: id.toUpperCase(),
  color: '#123456',
  logo: `https://logo.test/${id}.png`,
})

describe('buildTiles', () => {
  it('runs the reader’s card order down the middle column', () => {
    // The middle column is the one the zoom drives at the reader, so it is the
    // one that has to be their stack: the top card first - their country's
    // news - then the next card, and so on down the rows.
    const data = [src('home', 9), src('bbc', 9), src('nyt', 9)]
    const metas = [meta('home'), meta('bbc'), meta('nyt')]
    const tiles = buildTiles(data, metas, 3, 3)
    const middles = [tiles[1], tiles[4], tiles[7]].map((t) => t!.id)
    expect(middles).toEqual(['home', 'bbc', 'nyt'])
  })

  it('opens every pass on the same card, with different headlines', () => {
    // A page arriving from below is a fresh deal, but the stack is the stack:
    // its middle still starts at the reader's top card.
    const data = [src('home', 9), src('bbc', 9), src('nyt', 9)]
    const metas = [meta('home'), meta('bbc'), meta('nyt')]
    const first = buildTiles(data, metas, 3, 3, 0)
    const second = buildTiles(data, metas, 3, 3, 1)
    expect(second[1]!.id).toBe('home')
    expect(second[1]!.title).not.toBe(first[1]!.title)
  })

  it('takes turns across sources either side of the middle', () => {
    // Draining would make a row nine headlines from one outlet, which defeats
    // the point of showing the whole wall at once.
    const tiles = buildTiles(
      [src('bbc', 10), src('npr', 10), src('ars', 10)],
      [meta('bbc'), meta('npr'), meta('ars')],
      3,
      2,
    )
    expect(new Set(tiles.slice(0, 3).map((t) => t.id)).size).toBe(3)
  })

  it('fills exactly the grid it is asked for', () => {
    const tiles = buildTiles([src('bbc', 100)], [meta('bbc')], 9, 2)
    expect(tiles).toHaveLength(18)
  })

  it('terminates when the sources run dry before the grid is full', () => {
    // Fewer headlines than the mosaic wants must not spin: queues empty and
    // the loop has to give up rather than ask for more forever.
    const tiles = buildTiles(
      [src('bbc', 2), src('npr', 1)],
      [meta('bbc')],
      9,
      10,
    )
    expect(tiles).toHaveLength(3)
  })

  it('skips sources with no headlines', () => {
    const tiles = buildTiles(
      [{ id: 'empty' }, src('bbc', 2)],
      [meta('bbc')],
      3,
      3,
    )
    expect(tiles).toHaveLength(2)
    expect(tiles.every((t) => t.source === 'BBC')).toBe(true)
  })

  it('falls back when a source has no metadata', () => {
    // The batch route can return a source the metadata request did not, so a
    // missing meta must degrade to something renderable, never crash a tile.
    const tiles = buildTiles([src('mystery', 1)], [], 3, 3)
    expect(tiles[0]!.source).toBe('mystery')
    expect(tiles[0]!.color).toMatch(/^#/)
    expect(tiles[0]!.logo).toBeNull()
  })

  it('keeps every source in play when its headlines run out', () => {
    // The rotation wraps rather than dropping a source off the end, or an
    // outlet with few headlines would vanish after a couple of passes.
    const data = [src('bbc', 2)]
    const metas = [meta('bbc')]
    for (const cycle of [0, 1, 2, 5, 11]) {
      expect(buildTiles(data, metas, 2, 1, cycle)).toHaveLength(2)
    }
  })

  it('carries the headline and its link onto the tile', () => {
    const tiles = buildTiles([src('bbc', 1)], [meta('bbc')], 1, 1)
    expect(tiles[0]!.title).toBe('bbc headline 0')
    expect(tiles[0]!.href).toBe('https://example.test/bbc/0')
  })
})
