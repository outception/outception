import {
  getEditionSnapshot,
  subscribeEdition,
} from '@/design-system/themeStore'
import { useId, useSyncExternalStore } from 'react'
import {
  ClipPath,
  Defs,
  G,
  LinearGradient,
  Path,
  RadialGradient,
  Rect,
  Stop,
  Svg,
} from 'react-native-svg'

// Outception sparkle mark — matches the web LogoIcon / favicon: a crisp star
// silhouette clip painted with the ACTIVE edition's brand ramp (the web
// --color-brand-* tokens), a darker underside tail, and two thin "equator"
// seams. The gem recolors with the edition (logo tap), like the web.
const STAR_PATH =
  'M5059 5751 c-93 -30 -117 -61 -228 -285 -158 -319 -317 -543 -555 -782 -255 -255 -523 -440 -866 -597 -113 -52 -151 -81 -181 -139 -44 -87 -33 -186 29 -258 28 -33 68 -57 196 -119 336 -161 579 -332 826 -580 236 -237 396 -462 552 -778 80 -163 108 -210 140 -237 83 -71 213 -71 296 0 32 27 60 74 140 237 156 314 317 542 552 778 246 247 485 416 816 575 137 66 178 91 206 124 78 91 74 223 -10 313 -14 15 -116 72 -226 126 -319 158 -544 317 -782 555 -236 236 -397 463 -552 775 -105 212 -125 242 -185 272 -44 23 -128 33 -168 20z'

// Each edition's brand ramp [100…900] (mirrors --color-brand-* in globals.css).
export const BRAND_RAMPS: Record<string, readonly string[]> = {
  // Mirrors the web's ruby edition --color-brand-100…900 (globals.css) — the
  // DEFAULT edition; missing here, every default-theme user got the phosphor
  // (green) fallback instead of the red mark.
  ruby: [
    '#ffd7da',
    '#ffadb4',
    '#ff8290',
    '#f8505f',
    '#e81c2e',
    '#c11322',
    '#98101c',
    '#700c15',
    '#4a080e',
  ],
  midnight: [
    '#d7e6ef',
    '#c1d7e5',
    '#aac7d9',
    '#8fb3c9',
    '#74a0b9',
    '#57869f',
    '#416b81',
    '#305264',
    '#223c49',
  ],
  tide: [
    '#c9ecf9',
    '#a3ddf3',
    '#6ec7e9',
    '#45b4e0',
    '#21a1d6',
    '#1585b4',
    '#0f6a91',
    '#0a506e',
    '#073a50',
  ],
  neon: [
    '#ffd1e9',
    '#ffadd8',
    '#ff8ac7',
    '#ff61b2',
    '#ff2f98',
    '#d61d7c',
    '#ab1662',
    '#7f104a',
    '#570b33',
  ],
  dune: [
    '#ffedd3',
    '#ffe0b6',
    '#ffd59d',
    '#f2bc74',
    '#dfa053',
    '#c08138',
    '#9c6527',
    '#784c1c',
    '#553413',
  ],
  phosphor: [
    '#c8ffdc',
    '#99ffbe',
    '#66ff99',
    '#3df57e',
    '#1fe266',
    '#12bd51',
    '#0d953f',
    '#086e2e',
    '#054a1f',
  ],
}

const LogoIcon = ({ size = 24 }: { size?: number }) => {
  const uid = useId()
  const dome = `dome-${uid}`
  const tail = `tail-${uid}`
  const clip = `star-${uid}`
  const edition = useSyncExternalStore(
    subscribeEdition,
    getEditionSnapshot,
    getEditionSnapshot,
  )
  // r[i]: 0=brand-100 … 8=brand-900.
  const r = BRAND_RAMPS[edition] ?? BRAND_RAMPS.ruby
  return (
    <Svg width={size} height={size} viewBox="288 160 448 448" fill="none">
      <Defs>
        <RadialGradient id={dome} cx="0.5" cy="0.28" r="0.5">
          <Stop offset="0" stopColor={r[1]} />
          <Stop offset="0.32" stopColor={r[4]} />
          <Stop offset="0.75" stopColor={r[5]} />
          <Stop offset="1" stopColor={r[6]} />
        </RadialGradient>
        <LinearGradient
          id={tail}
          x1="0"
          y1="384"
          x2="0"
          y2="578"
          gradientUnits="userSpaceOnUse"
        >
          <Stop offset="0" stopColor={r[7]} />
          <Stop offset="0.30" stopColor={r[6]} />
          <Stop offset="1" stopColor={r[2]} />
        </LinearGradient>
        <ClipPath id={clip}>
          <Path transform="translate(0,768) scale(0.1,-0.1)" d={STAR_PATH} />
        </ClipPath>
      </Defs>
      <G clipPath={`url(#${clip})`}>
        <Rect x="288" y="160" width="448" height="448" fill={`url(#${dome})`} />
        <Path
          d="M296 374 Q512 450 728 374 L728 624 L296 624 Z"
          fill={`url(#${tail})`}
        />
        <Path
          d="M322 384 Q512 436 702 384"
          stroke={r[8]}
          strokeWidth="4"
          fill="none"
          opacity="0.45"
        />
        <Path
          d="M330 380 Q512 426 694 380"
          stroke={r[0]}
          strokeWidth="3"
          fill="none"
          opacity="0.55"
        />
      </G>
    </Svg>
  )
}

export default LogoIcon
