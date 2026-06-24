import { twMerge } from 'tailwind-merge'

/**
 * Text wordmark used in place of the (removed) Polar logo graphics. Renders the
 * brand name as styled text — no SVG asset, no right-click "copy brand asset"
 * behavior.
 */
export const Wordmark = ({
  className,
  size,
}: {
  className?: string
  size?: number
}) => (
  <span
    className={twMerge(
      'font-semibold tracking-tight whitespace-nowrap',
      className,
    )}
    style={{ fontSize: size ? Math.round(size * 0.42) : 22, lineHeight: 1 }}
  >
    Outception
  </span>
)

export default Wordmark
