import { Box } from '@/components/Shared/Box'
import { Image } from '@/components/Shared/Image/Image'
import { sourceIconUrl } from '@/utils/news'
import { useState } from 'react'

/** The card/roster badge: a real logo/crest (for entity feeds resolved from
 * Wikipedia), else the source's own favicon / category icon from
 * `/news-icons/{prefix}.png`. The image is shown in full via `contain` on a
 * fully transparent background - no circular mask and no white plate - so each
 * logo keeps its own shape and colour. Error-fallback chain like the web
 * badge: a dead remote logo degrades to the bundled icon, and a dead bundled
 * icon to the bare transparent box (never a broken-image square). */
export const SourceBadge = ({
  id,
  name,
  logo,
  size = 32,
}: {
  id: string
  name?: string
  logo?: string | null
  size?: number
}) => {
  // Keyed by URI (not a step counter) so a recycled row with fresh props
  // retries its own images instead of inheriting the previous row's failures.
  const [failed, setFailed] = useState<ReadonlySet<string>>(new Set())
  const local = sourceIconUrl(id)
  const uri =
    logo && !failed.has(logo) ? logo : !failed.has(local) ? local : null
  return (
    <Box width={size} height={size} style={{ overflow: 'hidden' }}>
      {uri ? (
        <Image
          source={uri}
          // expo-image prop - RN's `resizeMode` is silently ignored, which left
          // the default `cover` cropping logos into edge-to-edge blobs.
          contentFit="contain"
          style={{ width: '100%', height: '100%' }}
          accessibilityLabel={name}
          onError={() => setFailed((prev) => new Set(prev).add(uri))}
        />
      ) : null}
    </Box>
  )
}
