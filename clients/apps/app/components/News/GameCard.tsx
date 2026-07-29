import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import type { NewsSourceMeta } from '@/hooks/outception/news'
import { useT } from '@/providers/LocaleProvider'
import { WEB_URL } from '@/utils/env'
import { setGamePlaying } from '@/utils/gamePlaying'
import { setGameStrip } from '@/utils/gameStrip'
import { getSummarySwipeHandler } from '@/utils/summaryOpen'
import { openExternalUrl } from '@/utils/news'
import { memo, useCallback, useEffect, useRef, useState } from 'react'
import { WebView, type WebViewMessageEvent } from 'react-native-webview'
import { FollowButton } from './FollowButton'
import { KICKER_STYLE } from './newsStyles'
import { ShareButton } from './ShareButton'
import { SourceAccentTab } from './SourceAccentTab'

// Prefix match on the origin plus a path separator: a bare startsWith(WEB_URL)
// would also accept "<WEB_URL>.evil.tld".
const WEB_ORIGIN = WEB_URL.replace(/\/+$/, '')
const isOwnWebUrl = (url: string) =>
  url === WEB_ORIGIN || url.startsWith(`${WEB_ORIGIN}/`)

// The games' identity is localized like the web's MINI_GAMES map - the server
// roster only carries English name/title. Unknown ids fall back to those.
const GAME_KEYS = {
  cube: { name: 'news.cube.name', kicker: 'news.cube.kicker' },
  crossword: { name: 'news.crossword.name', kicker: 'news.crossword.kicker' },
  sudoku: { name: 'news.sudoku.name', kicker: 'news.sudoku.kicker' },
  solitaire: { name: 'news.solitaire.name', kicker: 'news.solitaire.kicker' },
} as const

export type MiniGameId = keyof typeof GAME_KEYS

/** Only these four ids have a page under WEB_URL (web MINI_GAMES/isMiniGameId).
 * `type === 'game'` alone is the SERVER's word for it - an id the app doesn't
 * ship a page for would otherwise mount a WebView pointed at a 404, so the
 * deck pairs this with the type check and falls back to the news card. */
export const isMiniGameId = (id: string): id is MiniGameId => id in GAME_KEYS

/** What a game page posts up over the bridge - the exact payloads the web
 * host receives via iframe postMessage (see web MiniGameCard/gameNoteStore):
 * `{outceptionGame, timer}` ticks plus `{outceptionGame, note, actions,
 * playing}` strip updates. Loaded with ?embed=1 the pages mirror the same
 * JSON strings to window.ReactNativeWebView.postMessage. */
type GameAction = { cmd: string; label: string }
type GameBridgeMessage = {
  outceptionGame?: string
  timer?: string
  note?: string
  actions?: GameAction[]
  playing?: boolean
  outceptionGameSwipe?: 'left' | 'right'
}

/** A playable break card - the same self-contained game pages the web wall
 * embeds (crossword, sudoku, solitaire, cube), rendered in a WebView with
 * ?embed=1, so the page hides its own hud/tool chrome and posts its state up
 * exactly like the web iframe does. The card itself keeps only the solve
 * clock, centered in the header (in the kicker's place while the game is
 * live); the clue/status pill and the tool row (ERASE / CHECK / REVEAL…) are
 * published to utils/gameStrip and rendered on the WALL above the card by
 * GameStrip - where the phone keyboard can never cover them, exactly like the
 * web MiniGameCard → GameNoteBar. The deck's swipe gesture is restricted to
 * the header for game cards (see SwipeDeckCard) - touches on the board belong
 * to the game, exactly like the web where the iframe owns its pointer events. */
export const GameCard = memo(function GameCard({
  source,
  elevated,
}: {
  source: NewsSourceMeta
  elevated?: boolean
}) {
  const theme = useTheme()
  const t = useT()
  const game = GAME_KEYS[source.id as keyof typeof GAME_KEYS] as
    | (typeof GAME_KEYS)[keyof typeof GAME_KEYS]
    | undefined

  const webviewRef = useRef<WebView>(null)
  // Starts at zero and the header shows it from the first frame, exactly like
  // the web card - a clock that appears late (and displaced the kicker while
  // it did) made the header twitch on every card landing.
  const [clock, setClock] = useState('0:00')
  const [note, setNote] = useState('')
  const [actions, setActions] = useState<GameAction[]>([])
  const [playing, setPlaying] = useState(false)
  // The page (or the network) failed us: swap the WebView for a caption and a
  // way out to the browser rather than showing the platform's error chrome -
  // or, with a transparent WebView background, nothing at all.
  const [failed, setFailed] = useState(false)

  const gameUrl = `${WEB_URL}/${encodeURIComponent(source.id)}/`

  const onGameMessage = (e: WebViewMessageEvent) => {
    let d: GameBridgeMessage | null = null
    try {
      d = JSON.parse(e.nativeEvent.data) as GameBridgeMessage
    } catch {
      return
    }
    // A stroke on the game's non-interactive chrome: the deck's own pan is
    // restricted to the header while a game runs, so the page reports the
    // direction and the top card's swipe executor applies its usual
    // direction/RTL/bounds rules (the same store slot the open summary
    // dispatches through). The web host does the same via window messages.
    if (
      d?.outceptionGameSwipe === 'left' ||
      d?.outceptionGameSwipe === 'right'
    ) {
      getSummarySwipeHandler()?.(d.outceptionGameSwipe === 'left' ? -60 : 60)
      return
    }
    // Keyed by game id like the web host - the page only ever loads our own
    // origin (originWhitelist below), so this matches the iframe's trust.
    if (!d || d.outceptionGame !== source.id) return
    if (typeof d.timer === 'string') setClock(d.timer)
    if (typeof d.note === 'string') {
      setNote(d.note)
      setActions(Array.isArray(d.actions) ? d.actions : [])
      setPlaying(d.playing === true)
    }
  }

  // The same dispatch the web host uses (postMessage into the frame): the
  // pages listen for window `message` events and check the sender's origin,
  // which a same-context window.postMessage satisfies. Identity-stable (the
  // ref carries the WebView) so republishing it never churns the store.
  const sendCmd = useCallback((cmd: string) => {
    webviewRef.current?.injectJavaScript(
      `window.postMessage(${JSON.stringify({ outceptionGameCmd: cmd })}, window.location.origin); true;`,
    )
  }, [])

  // Publish the strip to the wall (web MiniGameCard → gameNoteStore): only
  // the TOP card owns it - the peeking neighbours must not clobber it - and
  // de-elevating or unmounting clears it via the cleanup.
  useEffect(() => {
    if (!elevated) return
    setGameStrip({ clock, note, actions, dispatch: sendCmd })
    return () => setGameStrip(null)
  }, [elevated, clock, note, actions, sendCmd])

  // Publish play state so the home header can step its ornament aside (web
  // WallOrnament). Only the running card ever touches the store - a mounting
  // peek must not clobber the top card's `true` - and stopping, swiping the
  // card behind, or unmounting clears it via the cleanup.
  const running = Boolean(elevated) && playing
  useEffect(() => {
    if (!running) return
    setGamePlaying(true)
    return () => setGamePlaying(false)
  }, [running])

  // A card swiped behind unmounts its WebView (see below) - drop the bridge
  // state with it so the strip never replays stale controls on remount.
  useEffect(() => {
    if (elevated) return
    setClock('0:00')
    setNote('')
    setActions([])
    setPlaying(false)
    // A swipe away and back is the retry: the WebView remounts fresh.
    setFailed(false)
  }, [elevated])

  return (
    <Box
      flex={1}
      gap="spacing-12"
      padding="spacing-16"
      borderRadius="border-radius-16"
      backgroundColor={elevated ? 'card' : 'cardUnder'}
      borderWidth={1}
      borderColor="border"
      style={[
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
          : { elevation: 1 },
      ]}
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
          {/* An inert dot, not the source badge: a game has no publisher to
              visit, and the web card draws the same 8px accent dot here. A
              Touchable would have thrown the player out to the browser
              mid-solve. */}
          <Box
            width={8}
            height={8}
            borderRadius="border-radius-999"
            flexShrink={0}
            style={{ backgroundColor: source.color }}
          />
          <Box gap="spacing-2" flexShrink={1}>
            <Text variant="bodySerif" numberOfLines={1}>
              {game ? t(game.name) : source.name}
            </Text>
            {/* Name AND kicker stay put for the whole solve (web
                MiniGameCard) - the clock has its own absolute slot. */}
            <Text variant="caption" color="subtext" style={KICKER_STYLE}>
              {(game ? t(game.kicker) : (source.title ?? '')).toUpperCase()}
            </Text>
          </Box>
        </Box>
        {/* The game's clock. A flex sibling, NOT the absolute center slot it
            used to be: dead-centering printed the clock straight through any
            localized title long enough to reach the middle ("Crucigrama del
            NYT" under es). As a shrink-proof sibling the title ellipsizes
            before touching it (web MiniGameCard fixed the same way). */}
        <Box pointerEvents="none" flexShrink={0}>
          <Text
            variant="body"
            style={{ fontWeight: '800', fontVariant: ['tabular-nums'] }}
          >
            {clock}
          </Text>
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
        {failed ? (
          // Offline, or the page 404'd: a plain caption plus a way out,
          // instead of the platform's error page or (with the transparent
          // WebView background) a silent void.
          <Box
            flex={1}
            backgroundColor="cardUnder"
            alignItems="center"
            justifyContent="center"
            gap="spacing-8"
          >
            <Text variant="caption" color="subtext">
              {t('news.card.failed')}
            </Text>
            <Touchable onPress={() => openExternalUrl(gameUrl)}>
              <Box
                paddingVertical="spacing-4"
                paddingHorizontal="spacing-12"
                borderRadius="border-radius-999"
                borderWidth={1}
                borderColor="border"
              >
                <Text variant="caption" color="text">
                  {t('news.card.openInBrowser')}
                </Text>
              </Box>
            </Touchable>
          </Box>
        ) : elevated ? (
          <WebView
            ref={webviewRef}
            source={{
              // ?embed=1: the page hides its own hud and mirrors its host
              // postMessage traffic to the ReactNativeWebView bridge.
              uri: `${gameUrl}index.html?embed=1`,
            }}
            onMessage={onGameMessage}
            onError={() => setFailed(true)}
            onHttpError={() => setFailed(true)}
            // Keep the WebView on our own origin: anything else a game page
            // links to goes to the system browser, never rendered in-card.
            originWhitelist={[WEB_URL]}
            onShouldStartLoadWithRequest={(request) => {
              if (isOwnWebUrl(request.url)) return true
              openExternalUrl(request.url)
              return false
            }}
            style={{ flex: 1, backgroundColor: 'transparent' }}
            // The grid games raise the phone keyboard by focusing a hidden
            // input from a tap handler - iOS blocks that unless allowed here.
            keyboardDisplayRequiresUserAction={false}
            // The pages are fixed-viewport (their inner panes scroll
            // themselves); the WebView's own scroller only adds rubber-banding.
            scrollEnabled={false}
            bounces={false}
            setSupportMultipleWindows={false}
            allowsBackForwardNavigationGestures={false}
          />
        ) : (
          // Peeking neighbours DON'T run a live WebView: the cube renders
          // WebGL continuously and multiple mounted game pages tripped the
          // iOS RAM watchdog (seen on Apple's own review devices). Games
          // save to localStorage on every move, so the remount when the
          // card lands on top restores exactly where the player left off.
          <Box
            flex={1}
            backgroundColor="cardUnder"
            alignItems="center"
            justifyContent="center"
          />
        )}
      </Box>
    </Box>
  )
})
