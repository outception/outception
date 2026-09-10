import { Box } from '@/components/Shared/Box'
import { EDITIONS, DEFAULT_EDITION_ID } from '@/design-system/editions'
import {
  getEditionSnapshot,
  subscribeEdition,
} from '@/design-system/themeStore'
import { useTone } from '@/design-system/toneStore'
import { useSyncExternalStore } from 'react'
import { Dimensions, StyleSheet, useWindowDimensions } from 'react-native'
import Svg, { Defs, Path, Pattern, Rect } from 'react-native-svg'

// Grain tile, built once at module scope from a fixed seed so it is identical
// on every launch (a tile that reshuffled would shimmer whenever this
// remounted).
//
// Generated rather than shipped as a PNG: no asset to download or keep in the
// bundle, and no dependency on the SVG filter primitives, which
// react-native-svg has in its source but does not export.
const TILE = 48
const CELLS = TILE * TILE

// The alpha of one 1dp speck, as sixteen equal-population buckets.
//
// These are not tuned by eye. They are the web backdrop's own noise, measured:
// a screenshot of outception.com was sampled over two clean patches of empty
// page, each pixel converted back to the alpha that would produce it over the
// page colour, and the resulting distribution cut into sixteen buckets of
// equal population. Bucket 0 comes out at alpha 0 - bare page - and is simply
// not drawn, which is why there are fifteen entries for sixteen buckets.
//
// Reproducing the SHAPE is the point. An earlier tile matched the web on
// overall strength but spent it on a few hard dots: 12% of pixels lifted by
// about 13 levels each, against the web's 90% lifted by about 8. Same average,
// completely different surface - the phone read as flat black with dust on it
// while the web read as an evenly textured page.
const LEVELS = [
  0.0014, 0.0057, 0.0086, 0.0135, 0.0172, 0.0202, 0.0249, 0.0276, 0.031, 0.0366,
  0.0408, 0.0465, 0.0545, 0.0648, 0.0884,
] as const
/** Buckets that draw nothing. Kept explicit so the split stays exact. */
const BARE = 1
const BUCKETS = LEVELS.length + BARE

// The web paints the grain at opacity 0.36 on the light page and 0.42 on the
// dark one. The levels above were measured off the dark page, so the light
// tone carries that same ratio rather than a second set of numbers.
const LIGHT_SCALE = 0.36 / 0.42

/**
 * One path per alpha level, each the union of every 1dp square at that level.
 *
 * Fifteen paths rather than ~2160 rects: react-native-svg turns each element
 * into a native node, and the tile needs near-total coverage to look like the
 * web. Grouping by level keeps the node count flat while the square count
 * grows.
 */
const grainPaths = ((): string[] => {
  let seed = 0x9e3779b9
  const next = (): number => {
    // xorshift32 - small, fast, and stable across platforms. Divided by 2^32
    // rather than 2^32-1 so the result can never reach exactly 1 and push a
    // shuffle index out of range.
    seed ^= seed << 13
    seed ^= seed >>> 17
    seed ^= seed << 5
    return (seed >>> 0) / 0x100000000
  }
  // Deal every cell a bucket, exactly CELLS/BUCKETS of each, then shuffle.
  // Dealing and shuffling rather than sampling per cell makes the tile's
  // distribution exactly the measured one instead of an approximation of it.
  const ids = new Uint8Array(CELLS)
  for (let i = 0; i < CELLS; i += 1) ids[i] = i % BUCKETS
  for (let i = CELLS - 1; i > 0; i -= 1) {
    const j = Math.floor(next() * (i + 1))
    const swap = ids[i]!
    ids[i] = ids[j]!
    ids[j] = swap
  }
  const parts: string[][] = LEVELS.map(() => [])
  for (let i = 0; i < CELLS; i += 1) {
    const bucket = ids[i]!
    if (bucket < BARE) continue
    parts[bucket - BARE]!.push(`M${i % TILE} ${(i / TILE) | 0}h1v1h-1z`)
  }
  return parts.map((p) => p.join(''))
})()

/**
 * The wall's backdrop: one solid colour per edition, with a fine grain over
 * it and nothing else.
 *
 * There is deliberately no wash, no gradient and no paper texture. The page is
 * a single flat colour so the reading surface stays completely even behind the
 * cards, and the grain is the only relief. That also makes this the cheapest
 * layer on screen - one rect plus one tiled pattern, no per-frame work - on a
 * view that sits under every swipe.
 */
export const SpectraBackground = () => {
  // Cover the whole screen, not just the window: the status/nav bars are
  // outside the window on Android, and a rotation or inset change must never
  // expose an edge of this absolutely-filled container.
  const win = useWindowDimensions()
  const screen = Dimensions.get('screen')
  const w = Math.max(win.width, screen.width)
  const h = Math.max(win.height, screen.height)
  const tone = useTone()
  const edition = useSyncExternalStore(
    subscribeEdition,
    getEditionSnapshot,
    getEditionSnapshot,
  )
  const set =
    EDITIONS.find((e) => e.id === edition) ??
    EDITIONS.find((e) => e.id === DEFAULT_EDITION_ID)!
  const dark = tone === 'dark'
  const page = dark ? set.dark.bg : set.light.bg
  // Like the web: the dark page is lifted by white specks and the light page
  // is cut by black ones. Mixing both on one page cancels half the grain out.
  const speck = dark ? '#ffffff' : '#000000'
  const scale = dark ? 1 : LIGHT_SCALE

  return (
    <Box style={StyleSheet.absoluteFill} pointerEvents="none">
      <Svg width={w} height={h}>
        <Defs>
          {/* Tiled as an SVG pattern rather than a repeating Image: on the new
              Android architecture RN's resizeMode="repeat" silently paints the
              tile ONCE, leaving one tile in the corner and bare colour
              everywhere else. The pattern is rasterised once and reused, so
              the square count costs nothing per frame. */}
          <Pattern
            id="grain"
            x={0}
            y={0}
            width={TILE}
            height={TILE}
            patternUnits="userSpaceOnUse"
          >
            {grainPaths.map((d, i) => (
              <Path
                key={LEVELS[i]}
                d={d}
                fill={speck}
                fillOpacity={LEVELS[i]! * scale}
              />
            ))}
          </Pattern>
        </Defs>
        <Rect x={0} y={0} width={w} height={h} fill={page} />
        <Rect x={0} y={0} width={w} height={h} fill="url(#grain)" />
      </Svg>
    </Box>
  )
}
