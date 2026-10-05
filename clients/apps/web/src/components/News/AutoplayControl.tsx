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
import { useEffect, useMemo, useRef, useState } from 'react'

/** How long the wall rests on each card while playing itself. */
const CARD_DWELL_MS = 8000
const TRAVEL_MS = 500

const clock = createClock(
  () => Date.now(),
  (fn, ms) => setTimeout(fn, ms),
  (handle) => clearTimeout(handle as ReturnType<typeof setTimeout>),
)

/**
 * The ambient play control: a play or pause button and a seekable progress
 * line. The runner lives in news-core; this binds it to the deck. It stops
 * on any interaction with the deck and resumes only from the control, and
 * it takes an animation hold so a hidden tab pauses it.
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
  const timeline = useMemo(
    () =>
      buildTimeline(
        cardIds.map((id) => ({ id, items: [] })),
        { minMs: CARD_DWELL_MS, maxMs: CARD_DWELL_MS },
      ),
    [cardIds],
  )
  const [state, setState] = useState<RunnerState | null>(null)
  const runner = useRef<AutoplayRunner | null>(null)
  const goToRef = useRef(goTo)
  useEffect(() => {
    goToRef.current = goTo
  }, [goTo])
  const release = useRef<(() => void) | null>(null)

  // One runner per timeline; stopping the old one on change.
  useEffect(() => {
    const r = createRunner({
      timeline,
      clock,
      travelMs: TRAVEL_MS,
      travel: (_shot, i) => goToRef.current(i),
      onChange: setState,
    })
    runner.current = r
    return () => {
      r.stop()
      release.current?.()
      release.current = null
    }
  }, [timeline])

  const playing = state?.phase === 'travel' || state?.phase === 'hold'

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
    el.addEventListener('wheel', stop, { passive: true })
    return () => {
      el.removeEventListener('pointerdown', stop)
      el.removeEventListener('keydown', stop)
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

  const total = timeline.totalMs || 1
  const position = state?.positionMs ?? timeline.shots[index]?.startMs ?? 0

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
        className="autoplay-progress"
        min={0}
        max={total}
        step={100}
        value={Math.min(position, total)}
        aria-label={t('news.autoplay.progress')}
        onChange={(e) => runner.current?.seek(Number(e.target.value))}
      />
    </span>
  )
}
