'use client'

import { useDefaultCards, useWallSourceMetas } from '@/hooks/queries/news'
import { type NewsSourceMeta } from '@/utils/news'
import { useEffect, useMemo, useState } from 'react'
import { NewsColumnProvider } from './NewsColumnContext'
import { NewsSourceCard } from './NewsSourceCard'

/**
 * The wall as a hand of cards.
 *
 * Cards fan out in a half circle the way a dealt hand sits in a fist: each one
 * pivoted a few degrees further round a point far below the screen, so they
 * splay from a single hinge rather than being placed one by one. Pick a card
 * and it rises out of the fan, straightens, and grows - while the cards on
 * either side lean away to make the room for it, which is what a hand does
 * when you pull a card halfway out to look at it.
 *
 * Every card is REAL - the same component the wall uses, so the one you pull
 * out has live headlines, working links and the AI summary on tap. This is
 * CSS 3D on actual elements: nothing here is painted into a texture, so the
 * text stays sharp, selectable and readable by a screen reader at any size.
 */

/** Degrees between neighbouring cards in the fan. */
const SPREAD = 7.5
/** How far below the cards the fan's hinge sits, in pixels. Larger makes a
 * shallower, wider arc; this is what turns a rotation into a fan. */
const HINGE = 900
/** How far a neighbour leans away to make room for the chosen card. */
const MAKE_ROOM = 9

const Hand = () => {
  const [picked, setPicked] = useState<string | null>(null)

  const { data: defaultIds } = useDefaultCards(true)
  const ids = useMemo(() => (defaultIds ?? []).slice(0, 11), [defaultIds])
  const { data: allMetas } = useWallSourceMetas(ids)
  // The metas query accumulates across card sets, so narrow it back to this
  // hand's ids - and keep the card set's order, which the map does not.
  const metas = useMemo(() => {
    const byId = new Map((allMetas ?? []).map((m) => [m.id, m]))
    return ids.map((id) => byId.get(id)).filter((m): m is NewsSourceMeta => !!m)
  }, [allMetas, ids])

  useEffect(() => {
    if (!picked) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setPicked(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [picked])

  const pickedIndex = metas.findIndex((m) => m.id === picked)

  return (
    <div
      className="relative flex h-[84svh] w-full items-end justify-center overflow-hidden"
      // The shared vanishing point. On the container rather than per card, so
      // the whole hand is seen from ONE eye - per-card perspective gives each
      // its own and the fan stops reading as a single object.
      style={{ perspective: '1800px' }}
      onClick={() => setPicked(null)}
      role="presentation"
    >
      {metas.map((meta, i) => {
        const middle = (metas.length - 1) / 2
        const fromMiddle = i - middle
        const isPicked = meta.id === picked
        // Cards to either side of the chosen one lean away from it.
        const room =
          pickedIndex < 0 || isPicked
            ? 0
            : (i < pickedIndex ? -1 : 1) * MAKE_ROOM
        const angle = fromMiddle * SPREAD + room

        const transform = isPicked
          ? 'translateY(-16%) scale(1.06)'
          : `rotate(${angle}deg)`

        return (
          <div
            key={meta.id}
            className={`paper-sheet absolute bottom-[-8%] h-[560px] w-[400px] overflow-hidden rounded-2xl transition-[transform,box-shadow] duration-500 ease-[cubic-bezier(.16,1,.3,1)] ${
              isPicked ? 'z-30 shadow-2xl' : ''
            }`}
            style={{
              // The hinge: rotating about a point far below turns a plain
              // rotation into a fan, the way a hand pivots at the fist.
              transformOrigin: `50% ${HINGE}px`,
              transform,
              // Later cards sit in front, so the fan overlaps like a real
              // hand - except the chosen one, which comes over everything.
              zIndex: isPicked ? 30 : i,
            }}
          >
            {/* The source's colour tab, as on the wall's own cards. */}
            <span
              aria-hidden
              className="absolute top-0 left-6 z-10 h-1 w-10 rounded-b-full opacity-90"
              style={{ backgroundColor: meta.color }}
            />
            {/* A card still in the hand is a THING TO PICK, not a card to
                read: it is rotated, overlapped and mostly hidden, so its own
                links are unusable. This layer takes the whole click and the
                card beneath goes inert - which also keeps the card's own
                buttons out of a button, which is invalid HTML and exactly
                what React was complaining about. Pulled out, the layer goes
                and every link and the summary work normally. */}
            {isPicked ? null : (
              <button
                type="button"
                className="absolute inset-0 z-20 cursor-pointer hover:brightness-[1.02]"
                aria-label={`Pick out ${meta.name}`}
                onClick={(e) => {
                  e.stopPropagation()
                  setPicked(meta.id)
                }}
              />
            )}
            {/* `upcoming` until picked: every card fetches its headlines once
                so the fan is real from the start, but only the card being read
                joins the polling loop. */}
            <div className={isPicked ? '' : 'pointer-events-none'}>
              <NewsSourceCard
                source={meta}
                active={isPicked}
                upcoming={!isPicked}
              />
            </div>
          </div>
        )
      })}

      {metas.length === 0 ? (
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-sm text-neutral-500">
          Dealing the hand…
        </div>
      ) : null}
    </div>
  )
}

/**
 * The real card reaches for the wall's column context (to report a source
 * that failed to load, among other things), and it is not optional - without
 * a provider the card throws and takes the whole route down with it. The
 * landing page gets one from its layout; this route brings its own.
 */
export const CardHand = () => (
  <NewsColumnProvider>
    <Hand />
  </NewsColumnProvider>
)
