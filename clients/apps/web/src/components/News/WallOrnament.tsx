'use client'

import { OutceptionLogotype } from '@/components/Layout/Public/OutceptionLogotype'
import { Box } from '@outception-com/orbit/Box'
import { useSyncExternalStore } from 'react'
import {
  getGameStrip,
  getGameStripServerSnapshot,
  subscribeGameStrip,
} from './gameNoteStore'

/** The gem ornament between hairlines. While a game is actually being PLAYED
 * it steps aside — the header shrinks and the card and its text ride up,
 * which matters when the phone keyboard already eats half the screen. Backing
 * out of the game brings it straight back. */
export const WallOrnament = () => {
  const strip = useSyncExternalStore(
    subscribeGameStrip,
    getGameStrip,
    getGameStripServerSnapshot,
  )

  if (strip.playing) return null

  return (
    <Box alignItems="center" columnGap="m">
      <div aria-hidden className="rule-hairline w-12" />
      <OutceptionLogotype href="/" togglesTheme size={32} />
      <div aria-hidden className="rule-hairline w-12" />
    </Box>
  )
}
