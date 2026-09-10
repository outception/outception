'use client'

import { useT } from '@/providers/locale'
import { safeExternalHref, type NewsSourceMeta } from '@/utils/news'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import { X } from 'lucide-react'
import { useEffect } from 'react'
import { FollowButton } from './FollowButton'
import { InlineSummary } from './InlineSummary'
import { ShareButton } from './ShareButton'
import { SourceBadge } from './SourceBadge'

/**
 * A mosaic tile brought to the middle of the screen.
 *
 * In the card view a headline expands its AI summary in place, under the row.
 * A mosaic tile has nowhere to expand into - at rest it is a thumbnail of
 * text - so the tile comes forward instead, and carries the things a card
 * carries: the source's mark, accent and name, share, unfollow, the headline
 * itself as a link, and the summary written out in the reader's language.
 */
export const WallZoomFocus = ({
  title,
  href,
  source,
  onClose,
}: {
  title: string
  href: string
  source: NewsSourceMeta
  onClose: () => void
}) => {
  const t = useT()

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <>
      {/* Plain divs for the overlay geometry: the scrim tint, the centring and
          the dialog's own max height aren't Box tokens, and Box takes no
          className (AGENTS.md escape hatch). */}
      <div
        className="paper-overlay zoom-focus-scrim"
        onClick={onClose}
        aria-hidden
      />
      <div className="zoom-focus" role="dialog" aria-modal="true">
        <button
          type="button"
          className="ghost-pill zoom-focus-close"
          onClick={onClose}
          aria-label={t('news.view.close')}
          title={t('news.view.close')}
        >
          <X size={15} aria-hidden />
        </button>
        <div className="paper-sheet zoom-focus-card">
          <Box
            flexDirection="column"
            rowGap="m"
            padding={{ base: 'l', md: 'xl' }}
          >
            <Box
              flexDirection="row"
              alignItems="center"
              justifyContent="between"
              columnGap="s"
            >
              <Box
                flexDirection="row"
                alignItems="center"
                columnGap="s"
                flexShrink={1}
                minWidth={0}
              >
                <a
                  href={safeExternalHref(source.home)}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={source.name}
                  style={{ flexShrink: 0, lineHeight: 0 }}
                >
                  <SourceBadge
                    id={source.id}
                    name={source.name}
                    logo={source.logo}
                    size={32}
                  />
                </a>
                <Box
                  flexDirection="row"
                  alignItems="center"
                  columnGap="s"
                  minWidth={0}
                >
                  <span
                    aria-hidden
                    style={{
                      display: 'inline-block',
                      width: 8,
                      height: 8,
                      flexShrink: 0,
                      borderRadius: 9999,
                      backgroundColor: source.color,
                    }}
                  />
                  <Text variant="body" as="h3" serif truncate>
                    {source.name}
                  </Text>
                </Box>
              </Box>
              <Box
                flexDirection="row"
                alignItems="center"
                columnGap="s"
                flexShrink={0}
              >
                <ShareButton source={source} />
                <FollowButton sourceId={source.id} />
              </Box>
            </Box>

            {/* The same hairline the cards draw under their header. */}
            <div className="rule-corner min-w-0">
              <a
                href={safeExternalHref(href)}
                target="_blank"
                rel="noopener noreferrer"
                className="headline-link block rounded-md pr-1 pb-2"
              >
                <Text variant="heading-xxs" as="span" serif>
                  {title}
                </Text>
              </a>
              <InlineSummary
                url={href}
                sourceName={source.name}
                onClose={onClose}
              />
            </div>
          </Box>
        </div>
      </div>
    </>
  )
}
