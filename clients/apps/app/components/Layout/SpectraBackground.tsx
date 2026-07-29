import {
  getEditionSnapshot,
  subscribeEdition,
} from '@/design-system/themeStore'
import { useTone } from '@/design-system/toneStore'
import { useSyncExternalStore } from 'react'
import { Dimensions, StyleSheet, useWindowDimensions } from 'react-native'
import { Box } from '@/components/Shared/Box'
import Svg, {
  Defs,
  Image as SvgImage,
  LinearGradient,
  Pattern,
  RadialGradient,
  Rect,
  Stop,
} from 'react-native-svg'

// Per-edition page gradients, mirroring the web wall's `--page-gradient` for
// each theme in globals.css. Linear editions run the web's 135deg angle with
// CSS's exact endpoint geometry; radial editions use the web's `circle at
// cx% cy%` anchor and extend to the farthest corner (CSS default). The active edition is
// logo-cycled + persisted (themeStore); the OS setting picks light/dark tone -
// exactly like the web repainting the whole page per edition.
type Stops = readonly [number, string][]
type Gradient =
  | { kind: 'linear'; stops: Stops }
  | { kind: 'radial'; cx: number; cy: number; stops: Stops }

const GRADIENTS: Record<string, { light: Gradient; dark: Gradient }> = {
  midnight: {
    light: {
      kind: 'linear',
      stops: [
        [0, '#f7fafc'],
        [0.55, '#e9eef4'],
        [1, '#c6d2dd'],
      ],
    },
    dark: {
      kind: 'linear',
      stops: [
        [0, '#2a3039'],
        [0.52, '#101413'],
        [1, '#06080b'],
      ],
    },
  },
  tide: {
    light: {
      kind: 'radial',
      cx: 0.28,
      cy: 0.24,
      stops: [
        [0, '#eaf7fe'],
        [0.42, '#b9e3f7'],
        [1, '#5da8cf'],
      ],
    },
    dark: {
      kind: 'radial',
      cx: 0.28,
      cy: 0.24,
      stops: [
        [0, '#6ec7e9'],
        [0.42, '#0b8edc'],
        [1, '#063d61'],
      ],
    },
  },
  neon: {
    light: {
      kind: 'radial',
      cx: 0.3,
      cy: 0.24,
      stops: [
        [0, '#fdf0f8'],
        [0.44, '#f7cfe6'],
        [1, '#d891bd'],
      ],
    },
    dark: {
      kind: 'radial',
      cx: 0.3,
      cy: 0.24,
      stops: [
        [0, '#ff61b2'],
        [0.44, '#ff2f98'],
        [1, '#25101f'],
      ],
    },
  },
  dune: {
    light: {
      kind: 'linear',
      stops: [
        [0, '#fff3e2'],
        [0.42, '#e9c199'],
        [1, '#94532f'],
      ],
    },
    dark: {
      kind: 'linear',
      stops: [
        [0, '#3a2a1d'],
        [0.52, '#221510'],
        [1, '#120a06'],
      ],
    },
  },
  phosphor: {
    light: {
      kind: 'radial',
      cx: 0.32,
      cy: 0.2,
      stops: [
        [0, '#edfbf2'],
        [0.5, '#c4ecd4'],
        [1, '#7cc697'],
      ],
    },
    dark: {
      kind: 'radial',
      cx: 0.32,
      cy: 0.2,
      stops: [
        [0, '#062414'],
        [0.56, '#020403'],
        [1, '#000201'],
      ],
    },
  },
  ruby: {
    light: {
      kind: 'radial',
      cx: 0.32,
      cy: 0.2,
      stops: [
        [0, '#faf9f4'],
        [0.5, '#f0eee4'],
        [1, '#cfc9b8'],
      ],
    },
    dark: {
      kind: 'radial',
      cx: 0.32,
      cy: 0.2,
      stops: [
        [0, '#5c0a12'],
        [0.56, '#1a0407'],
        [1, '#0a0102'],
      ],
    },
  },
}

const farthestCorner = (cx: number, cy: number, w: number, h: number) =>
  Math.max(
    Math.hypot(cx, cy),
    Math.hypot(w - cx, cy),
    Math.hypot(cx, h - cy),
    Math.hypot(w - cx, h - cy),
  )

/** Full-screen paper backdrop mirroring the web wall: the active edition's page
 * gradient plus a grainy tooth. Repaints when the edition (logo tap) or OS tone
 * changes. Behind all content; ignores touches. */
export function SpectraBackground() {
  // Screen, not window: on Android the window excludes the status/navigation
  // bars, so sizing the SVG to it leaves an unpainted band at the bottom of
  // this absolutely-filled container. Overscan a little so rotation or an
  // inset change can never expose an edge.
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
  const set = GRADIENTS[edition] ?? GRADIENTS.phosphor
  const grad = tone === 'dark' ? set.dark : set.light

  return (
    <Box style={StyleSheet.absoluteFill} pointerEvents="none">
      <Svg width={w} height={h}>
        <Defs>
          {grad.kind === 'linear' ? (
            // CSS `linear-gradient(135deg)` keeps its 45° iso-color lines on
            // ANY aspect ratio - its axis endpoints are the corner projections,
            // not the corners themselves. Corner-to-corner (the old approach)
            // matches only on a square; on a tall phone it skewed the wash so
            // the right half collapsed to the darkest stop.
            <LinearGradient
              id="wallWash"
              x1={(w - h) / 4}
              y1={(h - w) / 4}
              x2={(3 * w + h) / 4}
              y2={(3 * h + w) / 4}
              gradientUnits="userSpaceOnUse"
            >
              {grad.stops.map(([offset, color]) => (
                <Stop key={color} offset={offset} stopColor={color} />
              ))}
            </LinearGradient>
          ) : (
            <RadialGradient
              id="wallWash"
              cx={grad.cx * w}
              cy={grad.cy * h}
              r={farthestCorner(grad.cx * w, grad.cy * h, w, h)}
              gradientUnits="userSpaceOnUse"
            >
              {grad.stops.map(([offset, color]) => (
                <Stop key={color} offset={offset} stopColor={color} />
              ))}
            </RadialGradient>
          )}
          {/* Grainy paper tooth, mirroring the web wall: the balanced
              transparent speckle tiled over the wash - no color shift, just
              texture. Tiled as an SVG pattern because RN Image's
              resizeMode="repeat" silently paints the tile ONCE on the new
              Android architecture, leaving a visible 256dp square in the
              top-left corner and bare gradient everywhere else. */}
          <Pattern
            id="tooth"
            x={0}
            y={0}
            width={256}
            height={256}
            patternUnits="userSpaceOnUse"
          >
            <SvgImage
              href={require('../../assets/images/grain.png')}
              x={0}
              y={0}
              width={256}
              height={256}
            />
          </Pattern>
        </Defs>
        <Rect x={0} y={0} width={w} height={h} fill="url(#wallWash)" />
        <Rect x={0} y={0} width={w} height={h} fill="url(#tooth)" />
      </Svg>
    </Box>
  )
}
