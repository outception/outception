const prefixOf = (id: string) => id.split('-')[0]

/** The card/roster badge: a real logo/crest (for entity feeds resolved from
 * Wikipedia), else the source's own favicon / category icon from
 * `/news-icons/{prefix}.png`. The image is shown in full via `contain` on a
 * fully transparent background — no circular mask and no white plate — so each
 * logo keeps its own shape and colour. */
export const SourceBadge = ({
  id,
  logo,
  size = 32,
}: {
  id: string
  /** Accepted for call-site convenience but intentionally unused: the badge is
   * `aria-hidden`, so a label on it is inert — the wrapping link supplies the
   * accessible name. */
  name?: string
  logo?: string | null
  size?: number
}) => {
  const src = logo ?? `/news-icons/${prefixOf(id)}.png`
  return (
    <span
      aria-hidden
      style={{
        display: 'inline-block',
        boxSizing: 'border-box',
        height: size,
        width: size,
        flexShrink: 0,
        backgroundColor: 'transparent',
        backgroundImage: `url(${src})`,
        backgroundSize: 'contain',
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'center',
      }}
    />
  )
}
