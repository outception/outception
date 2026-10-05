/**
 * Animation holds: tickers, flaps and auto-play take a hold while they want
 * to animate. With no holds, a hidden tab, an offscreen card or reduced
 * motion, nothing animates. The useful half of a render governor.
 */

export interface HoldRegistry {
  /** Take a hold for `owner`; returns the release. Releasing twice is safe. */
  take(owner: string): () => void
  count(): number
  owners(): readonly string[]
  /** The tab or app is visible. */
  setVisible(visible: boolean): void
  /** The reader asked for reduced motion. */
  setReducedMotion(reduced: boolean): void
  /** Whether an animation for `owner` should run now. `onscreen` is the
   * owner's own visibility, when it knows it. */
  shouldAnimate(owner?: string, onscreen?: boolean): boolean
  subscribe(listener: () => void): () => void
}

export const createHoldRegistry = (): HoldRegistry => {
  const holds = new Map<string, number>()
  const listeners = new Set<() => void>()
  let visible = true
  let reducedMotion = false

  const emit = () => {
    for (const listener of listeners) listener()
  }

  const count = () => {
    let total = 0
    for (const n of holds.values()) total += n
    return total
  }

  return {
    take: (owner) => {
      holds.set(owner, (holds.get(owner) ?? 0) + 1)
      emit()
      let released = false
      return () => {
        if (released) return
        released = true
        const n = (holds.get(owner) ?? 0) - 1
        if (n <= 0) holds.delete(owner)
        else holds.set(owner, n)
        emit()
      }
    },
    count,
    owners: () => [...holds.keys()],
    setVisible: (next) => {
      if (next === visible) return
      visible = next
      emit()
    },
    setReducedMotion: (next) => {
      if (next === reducedMotion) return
      reducedMotion = next
      emit()
    },
    shouldAnimate: (owner, onscreen = true) => {
      if (reducedMotion || !visible || !onscreen) return false
      if (owner !== undefined) return (holds.get(owner) ?? 0) > 0
      return count() > 0
    },
    subscribe: (listener) => {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    },
  }
}
