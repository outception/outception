import { Box } from '@/components/Shared/Box'
import { Image } from '@/components/Shared/Image/Image'
import { sourceIconUrl } from '@/utils/news'

/** The card/roster badge: a real logo/crest (for entity feeds resolved from
 * Wikipedia), else the source's own favicon / category icon from
 * `/news-icons/{prefix}.png`. The image is shown in full via `contain` on a
 * fully transparent background — no circular mask and no white plate — so each
 * logo keeps its own shape and colour. */
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
  return (
    <Box width={size} height={size} style={{ overflow: 'hidden' }}>
      <Image
        source={logo ?? sourceIconUrl(id)}
        resizeMode="contain"
        style={{ width: '100%', height: '100%' }}
        accessibilityLabel={name}
      />
    </Box>
  )
}
