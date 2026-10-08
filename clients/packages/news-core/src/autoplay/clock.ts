/** A clock the runner can be handed: real time in the app, manual in tests. */

export interface Clock {
  now(): number
  /** Run `fn` after `ms`; returns the cancel. */
  schedule(fn: () => void, ms: number): () => void
}

export interface ManualClock extends Clock {
  /** Advance time, firing due callbacks in order. */
  advance(ms: number): void
  pending(): number
}

export const createManualClock = (start = 0): ManualClock => {
  let now = start
  let nextId = 1
  const timers = new Map<number, { at: number; fn: () => void }>()
  return {
    now: () => now,
    schedule: (fn, ms) => {
      const id = nextId
      nextId += 1
      timers.set(id, { at: now + Math.max(0, ms), fn })
      return () => {
        timers.delete(id)
      }
    },
    advance: (ms) => {
      const target = now + Math.max(0, ms)
      for (;;) {
        let dueId: number | null = null
        let dueAt = Number.POSITIVE_INFINITY
        for (const [id, timer] of timers) {
          if (
            timer.at <= target &&
            (timer.at < dueAt || (timer.at === dueAt && id < (dueId ?? id)))
          ) {
            dueAt = timer.at
            dueId = id
          }
        }
        if (dueId === null) break
        const timer = timers.get(dueId)!
        timers.delete(dueId)
        now = timer.at
        timer.fn()
      }
      now = target
    },
    pending: () => timers.size,
  }
}

/** A clock over an injected scheduler, so the runner never touches globals. */
export const createClock = (
  now: () => number,
  setTimer: (fn: () => void, ms: number) => unknown,
  clearTimer: (handle: unknown) => void,
): Clock => ({
  now,
  schedule: (fn, ms) => {
    const handle = setTimer(fn, ms)
    return () => clearTimer(handle)
  },
})
