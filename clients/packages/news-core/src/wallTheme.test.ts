import { describe, expect, it } from 'vitest'
import {
  DEFAULT_EDITION_ID,
  LEGACY_EDITION_IDS,
  WALL_EDITIONS,
  WALL_LOOKS,
  lookFilter,
  normalizeEdition,
  normalizeLook,
} from './wallTheme'

describe('editions', () => {
  it('has five editions with both tones and migrates legacy ids', () => {
    expect(WALL_EDITIONS).toHaveLength(5)
    for (const e of WALL_EDITIONS) {
      expect(e.chrome.light).toMatch(/^#[0-9a-f]{6}$/)
      expect(e.chrome.dark).toMatch(/^#[0-9a-f]{6}$/)
    }
    expect(normalizeEdition(null).id).toBe(DEFAULT_EDITION_ID)
    expect(normalizeEdition('nope').id).toBe(DEFAULT_EDITION_ID)
    expect(normalizeEdition('tide').id).toBe('tide')
    for (const [legacy, target] of Object.entries(LEGACY_EDITION_IDS)) {
      expect(normalizeEdition(legacy).id, legacy).toBe(target)
    }
  })

  it('looks default to plain and compile to CSS filters', () => {
    expect(WALL_LOOKS.map((l) => l.id)).toEqual(['plain', 'noir', 'night'])
    expect(normalizeLook(undefined).id).toBe('plain')
    expect(lookFilter(normalizeLook('plain'))).toBe('none')
    expect(lookFilter(normalizeLook('noir'))).toBe(
      'grayscale(1) contrast(1.15) sepia(0.15) brightness(0.95)',
    )
  })
})
