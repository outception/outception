import { describe, expect, it } from 'vitest'
import {
  canMove,
  clampIndex,
  initialIndex,
  moveTo,
  parsePositions,
  reconcile,
  resolveIndexOnChange,
  withPosition,
  wrapIndex,
} from './swipeDeck'

describe('indexes', () => {
  it('clamps and wraps', () => {
    expect(clampIndex(5, 3)).toBe(2)
    expect(clampIndex(-1, 3)).toBe(0)
    expect(wrapIndex(3, 3)).toBe(0)
    expect(wrapIndex(-1, 3)).toBe(2)
    expect(wrapIndex(4, 0)).toBe(0)
    expect(canMove(1)).toBe(false)
    expect(canMove(2)).toBe(true)
  })

  it('starts on the shared card, else the saved one, else the first', () => {
    expect(initialIndex(['a', 'b', 'c'], 'b')).toBe(1)
    expect(initialIndex(['a', 'b', 'c'], 'b', 'c')).toBe(2)
    expect(initialIndex(['a', 'b', 'c'], 'gone', 'missing')).toBe(0)
    expect(initialIndex(['a'], undefined)).toBe(0)
  })

  it('jumps to an addition and otherwise stays anchored by id', () => {
    expect(resolveIndexOnChange(['a', 'n', 'b'], ['a', 'b'], 'b', 1)).toEqual({
      index: 1,
      added: true,
    })
    expect(resolveIndexOnChange(['b', 'a'], ['a', 'b'], 'b', 1)).toEqual({
      index: 0,
      added: false,
    })
    expect(resolveIndexOnChange(['a'], ['a', 'b'], 'b', 1)).toEqual({
      index: 1,
      added: false,
    })
  })
})

describe('state', () => {
  it('moves with wrap-around and records the active id', () => {
    expect(moveTo(['a', 'b'], 2)).toEqual({ index: 0, activeId: 'a' })
    expect(moveTo(['a', 'b'], -1)).toEqual({ index: 1, activeId: 'b' })
    expect(moveTo([], 1)).toEqual({ index: 0, activeId: null })
  })

  it('reconcile never leaves the counter past the end', () => {
    const r = reconcile({ index: 1, activeId: 'b' }, ['a'], ['a', 'b'])
    expect(r).toEqual({ index: 0, activeId: 'a', added: false })
  })
})

describe('positions', () => {
  it('parses a map of strings and rejects anything else', () => {
    expect(parsePositions('{"wall":"a","x":1}')).toEqual({ wall: 'a' })
    expect(parsePositions('[1]')).toEqual({})
    expect(parsePositions('nope')).toEqual({})
    expect(parsePositions(null)).toEqual({})
    expect(withPosition({ wall: 'a' }, 'hand', 'b')).toEqual({
      wall: 'a',
      hand: 'b',
    })
  })
})
