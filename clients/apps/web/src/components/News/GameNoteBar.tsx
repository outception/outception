'use client'

import { Box } from '@outception-com/orbit/Box'
import { useEffect, useSyncExternalStore } from 'react'
import { WallOrnament } from './WallOrnament'
import {
  getGameStrip,
  getGameStripServerSnapshot,
  subscribeGameStrip,
} from './gameNoteStore'

/** The game strip lifted out of the card: the controls row (ERASE / CHECK /
 * REVEAL) directly above the clue/status pill, both hugging the top of the
 * card - where the phone keyboard can never cover them.
 *
 * When the on-screen keyboard actually APPEARS (visualViewport shrinks -
 * i.e. a phone), a body flag collapses this strip's grown space and the
 * wall's centering so the whole stack rides up tight under the navbar.
 * Desktop never triggers it. */
export const GameNoteBar = () => {
  const strip = useSyncExternalStore(
    subscribeGameStrip,
    getGameStrip,
    getGameStripServerSnapshot,
  )

  useEffect(() => {
    const vv = window.visualViewport
    if (!vv) return
    const update = () => {
      const keyboardUp = vv.height < window.innerHeight - 140
      document.body.classList.toggle('kb-open', strip.playing && keyboardUp)
    }
    update()
    vv.addEventListener('resize', update)
    return () => {
      vv.removeEventListener('resize', update)
      document.body.classList.remove('kb-open')
    }
  }, [strip.playing])

  return (
    /* Plain wrapper: the keyboard-up CSS targets `.game-strip`, and Box
       takes no className (AGENTS.md escape hatch). It owns the grow/clamp
       so the kb-open override can collapse it; the Box lays out inside. */
    <div className="game-strip flex max-h-16 min-h-9 grow flex-col">
      <Box
        flexDirection="column"
        alignItems="center"
        justifyContent="end"
        rowGap="s"
        flexGrow={1}
        paddingHorizontal="xl"
        textAlign="center"
      >
        {/* The gem ornament, centered in whatever space is free between the
          navbar and the card (it hides itself during play). */}
        <Box flexGrow={1} alignItems="center" justifyContent="center">
          <WallOrnament />
        </Box>
        {strip.actions.length > 0 ? (
          <Box
            alignItems="center"
            justifyContent="center"
            flexWrap="wrap"
            columnGap="s"
            rowGap="s"
          >
            {strip.actions.map((action) => (
              <button
                key={action.cmd}
                type="button"
                className="game-pill game-pill--ghost"
                onClick={() => strip.send?.(action.cmd)}
              >
                {action.label}
              </button>
            ))}
          </Box>
        ) : null}
        {strip.note ? <span className="game-pill">{strip.note}</span> : null}
      </Box>
    </div>
  )
}
