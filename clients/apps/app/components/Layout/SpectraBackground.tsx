import { StyleSheet, useColorScheme, useWindowDimensions } from 'react-native'
import { Box } from '@/components/Shared/Box'
import Svg, {
  Defs,
  Mask,
  Path,
  Pattern,
  RadialGradient,
  Rect,
  Stop,
} from 'react-native-svg'

// Uniform square grid (px). The "concentration" is done with a radial alpha
// mask, so the lines read as a glow near the anchor and fade toward the edges.
const CELL = 60
const ANCHOR_X = 0.5
// A fixed distance down from the top — roughly the header/logo line — so a grid
// cell is centred there (the logo sits in the middle of a square), matching web.
const ANCHOR_TOP_PX = 90
const FADE_RADIUS_FRAC = 0.9

// Two outfits, mirroring the web app. Light: bright brand yellow on a warm
// cream→peach wash. Dark: muted golden amber on a warm near-black wash.
const LIGHT = {
  grid: '#f0b429',
  gridOpacity: 0.28,
  warmInner: '#fbe7d2',
  warmOuter: '#fdfaf4',
}
const DARK = {
  grid: '#caa12e',
  gridOpacity: 0.2,
  warmInner: '#1b1714',
  warmOuter: '#0d0e10',
}

/** Full-screen living background ported from the web app: a line grid (dub-style
 * squares) phased so a cell is centred near the top-centre, with a radial fade
 * and a warm wash. Follows the system theme (light/dark) like the web. Sits
 * behind all content; ignores touches. */
export function SpectraBackground() {
  const { width: w, height: h } = useWindowDimensions()
  const scheme = useColorScheme()
  const c = scheme === 'dark' ? DARK : LIGHT

  const ax = w * ANCHOR_X
  const ay = ANCHOR_TOP_PX
  // Phase the pattern so a cell is CENTRED on the anchor (edges at ax ± CELL/2).
  const px = ax - CELL / 2
  const py = ay - CELL / 2
  const fade = FADE_RADIUS_FRAC * Math.min(w, h)
  const warm = Math.max(w, h) * 0.9

  return (
    <Box style={StyleSheet.absoluteFill} pointerEvents="none">
      <Svg width={w} height={h}>
        <Defs>
          <Pattern
            id="spectraGrid"
            x={px}
            y={py}
            width={CELL}
            height={CELL}
            patternUnits="userSpaceOnUse"
          >
            <Path
              d={`M ${CELL} 0 L 0 0 0 ${CELL}`}
              stroke={c.grid}
              strokeWidth={1}
              fill="none"
            />
          </Pattern>
          <RadialGradient
            id="spectraFade"
            cx={ax}
            cy={ay}
            r={fade}
            gradientUnits="userSpaceOnUse"
          >
            <Stop offset="0" stopColor="#ffffff" stopOpacity={1} />
            <Stop offset="0.5" stopColor="#ffffff" stopOpacity={0.6} />
            <Stop offset="1" stopColor="#ffffff" stopOpacity={0} />
          </RadialGradient>
          <Mask id="spectraMask">
            <Rect x={0} y={0} width={w} height={h} fill="url(#spectraFade)" />
          </Mask>
          <RadialGradient
            id="spectraWarm"
            cx={ax}
            cy={ay}
            r={warm}
            gradientUnits="userSpaceOnUse"
          >
            <Stop offset="0" stopColor={c.warmInner} stopOpacity={0.9} />
            <Stop offset="1" stopColor={c.warmOuter} stopOpacity={0} />
          </RadialGradient>
        </Defs>
        {/* warm wash radiating from the anchor */}
        <Rect x={0} y={0} width={w} height={h} fill="url(#spectraWarm)" />
        {/* grid, faded by the radial mask */}
        <Rect
          x={0}
          y={0}
          width={w}
          height={h}
          fill="url(#spectraGrid)"
          opacity={c.gridOpacity}
          mask="url(#spectraMask)"
        />
      </Svg>
    </Box>
  )
}
