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
  it('takes turns across sources instead of draining one', () => {
    // A row is nine tiles. Draining would make every row nine headlines from
    // one outlet, which defeats the point of showing the whole wall at once.
    const tiles = buildTiles(
      [src('bbc', 10), src('npr', 10), src('ars', 10)],
      [meta('bbc'), meta('npr'), meta('ars')],
      6,
    )
    const sources = tiles.map((t) => t.source)
    expect(new Set(sources.slice(0, 3)).size).toBe(3)
    expect(sources.filter((s) => s === 'BBC')).toHaveLength(2)
  })

  it('stops at the limit', () => {
    const tiles = buildTiles([src('bbc', 100)], [meta('bbc')], 9)
    expect(tiles).toHaveLength(9)
  })

  it('terminates when the sources run dry before the limit', () => {
    // Fewer headlines than the mosaic wants must not spin: queues empty and
    // the loop has to give up rather than ask for more forever.
    const tiles = buildTiles([src('bbc', 2), src('npr', 1)], [meta('bbc')], 90)
    expect(tiles).toHaveLength(3)
  })

  it('skips sources with no headlines', () => {
    const tiles = buildTiles(
      [{ id: 'empty' }, src('bbc', 2)],
      [meta('bbc')],
      10,
    )
    expect(tiles).toHaveLength(2)
    expect(tiles.every((t) => t.source === 'BBC')).toBe(true)
  })

  it('falls back when a source has no metadata', () => {
    // The batch route can return a source the metadata request did not, so a
    // missing meta must degrade to something renderable, never crash a tile.
    const tiles = buildTiles([src('mystery', 1)], [], 5)
    expect(tiles[0]!.source).toBe('mystery')
    expect(tiles[0]!.color).toMatch(/^#/)
    expect(tiles[0]!.logo).toBeNull()
  })

  it('shows different headlines on each pass through the wall', () => {
    // Reaching the bottom hands back a fresh mosaic instead of a dead end, so
    // the centre - the part the zoom puts in your face - is never twice the
    // same. Without this the endless scroll would just repeat itself.
    const data = [src('bbc', 8), src('npr', 8), src('ars', 8)]
    const metas = [meta('bbc'), meta('npr'), meta('ars')]
    const first = buildTiles(data, metas, 6, 0).map((t) => t.title)
    const second = buildTiles(data, metas, 6, 1).map((t) => t.title)
    expect(second).not.toEqual(first)
  })

  it('keeps every source in play when its headlines run out', () => {
    // The rotation wraps rather than dropping a source off the end, or an
    // outlet with few headlines would vanish after a couple of passes.
    const data = [src('bbc', 2)]
    const metas = [meta('bbc')]
    for (const cycle of [0, 1, 2, 5, 11]) {
      expect(buildTiles(data, metas, 2, cycle)).toHaveLength(2)
    }
  })

  it('carries the headline and its link onto the tile', () => {
    const tiles = buildTiles([src('bbc', 1)], [meta('bbc')], 1)
    expect(tiles[0]!.title).toBe('bbc headline 0')
    expect(tiles[0]!.href).toBe('https://example.test/bbc/0')
  })
})
