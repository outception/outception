/**
 * The auto-play runner: select a shot, travel to it, hold, move on, until
 * the timeline completes. Injectable clock, cancellation through an abort
 * signal, and a seekable position so a progress line can scrub.
 */

import type { Clock } from './clock'
import { seekTimeline, type Shot, type Timeline } from './timeline'

export type AutoplayPhase =
  | 'idle'
  | 'select'
  | 'travel'
  | 'hold'
  | 'paused'
  | 'complete'

/** The subset of AbortSignal the runner needs, typed locally so this module
 * stays free of the DOM lib. */
export interface Abortable {
  readonly aborted: boolean
  addEventListener(type: 'abort', listener: () => void): void
  removeEventListener(type: 'abort', listener: () => void): void
}

export interface RunnerState {
  phase: AutoplayPhase
  index: number
  shot: Shot | null
  /** Position on the timeline, milliseconds. */
  positionMs: number
  totalMs: number
}

export interface RunnerOptions {
  timeline: Timeline
  clock: Clock
  /** Called to move the renderer onto the shot; `travelMs` is waited. */
  travel?: (shot: Shot, index: number) => void
  travelMs?: number
  signal?: Abortable
  onChange?: (state: RunnerState) => void
}

export interface AutoplayRunner {
  start(fromMs?: number): void
  pause(): void
  resume(): void
  stop(): void
  seek(ms: number): void
  state(): RunnerState
}

export const createRunner = (options: RunnerOptions): AutoplayRunner => {
  const { timeline, clock } = options
  const travelMs = options.travelMs ?? 400
  let phase: AutoplayPhase = 'idle'
  let index = -1
  let cancel: (() => void) | null = null
  // Where the current phase started on the clock and on the timeline, so a
  // pause can resume with the remaining time and a seek can report position.
  let phaseStartedAt = 0
  let phaseLengthMs = 0
  let remainingMs = 0
  let resumeTo: 'travel' | 'hold' | null = null

  const shot = (): Shot | null => timeline.shots[index] ?? null

  const positionMs = (): number => {
    const current = shot()
    if (!current) return phase === 'complete' ? timeline.totalMs : 0
    if (phase === 'hold') {
      return (
        current.startMs +
        Math.min(current.dwellMs, clock.now() - phaseStartedAt)
      )
    }
    if (phase === 'paused' && resumeTo === 'hold') {
      return current.startMs + Math.max(0, current.dwellMs - remainingMs)
    }
    return current.startMs
  }

  const state = (): RunnerState => ({
    phase,
    index,
    shot: shot(),
    positionMs: positionMs(),
    totalMs: timeline.totalMs,
  })

  const notify = () => options.onChange?.(state())

  const clearTimer = () => {
    cancel?.()
    cancel = null
  }

  const stop = () => {
    clearTimer()
    phase = 'idle'
    index = -1
    resumeTo = null
    notify()
  }

  const onAbort = () => stop()
  options.signal?.addEventListener('abort', onAbort)

  const wait = (ms: number, then: () => void) => {
    clearTimer()
    phaseStartedAt = clock.now()
    phaseLengthMs = ms
    cancel = clock.schedule(() => {
      cancel = null
      then()
    }, ms)
  }

  const complete = () => {
    clearTimer()
    phase = 'complete'
    notify()
  }

  let hold: (offsetMs: number) => void

  const next = () => {
    if (index + 1 >= timeline.shots.length) {
      complete()
      return
    }
    select(index + 1, 0)
  }

  hold = (offsetMs: number) => {
    const current = shot()
    if (!current) {
      complete()
      return
    }
    phase = 'hold'
    notify()
    wait(Math.max(0, current.dwellMs - offsetMs), next)
    // Report the position as if the hold started `offsetMs` ago.
    phaseStartedAt -= offsetMs
  }

  const select = (to: number, offsetMs: number) => {
    if (options.signal?.aborted) return
    index = to
    const current = shot()
    if (!current) {
      complete()
      return
    }
    phase = 'select'
    notify()
    phase = 'travel'
    options.travel?.(current, index)
    notify()
    wait(travelMs, () => hold(offsetMs))
  }

  return {
    start: (fromMs = 0) => {
      if (timeline.shots.length === 0) {
        complete()
        return
      }
      const { index: at, offsetMs } = seekTimeline(timeline, fromMs)
      select(at, offsetMs)
    },
    pause: () => {
      if (phase !== 'travel' && phase !== 'hold') return
      remainingMs = Math.max(0, phaseLengthMs - (clock.now() - phaseStartedAt))
      resumeTo = phase
      clearTimer()
      phase = 'paused'
      notify()
    },
    resume: () => {
      if (phase !== 'paused' || resumeTo === null) return
      const lane = resumeTo
      resumeTo = null
      const current = shot()
      if (!current) {
        complete()
        return
      }
      phase = lane
      notify()
      if (lane === 'hold') {
        const offset = current.dwellMs - remainingMs
        wait(remainingMs, next)
        phaseStartedAt -= offset
      } else {
        wait(remainingMs, () => hold(0))
      }
    },
    stop: () => {
      options.signal?.removeEventListener('abort', onAbort)
      stop()
    },
    seek: (ms) => {
      if (timeline.shots.length === 0) return
      const { index: at, offsetMs } = seekTimeline(timeline, ms)
      const wasPaused = phase === 'paused' || phase === 'idle'
      clearTimer()
      select(at, offsetMs)
      if (wasPaused) {
        // Land on the shot but stay paused, so scrubbing never starts play.
        clearTimer()
        remainingMs = travelMs
        resumeTo = 'travel'
        phase = 'paused'
        notify()
      }
    },
    state,
  }
}
