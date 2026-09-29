import { twMerge } from 'tailwind-merge'

/**
 * Outception wordmark. SVG text (rather than a styled span) so the mark
 * scales with the height/width its consumers already pass via classes
 * like `h-5` / `h-10`, exactly as the previous path-based logo did.
 */
const LogoType = ({
  className,
  width,
  height,
}: {
  className?: string
  width?: number
  height?: number
}) => {
  return (
    <svg
      viewBox="0 0 118 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={twMerge(className ? className : '')}
      width={width}
      height={height}
    >
      <text
        x="0"
        y="18"
        fontFamily="Hanken Grotesk, Geist, system-ui, sans-serif"
        fontSize="19"
        fontWeight="600"
        letterSpacing="-0.4"
        fill="currentColor"
      >
        Outception
      </text>
    </svg>
  )
}

export default LogoType
