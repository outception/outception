import { useId } from 'react'
import { twMerge } from 'tailwind-merge'

// Outception mark: the totem, traced from the founder's drawing. The
// silhouette (TOP_PATH, through the tenth-scale, flipped transform the
// earlier mark used) is a clip, painted as two flat halves in the edition's
// brand ramp (design tokens --color-brand-* in globals.css), the right one
// darker, with a hairline outline for weight at small sizes. The trace is
// reduced to the points that move its edge by more than 0.15 viewBox units,
// well under a pixel at the largest size the mark is drawn.
const TOP_PATH =
  'M5120 6080 5177 6070 5210 6050 5234 6030 5251 6010 5262 5990 5268 5970 5274 5930 5284 5770 5307 5490 5316 5330 5375 4530 5394 4410 5413 4330 5426 4290 5454 4210 5471 4170 5490 4130 5534 4050 5558 4010 5612 3930 5677 3850 5714 3810 5754 3770 5849 3690 5905 3650 5969 3610 6043 3570 6133 3530 6252 3490 6622 3410 6763 3370 6864 3330 6938 3290 6991 3250 7023 3210 7039 3170 7041 3130 7036 3100 7030 3085 7012 3055 6984 3025 6941 2995 6883 2965 6846 2950 6802 2935 6690 2905 6550 2875 6347 2836 6280 2826 6160 2799 5920 2754 5680 2721 5520 2705 5320 2693 5080 2689 4920 2693 4800 2699 4560 2721 4440 2736 4200 2775 3960 2826 3893 2836 3690 2875 3490 2920 3438 2935 3357 2965 3299 2995 3256 3025 3228 3055 3218 3070 3210 3085 3200 3115 3201 3170 3217 3210 3249 3250 3302 3290 3376 3330 3477 3370 3618 3410 3988 3490 4107 3530 4197 3570 4271 3610 4335 3650 4391 3690 4486 3770 4563 3850 4596 3890 4628 3930 4682 4010 4750 4130 4786 4210 4827 4330 4837 4370 4846 4410 4865 4530 4924 5330 4933 5490 4947 5650 4948 5690 4956 5770 4966 5930 4972 5970 4978 5990 4989 6010 5006 6030 5030 6050 5063 6070ZM4441 2700 4695 2671 4780 2665 4950 2656 5120 2653 5290 2656 5460 2665 5545 2671 5799 2700 5562 2230 5473 2050 5447 1990 5417 1930 5375 1860 5354 1830 5320 1790 5254 1730 5200 1700 5120 1680 5040 1700 4986 1730 4920 1790 4886 1830 4865 1860 4823 1930 4793 1990 4767 2050 4678 2230Z'

const LogoIcon = ({
  className,
  size = 29,
}: {
  className?: string
  size?: number
}) => {
  const uid = useId()
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
        <clipPath id={clip}>
          <path transform="translate(0,768) scale(0.1,-0.1)" d={TOP_PATH} />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clip})`}>
        {/* Two flat halves, split down the middle, the right one darker:
            the drawing's own shading, nothing soft. */}
        <rect
          x="288"
          y="160"
          width="224"
          height="448"
          style={{ fill: 'var(--color-brand-500)' }}
        />
        <rect
          x="512"
          y="160"
          width="224"
          height="448"
          style={{ fill: 'var(--color-brand-700)' }}
        />
      </g>
    </svg>
  )
}

export default LogoIcon
