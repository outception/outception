import { useId } from 'react'
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
// silhouette clip painted with the brand-green ramp (the web Phosphor edition's
// --color-brand-* tokens; phosphor green #1FE266 at the core), a darker
// underside tail, and two thin "equator" seams. Fixed-colour gradient.
const STAR_PATH =
  'M5059 5751 c-93 -30 -117 -61 -228 -285 -158 -319 -317 -543 -555 -782 -255 -255 -523 -440 -866 -597 -113 -52 -151 -81 -181 -139 -44 -87 -33 -186 29 -258 28 -33 68 -57 196 -119 336 -161 579 -332 826 -580 236 -237 396 -462 552 -778 80 -163 108 -210 140 -237 83 -71 213 -71 296 0 32 27 60 74 140 237 156 314 317 542 552 778 246 247 485 416 816 575 137 66 178 91 206 124 78 91 74 223 -10 313 -14 15 -116 72 -226 126 -319 158 -544 317 -782 555 -236 236 -397 463 -552 775 -105 212 -125 242 -185 272 -44 23 -128 33 -168 20z'

const LogoIcon = ({ size = 24 }: { size?: number }) => {
  const uid = useId()
  const dome = `dome-${uid}`
  const tail = `tail-${uid}`
  const clip = `star-${uid}`
  return (
    <Svg width={size} height={size} viewBox="288 160 448 448" fill="none">
      <Defs>
        <RadialGradient id={dome} cx="0.5" cy="0.28" r="0.5">
          <Stop offset="0" stopColor="#99ffbe" />
          <Stop offset="0.32" stopColor="#1fe266" />
          <Stop offset="0.75" stopColor="#12bd51" />
          <Stop offset="1" stopColor="#0d953f" />
        </RadialGradient>
        <LinearGradient
          id={tail}
          x1="0"
          y1="384"
          x2="0"
          y2="578"
          gradientUnits="userSpaceOnUse"
        >
          <Stop offset="0" stopColor="#086e2e" />
          <Stop offset="0.30" stopColor="#0d953f" />
          <Stop offset="1" stopColor="#66ff99" />
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
          stroke="#054a1f"
          strokeWidth="4"
          fill="none"
          opacity="0.45"
        />
        <Path
          d="M330 380 Q512 426 694 380"
          stroke="#c8ffdc"
          strokeWidth="3"
          fill="none"
          opacity="0.55"
        />
      </G>
    </Svg>
  )
}

export default LogoIcon
