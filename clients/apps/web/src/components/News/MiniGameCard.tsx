'use client'

import { useT } from '@/providers/locale'
import type { NewsSourceMeta } from '@/utils/news'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { useEffect, useRef, useState } from 'react'
import { FollowButton } from './FollowButton'
import { setGameStrip } from './gameNoteStore'
import type { GameAction } from './gameNoteStore'
import { ShareButton } from './ShareButton'

/** The wall's playable break cards — cube, crossword, sudoku — share one
 * shell: a self-contained static page (public/<game>/) in an iframe so each
 * game's renderer, input, and saved progress stay fully isolated from the
 * deck. The header strip stays in the newsprint idiom and doubles as the
 * drag handle for swiping the card away — pointer events inside the iframe
 * belong to the game. The deck mounts a card one swipe before it arrives,
 * so the game is already booted by the time it lands on top (and stays
 * mounted so a swipe away doesn't reset a solve).
 *
 * The solve clock lives in the header, and the game's text/controls strip
 * (clue, status, sudoku tools) lives on the wall ABOVE the card (see
 * GameNoteBar) — each game posts its state up via postMessage, and strip
 * buttons send commands back into the iframe. */
export const MINI_GAMES = {
  cube: {
    nameKey: 'news.cube.name',
    kickerKey: 'news.cube.kicker',
    src: '/cube/index.html',
  },
  crossword: {
    nameKey: 'news.crossword.name',
    kickerKey: 'news.crossword.kicker',
    src: '/crossword/index.html',
  },
  sudoku: {
    nameKey: 'news.sudoku.name',
    kickerKey: 'news.sudoku.kicker',
    src: '/sudoku/index.html',
  },
  solitaire: {
    nameKey: 'news.solitaire.name',
    kickerKey: 'news.solitaire.kicker',
    src: '/solitaire/index.html',
  },
} as const

export type MiniGameId = keyof typeof MINI_GAMES

export const isMiniGameId = (id: string): id is MiniGameId => id in MINI_GAMES

export const MiniGameCard = ({
  game,
  source,
  active = false,
}: {
  game: MiniGameId
  source: NewsSourceMeta
  active?: boolean
}) => {
  const t = useT()
  const spec = MINI_GAMES[game]
  const frameRef = useRef<HTMLIFrameElement>(null)
  const [clock, setClock] = useState('0:00')
  const [note, setNote] = useState('')
  const [actions, setActions] = useState<GameAction[]>([])
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      // The games are same-origin iframes — anything else (e.g. a page that
      // window-opened the wall) must not be able to spoof the strip.
      if (e.origin !== window.location.origin) return
      const d = e.data as {
        outceptionGame?: string
        timer?: string
        note?: string
        actions?: GameAction[]
        playing?: boolean
      } | null
      if (!d || d.outceptionGame !== game) return
      if (typeof d.timer === 'string') setClock(d.timer)
      if (typeof d.note === 'string') {
        setNote(d.note)
        setActions(Array.isArray(d.actions) ? d.actions : [])
        setPlaying(d.playing === true)
      }
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [game])

  // Only the TOP card owns the wall's strip (see GameNoteBar) — the peeking
  // neighbours stay mounted and keep posting, so gate on `active`.
  useEffect(() => {
    if (!active) return
    setGameStrip({
      note,
      actions,
      playing,
      send: (cmd) =>
        frameRef.current?.contentWindow?.postMessage(
          { outceptionGameCmd: cmd },
          '*',
        ),
    })
    return () => setGameStrip(null)
  }, [active, note, actions, playing])

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
        position="relative"
      >
        <Box
          flexDirection="row"
          alignItems="center"
          columnGap="s"
          flexShrink={1}
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
              backgroundColor: '#e81c2e',
            }}
          />
          <Box flexDirection="column" rowGap="none" minWidth={0}>
            <Text variant="body" as="h3" serif truncate>
              {t(spec.nameKey)}
            </Text>
            <span className="meta-kicker">{t(spec.kickerKey)}</span>
          </Box>
        </Box>
        {/* The game's clock, dead-center regardless of how wide the name or
            the buttons run (hence absolute, not a flex column). */}
        <Box
          position="absolute"
          left="50%"
          transform="translateX(-50%)"
          pointerEvents="none"
        >
          {/* Plain span: bold tabular digits aren't a Text variant (same
              escape hatch as the meta-kicker above). */}
          <span
            style={{ fontWeight: 800, fontVariantNumeric: 'tabular-nums' }}
          >
            {clock}
          </span>
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
      <Box
        flexGrow={1}
        minHeight={0}
        borderRadius="m"
        overflow="hidden"
        display="block"
      >
        <iframe
          ref={frameRef}
          src={spec.src}
          title={t(spec.nameKey)}
          style={{
            border: 0,
            width: '100%',
            height: '100%',
            display: 'block',
          }}
        />
      </Box>
    </Box>
  )
}
