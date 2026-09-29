/**
 * Box emits its responsive rules as a React 19 hoistable stylesheet.
 *
 * Regression test for a real defect: the rules used to render as a bare inline
 * `<style>` sibling of the element. `<style>` is not a permitted child of
 * `<ul>`/`<ol>`/`<tbody>`, so wherever a responsive Box rendered inside a list
 * - which the news wall does (`NewsCardList` renders `<Box as="li">` inside
 * `<Box as="ol">`) - the HTML parser relocated or dropped the tag and
 * hydration then mismatched against the server markup.
 *
 * `href` + `precedence` opt into React's stylesheet hoisting: the tag moves to
 * `<head>` and is deduplicated by `href`.
 *
 * StyleX is stubbed because its real API is compiled away by
 * `@stylexjs/babel-plugin`, which vitest's esbuild transform does not run -
 * `stylex.defineVars` throws at runtime. This test asserts the JSX contract
 * Box is responsible for, not StyleX's own behaviour.
 */
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@stylexjs/stylex', () => {
  const passthrough = (...args: unknown[]) => args
  return {
    default: {
      defineVars: (o: Record<string, unknown>) => o,
      defineConsts: (o: Record<string, unknown>) => o,
      create: (o: Record<string, unknown>) => o,
      props: () => ({ className: 'sx', style: {} }),
      keyframes: passthrough,
    },
    defineVars: (o: Record<string, unknown>) => o,
    defineConsts: (o: Record<string, unknown>) => o,
    create: (o: Record<string, unknown>) => o,
    props: () => ({ className: 'sx', style: {} }),
    keyframes: passthrough,
  }
})

const { Box } = await import('./Box')

describe('Box responsive style hoisting', () => {
  it('marks the style tag hoistable rather than emitting it inline', () => {
    const html = renderToStaticMarkup(
      <Box padding={{ base: 'l', md: '2xl' }}>content</Box>,
    )
    // A hoistable <style> carries href + precedence; React lifts it to <head>
    // instead of leaving it beside the element.
    expect(html).toMatch(/<style[^>]*\bhref=/)
    expect(html).toMatch(/<style[^>]*\bprecedence=/)
  })

  it('does not leave a <style> as a direct child of a list', () => {
    const html = renderToStaticMarkup(
      <Box as="ol">
        <Box as="li" padding={{ base: 'l', md: '2xl' }}>
          headline
        </Box>
      </Box>,
    )
    // The invalid nesting this test exists to prevent.
    expect(html).not.toMatch(/<ol[^>]*>\s*<style/)
    expect(html).not.toMatch(/<li[^>]*>\s*<style/)
  })

  it('emits no style tag when no prop is responsive', () => {
    const html = renderToStaticMarkup(<Box padding="l">content</Box>)
    expect(html).not.toContain('<style')
  })
})
