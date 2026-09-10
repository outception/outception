import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { PAPER_COLOR } from './brand'
import {
  DEFAULT_WALL_THEME,
  DEFAULT_WALL_THEME_ID,
  WALL_THEMES,
} from './wallTheme'

const css = readFileSync(
  join(__dirname, '../styles/globals.css'),
  'utf-8',
).toLowerCase()

const layout = readFileSync(
  join(__dirname, '../app/layout.tsx'),
  'utf-8',
).toLowerCase()

// brand.ts derives the PWA manifest's install colors from the default
// edition's chrome. This guards that the default edition's light chrome still
// matches its --color-paper CSS token (the surface a light-mode install
// shows), so the manifest never advertises a color the app doesn't use.
describe('default-edition install color stays in sync with the CSS token', () => {
  it("PAPER_COLOR matches the default edition's --color-paper", () => {
    const block = css.slice(
      css.indexOf(`[data-theme='${DEFAULT_WALL_THEME.id}']`),
    )
    const match = block.match(/--color-paper:\s*([^;]+);/)
    expect(match?.[1].trim()).toBe(PAPER_COLOR.toLowerCase())
  })
})

// The pre-hydration inline script in layout.tsx hard-codes a per-edition,
// per-tone chrome map and the first-visit default edition (it runs before any
// module loads, so it can't import WALL_THEMES). These guard the duplicated
// values against drifting from the WALL_THEMES source of truth.
describe('pre-hydration script mirrors the wallTheme source of truth', () => {
  for (const theme of WALL_THEMES) {
    it(`chrome map carries ${theme.id} [${theme.chrome.light}, ${theme.chrome.dark}]`, () => {
      const entry = `${theme.id}:['${theme.chrome.light}','${theme.chrome.dark}']`
      expect(layout).toContain(entry.toLowerCase())
    })
  }

  it(`default edition falls back to '${DEFAULT_WALL_THEME_ID}'`, () => {
    // Both the migration fallback and the unknown-id fallback in the inline
    // script must be the DEFAULT_WALL_THEME_ID literal.
    expect(layout).toContain(`:'${DEFAULT_WALL_THEME_ID}'`.toLowerCase())
    expect(layout).toContain(`id='${DEFAULT_WALL_THEME_ID}'`.toLowerCase())
  })
})
