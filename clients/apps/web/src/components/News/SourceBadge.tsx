const prefixOf = (id: string) => id.split('-')[0]

/** The card/roster badge: a real logo/crest (resolved server-side), else the
 * bundled per-source icon, else nothing but the transparent box. An `<img>`
 * with an error-fallback chain - a dead remote URL degrades to the local
 * icon instead of an invisible square (the failure mode that hid "working"
 * logos whenever an icon host changed behaviour). */
export const SourceBadge = ({
  id,
  logo,
  size = 32,
}: {
  id: string
  /** Accepted for call-site convenience but intentionally unused: the badge is
   * `aria-hidden`, so a label on it is inert - the wrapping link supplies the
   * accessible name. */
  name?: string
  logo?: string | null
  size?: number
}) => {
  const local = `/news-icons/${prefixOf(id)}.png`
  return (
    // Not next/image: these are third-party logos from ~15 hosts, swapped for a
    // bundled fallback by onError below. Routing them through the optimizer
    // would mean allowlisting every host and proxying an image we may discard.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      aria-hidden
      alt=""
      src={logo ?? local}
      width={size}
      height={size}
      loading="lazy"
      style={{
        display: 'inline-block',
        height: size,
        width: size,
        flexShrink: 0,
        objectFit: 'contain',
      }}
      onError={(e) => {
        const img = e.currentTarget
        if (img.src.endsWith(local)) {
          img.style.visibility = 'hidden'
        } else {
          img.src = local
        }
      }}
    />
  )
}
