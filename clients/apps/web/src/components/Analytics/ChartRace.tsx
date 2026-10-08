'use client'

import { holds, usePrefersReducedMotion } from '@/utils/motion'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  buildFrames,
  type RaceBar,
  type RaceMode,
  type RaceRow,
  type RaceSize,
} from './race'

const HOLD = 'chart-race'

/** The race's own play control, for the card around it. */
export interface RaceInstance {
  play: () => void
  pause: () => void
  isRunning: () => boolean
}

interface SizeSpec {
  /** Bars on screen at most. */
  topN: number
  /** A bar's height and the space under it, in pixels. */
  row: number
  gap: number
  /** Time per frame, in milliseconds. */
  tick: number
  /** The strip loops quietly; the larger sizes play once and stop. */
  loop: boolean
  /** Names, logos and values on the bars. */
  labels: boolean
}

const SIZES: Record<RaceSize, SizeSpec> = {
  strip: { topN: 4, row: 7, gap: 4, tick: 450, loop: true, labels: false },
  panel: { topN: 6, row: 34, gap: 6, tick: 600, loop: false, labels: true },
  sheet: { topN: 10, row: 40, gap: 8, tick: 700, loop: false, labels: true },
}
// A looping strip rests on its last frame before it starts again.
const LOOP_REST = 1800

const numbers = new Intl.NumberFormat('en')
const days = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
})

export interface ChartRaceProps {
  rows: readonly RaceRow[]
  mode: RaceMode
  size: RaceSize
  /** Display names for row names that are keys (the single-product race
   * sends `views` and `clicks`). */
  labels?: Record<string, string>
  title?: string
  /** The built race, for the card's own play control; null when gone. */
  onInstance?: (instance: RaceInstance | null) => void
  onPlaying?: (playing: boolean) => void
}

/** A bar chart race in the page's own glass and type: one row per name,
 * sliding to its rank as the frames go by, a tinted bar growing behind its
 * name, the value on the right, and the frame's day above with a thin
 * progress line. The race obeys the page's motion rules: it plays only
 * while the holds registry allows it, pauses when the tab hides or the
 * chart scrolls away and resumes when they return, and under reduced
 * motion shows its last frame and never moves. */
export const ChartRace = ({
  rows,
  mode,
  size,
  labels,
  title,
  onInstance,
  onPlaying,
}: ChartRaceProps) => {
  const spec = SIZES[size]
  const tick = spec.tick
  const race = useMemo(
    () =>
      buildFrames(rows, { cumulative: mode === 'products', topN: spec.topN }),
    [rows, mode, spec.topN],
  )
  const last = race.frames.length - 1
  const reduced = usePrefersReducedMotion()
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const slot = useRef<HTMLDivElement>(null)
  const onscreen = useRef(false)
  // Whether the race should run when the page lets it: set when a race is
  // built or replayed, cleared by a pause and by the last frame.
  const wantsPlay = useRef(false)
  const atEnd = useRef(false)

  const sync = () => {
    const allowed =
      wantsPlay.current && !reduced && holds.canAnimate(onscreen.current)
    setPlaying(allowed)
  }

  // A new race starts from its first frame; reduced motion shows the last.
  useEffect(() => {
    if (last < 0) return
    if (reduced) {
      wantsPlay.current = false
      setIndex(last)
      setPlaying(false)
      return
    }
    atEnd.current = false
    setIndex(0)
    wantsPlay.current = true
    sync()
    // sync reads refs and the motion setting, both current here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [race, reduced])

  // On screen or not: a race off screen pauses, and resumes on return.
  useEffect(() => {
    const el = slot.current
    if (!el || typeof IntersectionObserver === 'undefined') {
      onscreen.current = true
      sync()
      return
    }
    const observer = new IntersectionObserver(([entry]) => {
      onscreen.current = !!entry?.isIntersecting
      sync()
    })
    observer.observe(el)
    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // The registry's word: a hidden tab or reduced motion pauses the race.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => holds.subscribe(sync), [reduced])

  // A hold while running, so the page knows something animates.
  useEffect(() => {
    onPlaying?.(playing)
    if (!playing) return
    return holds.take(HOLD)
  }, [playing, onPlaying])

  // The clock: one frame per tick; at the end the strip rests and loops,
  // the larger sizes stop on their last frame.
  useEffect(() => {
    if (!playing || last < 0) return
    const atLast = index >= last
    const timer = window.setTimeout(
      () => {
        if (!atLast) {
          setIndex((current) => Math.min(current + 1, last))
        } else if (spec.loop) {
          setIndex(0)
        } else {
          atEnd.current = true
          wantsPlay.current = false
          setPlaying(false)
        }
      },
      atLast && spec.loop ? LOOP_REST : tick,
    )
    return () => window.clearTimeout(timer)
  }, [playing, index, last, tick, spec.loop])

  // The card's own play control, through the page's rules.
  useEffect(() => {
    if (!onInstance) return
    onInstance({
      play: () => {
        if (atEnd.current) {
          atEnd.current = false
          setIndex(0)
        }
        wantsPlay.current = true
        sync()
      },
      pause: () => {
        wantsPlay.current = false
        sync()
      },
      isRunning: () => wantsPlay.current,
    })
    return () => onInstance(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onInstance, race])

  if (last < 0) return null
  const frame = race.frames[Math.min(index, last)] ?? []
  const leader = frame[0]?.value || 1
  const step = spec.row + spec.gap
  // As many rows as the race ever shows, up to the size's limit: four cards
  // racing take four rows, not six with two empty.
  const slots = Math.min(spec.topN, Math.max(race.names.length, 1))
  const show = (name: string) =>
    labels && Object.hasOwn(labels, name) ? labels[name] : name
  const when = days.format(new Date(`${race.dates[index]}T00:00:00`))
  const finalFrame = race.frames[last] ?? []
  const summary = [
    title,
    finalFrame.map((bar) => `${show(bar.name)} ${bar.value}`).join(', '),
  ]
    .filter(Boolean)
    .join(': ')

  return (
    <div
      ref={slot}
      className={`chart-race chart-race-${size}${reduced ? ' chart-race-still' : ''}`}
      style={{ ['--race-tick' as string]: `${tick}ms` }}
      role="img"
      aria-label={summary}
    >
      {spec.labels ? (
        <div className="chart-race-head" aria-hidden>
          <span className="meta-kicker chart-race-when">{when}</span>
          <span className="chart-race-progress">
            <span
              style={{
                transform: `scaleX(${last > 0 ? index / last : 1})`,
              }}
            />
          </span>
        </div>
      ) : null}
      <div
        className="chart-race-bars"
        style={{ height: slots * step - spec.gap }}
        aria-hidden
      >
        {race.names.map((name) => {
          const rank = frame.findIndex((bar) => bar.name === name)
          const bar: RaceBar | undefined = rank >= 0 ? frame[rank] : undefined
          const width = bar ? Math.max(3, (bar.value / leader) * 100) : 0
          return (
            <div
              key={name}
              className="chart-race-row"
              data-lead={rank === 0 ? '' : undefined}
              style={{
                height: spec.row,
                transform: `translateY(${(bar ? rank : slots) * step}px)`,
                opacity: bar ? 1 : 0,
              }}
            >
              <span
                className="chart-race-fill"
                style={{ width: `${width}%` }}
              />
              {spec.labels ? (
                <>
                  <span className="chart-race-name">
                    <span className="chart-race-label">{show(name)}</span>
                  </span>
                  <span className="chart-race-value">
                    {bar ? numbers.format(bar.value) : ''}
                  </span>
                </>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
