import { describe, expect, it } from 'vitest'
import { maskPlaceholders, restorePlaceholders } from './utils'

const roundTrip = (s: string, translate: (masked: string) => string) => {
  const { masked, tokens } = maskPlaceholders(s)
  return restorePlaceholders(translate(masked), tokens)
}

describe('maskPlaceholders', () => {
  it('hides quotes from the model so its reply stays valid JSON', () => {
    // The real failure: asked to translate this string, the model wrote plain
    // double quotes around the translated label. Unescaped inside a JSON
    // string, that ends the string early and the whole reply fails to parse -
    // every time, so no retry helped. Masked, the model never sees a quote.
    const src = 'Your stack is empty. Open “Cards” to follow publications.'
    const { masked } = maskPlaceholders(src)
    expect(masked).not.toMatch(/["“”]/)
    expect(JSON.parse(JSON.stringify([masked]))[0]).toBe(masked)
  })

  it('restores the original quote characters after translation', () => {
    const src = 'Open “Cards” to follow publications.'
    // Stand in for the model: translate the words, keep the tokens.
    const out = roundTrip(src, (m) =>
      m.replace('Open', '打开').replace('Cards', '卡片'),
    )
    expect(out).toBe('打开 “卡片” to follow publications.')
  })

  it('still masks interpolations, and keeps them distinct from quotes', () => {
    const { masked, tokens } = maskPlaceholders('Added {count} to “Cards”')
    expect(masked).not.toContain('{count}')
    expect(tokens).toContain('{count}')
    expect(restorePlaceholders(masked, tokens)).toBe('Added {count} to “Cards”')
  })

  it('leaves a string with neither quotes nor placeholders untouched', () => {
    const { masked, tokens } = maskPlaceholders('Starter cards')
    expect(masked).toBe('Starter cards')
    expect(tokens).toEqual([])
  })
})
