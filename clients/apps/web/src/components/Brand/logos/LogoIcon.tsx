import { useId } from 'react'
import { twMerge } from 'tailwind-merge'

// Outception sparkle mark. Clean vector reconstruction of the 3D artwork: the
// crisp geometric star silhouette (STAR_PATH, drawn via its source group
// transform) is used as a clip, then painted with smooth gradients —
// a radial dome, a darker underside tail, and a crisp "equator" seam. Fully
// scalable, no raster artifacts, no black, no drop shadow.
const STAR_PATH =
  'M5059 5751 c-93 -30 -117 -61 -228 -285 -158 -319 -317 -543 -555 -782 -255 -255 -523 -440 -866 -597 -113 -52 -151 -81 -181 -139 -44 -87 -33 -186 29 -258 28 -33 68 -57 196 -119 336 -161 579 -332 826 -580 236 -237 396 -462 552 -778 80 -163 108 -210 140 -237 83 -71 213 -71 296 0 32 27 60 74 140 237 156 314 317 542 552 778 246 247 485 416 816 575 137 66 178 91 206 124 78 91 74 223 -10 313 -14 15 -116 72 -226 126 -319 158 -544 317 -782 555 -236 236 -397 463 -552 775 -105 212 -125 242 -185 272 -44 23 -128 33 -168 20z'

const LogoIcon = ({
  className,
  size = 29,
}: {
  className?: string
  size?: number
}) => {
  const uid = useId()
  const dome = `dome-${uid}`
  const tail = `tail-${uid}`
  const clip = `star-${uid}`
  return (
    <svg
      width={size}
      height={size}
      viewBox="288 160 448 448"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={twMerge(className ? className : '')}
    >
      <defs>
        <radialGradient id={dome} cx="0.5" cy="0.30" r="0.85">
          <stop offset="0" stopColor="#FF564B" />
          <stop offset="0.45" stopColor="#FF160C" />
          <stop offset="0.85" stopColor="#F00000" />
          <stop offset="1" stopColor="#D60000" />
        </radialGradient>
        <linearGradient
          id={tail}
          x1="0"
          y1="384"
          x2="0"
          y2="578"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0" stopColor="#9C0000" />
          <stop offset="0.30" stopColor="#BE0000" />
          <stop offset="1" stopColor="#FF332B" />
        </linearGradient>
        <clipPath id={clip}>
          <path
            transform="translate(0,768) scale(0.1,-0.1)"
            d={STAR_PATH}
          />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clip})`}>
        <rect
          x="288"
          y="160"
          width="448"
          height="448"
          fill={`url(#${dome})`}
        />
        <path
          d="M296 374 Q512 450 728 374 L728 624 L296 624 Z"
          fill={`url(#${tail})`}
        />
        <path
          d="M322 384 Q512 436 702 384"
          stroke="#7E0000"
          strokeWidth="4"
          fill="none"
          opacity="0.45"
        />
        <path
          d="M330 380 Q512 426 694 380"
          stroke="#FF7A70"
          strokeWidth="3"
          fill="none"
          opacity="0.55"
        />
      </g>
    </svg>
  )
}

export default LogoIcon
