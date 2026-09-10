/** Module store for the game strip shown on the wall itself, centered between
 * the gem ornament and the top of the card: the crossword's live clue, the
 * sudoku status line and its ERASE/CHECK/REVEAL controls (the phone keyboard
 * covers anything at the bottom of the card). The active MiniGameCard
 * publishes here; GameNoteBar subscribes and sends commands back into the
 * game's iframe. Same pattern as newsPrefsStore. */

export type GameAction = { cmd: string; label: string }

export type GameStrip = {
  note: string
  actions: GameAction[]
  playing: boolean
  send: ((cmd: string) => void) | null
}

const EMPTY: GameStrip = { note: '', actions: [], playing: false, send: null }

let strip: GameStrip = EMPTY
const listeners = new Set<() => void>()

export const setGameStrip = (next: GameStrip | null) => {
  const value = next ?? EMPTY
  const same =
    value.note === strip.note &&
    value.playing === strip.playing &&
    value.send === strip.send &&
    value.actions.length === strip.actions.length &&
    value.actions.every(
      (a, i) =>
        a.cmd === strip.actions[i]?.cmd && a.label === strip.actions[i]?.label,
    )
  if (same) return
  strip = value
  listeners.forEach((l) => l())
}

export const subscribeGameStrip = (listener: () => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getGameStrip = () => strip
export const getGameStripServerSnapshot = () => EMPTY
