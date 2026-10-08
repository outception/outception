'use client'

import { useT } from '@/providers/translate'
import { holds } from '@/utils/motion'
import {
  buildTimeline,
  createClock,
  createRunner,
  type AutoplayRunner,
  type RunnerState,
} from '@outception-com/news-core'
import { Pause, Play } from 'lucide-react'
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react'

/** How long the wall rests on each card at each speed. Three presets rather
 * than a free slider: a reader picks a pace, not a number, and nothing
 * goes under the five seconds a card needs to be read. */
const SPEEDS = [
  { id: 'slow', ms: 12000 },
  { id: 'normal', ms: 8000 },
  { id: 'fast', ms: 5000 },
] as const
const DEFAULT_SPEED = 2
const SPEED_KEY = 'news.autoplay.speed'
const TRAVEL_MS = 500

const readSpeed = (): number => {
  try {
    const stored = Number(localStorage.getItem(SPEED_KEY))
    return stored >= 1 && stored <= SPEEDS.length ? stored : DEFAULT_SPEED
  } catch {
    return DEFAULT_SPEED
  }
}

// The stored pace as an external store: read on the client, the default on
// the server, and every control re-reads when one changes it.
const speedListeners = new Set<() => void>()
const subscribeSpeed = (listener: () => void) => {
  speedListeners.add(listener)
  return () => {
    speedListeners.delete(listener)
  }
}
let sessionSpeed: number | null = null
const currentSpeed = (): number => sessionSpeed ?? readSpeed()
const storeSpeed = (speed: number) => {
  sessionSpeed = speed
  try {
    localStorage.setItem(SPEED_KEY, String(speed))
  } catch {
    // A private window or blocked storage: the choice lasts the page.
  }
  for (const listener of speedListeners) listener()
}

const clock = createClock(
  () => Date.now(),
  (fn, ms) => setTimeout(fn, ms),
  (handle) => clearTimeout(handle as ReturnType<typeof setTimeout>),
)

/**
 * The ambient play control: a play or pause button first, then the pace.
 * The runner lives in news-core; this binds it to the deck. It stops on any
 * interaction with the deck, or when the deck takes focus, and resumes only
 * from the control; it takes an animation hold so a hidden tab pauses it,
 * and it never starts under reduced motion.
 */
export const AutoplayControl = ({
  cardIds,
  index,
  goTo,
  interactionRef,
}: {
  cardIds: readonly string[]
  /** The card on top, so a manual move re-anchors the play head. */
  index: number
  goTo: (index: number) => void
  /** The deck element; any pointer or key on it stops play. */
  interactionRef: React.RefObject<HTMLElement | null>
}) => {
  const t = useT()
  const speed = useSyncExternalStore(
    subscribeSpeed,
    currentSpeed,
    () => DEFAULT_SPEED,
  )
  const dwellMs = SPEEDS[speed - 1]?.ms ?? SPEEDS[DEFAULT_SPEED - 1].ms
  const timeline = useMemo(
    () =>
      buildTimeline(
        cardIds.map((id) => ({ id, items: [] })),
        { minMs: dwellMs, maxMs: dwellMs },
      ),
    [cardIds, dwellMs],
  )
  const [state, setState] = useState<RunnerState | null>(null)
  const runner = useRef<AutoplayRunner | null>(null)
  const goToRef = useRef(goTo)
  useEffect(() => {
    goToRef.current = goTo
  }, [goTo])
  const release = useRef<(() => void) | null>(null)
  const indexRef = useRef(index)
  useEffect(() => {
    indexRef.current = index
  }, [index])
  // The wall plays itself on arrival, once: a later timeline (a card
  // dropped, a new pace) carries on only if it was playing, and never
  // restarts what the reader paused. The registry says no when motion is
  // reduced or the tab is hidden.
  const autoStarted = useRef(false)
  const playing = state?.phase === 'travel' || state?.phase === 'hold'
  const playingRef = useRef(false)
  useEffect(() => {
    playingRef.current = playing
  }, [playing])

  // One runner per timeline; stopping the old one on change.
  useEffect(() => {
    const wasPlaying = playingRef.current
    const r = createRunner({
      timeline,
      clock,
      travelMs: TRAVEL_MS,
      travel: (_shot, i) => goToRef.current(i),
      onChange: setState,
    })
    runner.current = r
    if ((!autoStarted.current || wasPlaying) && holds.canAnimate()) {
      autoStarted.current = true
      r.start(timeline.shots[indexRef.current]?.startMs ?? 0)
    }
    return () => {
      r.stop()
      release.current?.()
      release.current = null
    }
  }, [timeline])

  // The hold: while playing, the registry knows; when the tab hides or
  // motion is reduced, the registry says stop and the runner pauses.
  useEffect(() => {
    if (playing && !release.current) release.current = holds.take('autoplay')
    if (!playing && release.current) {
      release.current()
      release.current = null
    }
  }, [playing])
  useEffect(
    () =>
      holds.subscribe(() => {
        if (!holds.shouldAnimate('autoplay')) runner.current?.pause()
      }),
    [],
  )

  // Any interaction with the deck stops play; the control resumes it.
  useEffect(() => {
    const el = interactionRef.current
    if (!el) return
    const stop = () => runner.current?.pause()
    el.addEventListener('pointerdown', stop)
    el.addEventListener('keydown', stop)
    el.addEventListener('focusin', stop)
    el.addEventListener('wheel', stop, { passive: true })
    return () => {
      el.removeEventListener('pointerdown', stop)
      el.removeEventListener('keydown', stop)
      el.removeEventListener('focusin', stop)
      el.removeEventListener('wheel', stop)
    }
  }, [interactionRef])

  const toggle = () => {
    const r = runner.current
    if (!r) return
    if (playing) r.pause()
    else if (state?.phase === 'paused') r.resume()
    else r.start(timeline.shots[index]?.startMs ?? 0)
  }

  const speedLabel = (n: number) => {
    const preset = SPEEDS[n - 1] ?? SPEEDS[DEFAULT_SPEED - 1]
    return t(`news.autoplay.speeds.${preset.id}`, {
      seconds: String(preset.ms / 1000),
    })
  }

  return (
    <span className="autoplay-control" data-testid="autoplay">
      <button
        type="button"
        className="ghost-pill"
        onClick={toggle}
        aria-pressed={playing}
        aria-label={
          playing ? t('news.autoplay.pause') : t('news.autoplay.play')
        }
        title={playing ? t('news.autoplay.pause') : t('news.autoplay.play')}
      >
        {playing ? (
          <Pause size={14} aria-hidden />
        ) : (
          <Play size={14} aria-hidden />
        )}
      </button>
      <input
        type="range"
        className="autoplay-speed"
        min={1}
        max={SPEEDS.length}
        step={1}
        value={speed}
        list="autoplay-speeds"
        aria-label={t('news.autoplay.speed')}
        aria-valuetext={speedLabel(speed)}
        title={speedLabel(speed)}
        onChange={(e) => storeSpeed(Number(e.target.value))}
      />
      <datalist id="autoplay-speeds">
        {SPEEDS.map((preset, i) => (
          <option key={preset.id} value={i + 1} label={speedLabel(i + 1)} />
        ))}
      </datalist>
    </span>
  )
}
