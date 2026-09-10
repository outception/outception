// The game's host strip - the clue/status line and the tool row (ERASE /
// CHECK / REVEAL…) a game page posts up over the WebView bridge, plus the
// solve clock and the callback that sends a command back down into the page.
// It lives on the WALL above the card rather than inside it (web
// GameNoteBar/gameNoteStore), so the phone keyboard can never cover it.
// Exposed as an external store, same pattern as utils/gamePlaying.ts: only
// the elevated GameCard publishes, and GameStrip subscribes.

export type GameAction = { cmd: string; label: string }

export type GameStrip = {
  clock: string | null
  note: string
  actions: GameAction[]
  dispatch: ((cmd: string) => void) | null
}

const EMPTY: GameStrip = { clock: null, note: '', actions: [], dispatch: null }

// useSyncExternalStore compares snapshots by IDENTITY and re-renders until two
// reads agree - so the snapshot must be one cached object that is replaced
// only when a field actually changed, never rebuilt per read.
let strip: GameStrip = EMPTY
const listeners = new Set<() => void>()

export const setGameStrip = (next: GameStrip | null): void => {
  const value = next ?? EMPTY
  const same =
    value.clock === strip.clock &&
    value.note === strip.note &&
    value.dispatch === strip.dispatch &&
    value.actions.length === strip.actions.length &&
    value.actions.every(
      (action, i) =>
        action.cmd === strip.actions[i]?.cmd &&
        action.label === strip.actions[i]?.label,
    )
  if (same) return
  strip = value
  for (const listener of listeners) listener()
}

export const subscribeGameStrip = (listener: () => void): (() => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getGameStripSnapshot = (): GameStrip => strip
