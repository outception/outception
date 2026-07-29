import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import type { NewsSourceMeta } from '@/hooks/outception/news'
import { WEB_URL } from '@/utils/env'
import { openExternalUrl } from '@/utils/news'
import { memo } from 'react'
import { WebView } from 'react-native-webview'
import { FollowButton } from './FollowButton'
import { KICKER_STYLE } from './newsStyles'
import { ShareButton } from './ShareButton'
import { SourceAccentTab } from './SourceAccentTab'
import { SourceBadge } from './SourceBadge'

/** A playable break card — the same self-contained game pages the web wall
 * embeds (crossword, sudoku, solitaire, cube), rendered in a WebView. Outside
 * the wall's iframe the games run their standalone chrome (their own timer
 * hud, clue rail and tool row), so the card supplies only the newsprint
 * header. The deck's swipe gesture is restricted to that header for game
 * cards (see SwipeDeckCard) — touches on the board belong to the game,
 * exactly like the web where the iframe owns its pointer events. */
export const GameCard = memo(function GameCard({
  source,
  elevated,
}: {
  source: NewsSourceMeta
  elevated?: boolean
}) {
  const theme = useTheme()
  return (
    <Box
      flex={1}
      gap="spacing-12"
      padding="spacing-16"
      borderRadius="border-radius-16"
      backgroundColor={elevated ? 'card' : 'cardUnder'}
      borderWidth={1}
      borderColor="border"
      style={
        elevated
          ? {
              shadowOffset: {
                width: 0,
                height: theme.dimension['dimension-12'],
              },
              shadowOpacity: 0.18,
              shadowRadius: theme.dimension['dimension-24'],
              elevation: 8,
            }
          : { elevation: 1 }
      }
    >
      <SourceAccentTab color={source.color} />
      <Box
        flexDirection="row"
        alignItems="center"
        justifyContent="space-between"
        gap="spacing-8"
      >
        <Box
          flexDirection="row"
          alignItems="center"
          gap="spacing-8"
          flexShrink={1}
        >
          <Touchable onPress={() => openExternalUrl(source.home ?? undefined)}>
            <SourceBadge
              id={source.id}
              name={source.name}
              logo={source.logo}
              size={32}
            />
          </Touchable>
          <Box gap="spacing-2" flexShrink={1}>
            <Text variant="bodySerif" numberOfLines={1}>
              {source.name}
            </Text>
            <Text variant="caption" color="subtext" style={KICKER_STYLE}>
              {(source.title ?? '').toUpperCase()}
            </Text>
          </Box>
        </Box>
        <Box flexDirection="row" alignItems="center" gap="spacing-8">
          <ShareButton source={source} />
          <FollowButton sourceId={source.id} />
        </Box>
      </Box>
      <Box
        flex={1}
        borderRadius="border-radius-12"
        style={{ overflow: 'hidden' }}
      >
        <WebView
          source={{ uri: `${WEB_URL}/${source.id}/index.html` }}
          style={{ flex: 1, backgroundColor: 'transparent' }}
          // The grid games raise the phone keyboard by focusing a hidden
          // input from a tap handler — iOS blocks that unless allowed here.
          keyboardDisplayRequiresUserAction={false}
          // The pages are fixed-viewport (their inner panes scroll
          // themselves); the WebView's own scroller only adds rubber-banding.
          scrollEnabled={false}
          bounces={false}
          setSupportMultipleWindows={false}
          allowsBackForwardNavigationGestures={false}
        />
      </Box>
    </Box>
  )
})
