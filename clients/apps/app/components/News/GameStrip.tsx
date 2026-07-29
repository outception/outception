import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import {
  getGamePlayingSnapshot,
  subscribeGamePlaying,
} from '@/utils/gamePlaying'
import { getGameStripSnapshot, subscribeGameStrip } from '@/utils/gameStrip'
import { useSyncExternalStore } from 'react'
import { Pressable } from 'react-native'

/** Web `.game-pill` (globals.css): 11px / 700 / 0.02em — its own micro type,
 * NOT the wall's letterspaced kicker (the labels arrive already uppercased
 * from the page, so no textTransform here either). */
const PILL_LABEL = {
  fontSize: 11,
  fontWeight: '700',
  letterSpacing: 0.22,
  lineHeight: 14,
} as const

/** Web `.game-strip` reserves `min-h-9` (36px) whether or not the game is
 * publishing anything, so the deck never jolts when a clue or a tool row
 * appears mid-solve. */
const STRIP_MIN_HEIGHT = 36

/** The game strip lifted out of the card and onto the wall (web GameNoteBar):
 * the tool row (ERASE / CHECK / REVEAL…) with the clue/status pill under it,
 * both ABOVE the card — where the phone keyboard can never cover them. It
 * takes the slot the gem ornament vacates during play (see gamePlaying).
 *
 * While a game is live the container is ALWAYS rendered at its reserved
 * height, even between clues, so the board never resizes mid-solve. With no
 * game running it renders nothing at all: an empty Box would still push the
 * deck down on every other card. */
export const GameStrip = () => {
  const strip = useSyncExternalStore(
    subscribeGameStrip,
    getGameStripSnapshot,
    getGameStripSnapshot,
  )
  const playing = useSyncExternalStore(
    subscribeGamePlaying,
    getGamePlayingSnapshot,
    getGamePlayingSnapshot,
  )

  // A live `dispatch` means the elevated card IS a game (only the top card
  // publishes) — so the slot is reserved from the moment the card lands, not
  // from the first move. `playing` is the same signal the header uses to step
  // the ornament aside, kept here so the two can never disagree.
  const gameLive = strip.dispatch !== null || playing
  const hasContent = strip.actions.length > 0 || Boolean(strip.note)
  if (!hasContent && !gameLive) return null

  return (
    <Box
      gap="spacing-8"
      alignItems="center"
      justifyContent="center"
      minHeight={STRIP_MIN_HEIGHT}
      paddingHorizontal="spacing-16"
      paddingBottom="spacing-12"
    >
      {strip.actions.length > 0 ? (
        <Box
          flexDirection="row"
          flexWrap="wrap"
          justifyContent="center"
          gap="spacing-8"
        >
          {strip.actions.map((action) => (
            // Pressable, not the shared Touchable: web's `.game-pill:active`
            // scales to .94 as well as fading, and only the style callback
            // gives us the pressed flag to drive the transform.
            <Pressable
              key={action.cmd}
              onPress={() => strip.dispatch?.(action.cmd)}
              accessibilityRole="button"
              style={({ pressed }) => ({
                opacity: pressed ? 0.7 : 1,
                transform: [{ scale: pressed ? 0.94 : 1 }],
              })}
            >
              <Box
                paddingVertical="spacing-4"
                paddingHorizontal="spacing-12"
                borderRadius="border-radius-999"
                borderWidth={1}
                borderColor="border"
              >
                <Text variant="caption" color="subtext" style={PILL_LABEL}>
                  {action.label}
                </Text>
              </Box>
            </Pressable>
          ))}
        </Box>
      ) : null}
      {strip.note ? (
        <Box
          paddingVertical="spacing-4"
          paddingHorizontal="spacing-12"
          borderRadius="border-radius-999"
          backgroundColor="gamePill"
        >
          {/* Two lines max: a long crossword clue wrapping to three squeezed
              the board out of the card. */}
          <Text
            variant="caption"
            color="gamePillText"
            numberOfLines={2}
            style={{ textAlign: 'center' }}
          >
            {strip.note}
          </Text>
        </Box>
      ) : null}
    </Box>
  )
}
