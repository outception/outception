'use client'

import { usePromotedSlot } from '@/hooks/queries/promoted'
import { useT } from '@/providers/locale'
import { safeExternalHref } from '@/utils/news'
import { Button } from '@outception-com/orbit/Button'
import { Text } from '@outception-com/orbit/Text'
import { Box } from '@outception-com/orbit/Box'
import { useEffect, useRef, useState } from 'react'

/** The wall's one sponsored card: the active Promoted run's ad video with a
 * clear "Promoted" kicker, in the same paper-sheet idiom as every other card.
 * At most one of these ever exists in a card set (the wall splices it in only
 * while a run is active). The video starts muted and looping like any feed
 * video; tapping it toggles sound. Playback pauses whenever the card isn't
 * the front sheet, mirroring how game cards pause off the top. */
export const PromotedCard = ({ active = false }: { active?: boolean }) => {
  const t = useT()
  const { data: slot } = usePromotedSlot()
  const videoRef = useRef<HTMLVideoElement>(null)
  const [muted, setMuted] = useState(true)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    if (active) {
      // Autoplay can be denied (browser policy) - muted playback never is,
      // but the promise still wants handling so a denial stays silent.
      video.play().catch(() => {})
    } else {
      video.pause()
    }
  }, [active])

  if (!slot) return null

  const videoSrc = safeExternalHref(slot.videoUrl)
  const clickHref = safeExternalHref(slot.clickUrl)

  return (
    <Box
      flexDirection="column"
      rowGap="m"
      height="100%"
      padding={{ base: 'l', md: 'xl' }}
    >
      <Box
        flexDirection="row"
        alignItems="center"
        justifyContent="between"
        columnGap="s"
      >
        <Box flexDirection="column" rowGap="none" minWidth={0}>
          <Text variant="body" as="h3" serif truncate>
            {slot.businessName}
          </Text>
          <span className="meta-kicker">{t('news.promoted.kicker')}</span>
        </Box>
        {clickHref && (
          <a href={clickHref} target="_blank" rel="noreferrer sponsored">
            <Button variant="secondary" size="sm">
              {t('news.promoted.visit')}
            </Button>
          </a>
        )}
      </Box>
      <Box
        flexGrow={1}
        minHeight={0}
        borderRadius="m"
        overflow="hidden"
        backgroundColor="background-secondary"
        position="relative"
      >
        {videoSrc && (
          <video
            ref={videoRef}
            src={videoSrc}
            muted={muted}
            loop
            playsInline
            autoPlay={active}
            onClick={() => setMuted((m) => !m)}
            aria-label={t('news.promoted.toggleSound')}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              cursor: 'pointer',
            }}
          />
        )}
      </Box>
      {slot.tagline && (
        <Text variant="caption" color="muted" truncate>
          {slot.tagline}
        </Text>
      )}
    </Box>
  )
}
