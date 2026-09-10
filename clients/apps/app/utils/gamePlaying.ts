// Whether a game card is actively being PLAYED (its embedded page reports
// `playing: true` over the WebView bridge - see GameCard). Exposed as an
// external store, same pattern as utils/locale.ts, so the home header can
// step its gem ornament aside during play exactly like the web WallOrnament.
let playing = false
const listeners = new Set<() => void>()

export const setGamePlaying = (next: boolean): void => {
  if (next === playing) return
  playing = next
  for (const listener of listeners) listener()
}

export const subscribeGamePlaying = (listener: () => void): (() => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getGamePlayingSnapshot = (): boolean => playing
