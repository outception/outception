'use client'

import { useWallBatch } from '@/hooks/queries/news'
import Lenis from 'lenis'
import { useLocale } from '@/providers/locale'
import { useIsMobileMedia } from '@/utils/mobile'
import OutceptionTimeAgo from '@outception-com/ui/components/atoms/OutceptionTimeAgo'
import { isSummarizable, type NewsSourceMeta } from '@/utils/news'
import { buildTiles, type Tile } from './wallTiles'
import { useHeadlineMenu } from './HeadlineMenu'
import {
  getMutedWords,
  getMutedWordsServerSnapshot,
  isMuted,
  subscribeMutedWords,
} from './mutedWords'
import { SourceBadge } from './SourceBadge'
import { WallZoomFocus } from './WallZoomFocus'
import {
  startTransition,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react'

/** Row width at rest and fully zoomed, as a percentage of the section. The row
 * is centred, so growing it pushes the middle at the reader and slides the
 * edges out of frame. Growing the real WIDTH, never a transform: a transform
 * scales how a row is drawn without changing the room it takes, so rows ended
 * up painted on top of each other. */
const REST = { desktop: 125, mobile: 190 }
const ZOOMED = { desktop: 440, mobile: 500 }

/**
 * Tiles across a row, and rows in the mosaic.
 *
 * Nine across is the density the effect needs on a wide screen: enough that a
 * row overflows it hard at rest, few enough that the DOM stays cheap. A phone
 * cannot carry nine - it is a third of the width, so nine tiles made each row a
 * shallow band and the screen showed eight of them at once, a grid rather than
 * something you are flying into.
 *
 * Five is what a phone takes, and the count decides the zoom. Five across at
 * full zoom puts ONE tile across the width of the screen, which is the most a
 * headline can have before it starts running off both edges. Three across, the
 * first try, put a grown tile at nearly twice the screen and cut every headline
 * in half.
 *
 * Odd on both, so the middle column - the reader's own card order - sits dead
 * centre rather than half a tile to one side.
 */
const PER_ROW = { desktop: 9, mobile: 5 }
const ROWS = 10

/** How far the top row is already grown when the wall opens. */
const HEAD = 0.65

/**
 * How much of a row's growth separates it from the row below - what makes the
 * rows under the leading one step DOWN in size rather than sitting at their
 * resting width in a block.
 *
 * A phone takes a gentler one. Its screen is twice as tall in proportion, so a
 * quarter of a row's growth between neighbours dropped everything under the
 * leading row to resting width within three rows: one big row with a block of
 * small ones beneath it, which is the grid this view exists to escape. At a
 * sixth the falloff is slow enough that the screen holds the leading row and
 * most of the next, the way a wide screen does.
 */
const STAGGER = { desktop: 0.25, mobile: 0.15 }

/** Pages of rows kept in the document. Three is two more than the reader can
 * see: one being read, one already passed, one coming. Past that the oldest is
 * cut away, which is what keeps the DOM the same size however long the reader
 * scrolls. */
/** How many pages behind the reader keep their tiles, so turning back finds
 * the wall still there. Everything further back keeps its ROWS and drops its
 * tiles: the row holds the height it was worth, so the document never changes
 * size and there is nothing to compensate. Ahead of the reader nothing is ever
 * emptied - a page with no height would leave the document too short and the
 * wall would append forever trying to fill it. */
const KEPT_BEHIND = 1

/** How still the scroll has to be before the wall will move it. Long enough
 * that a finger's fling has landed, short enough that the reader never waits
 * for the wall to tidy up behind them. */
const QUIET_MS = 180

/** Append another page once the reader is within this much of the bottom. Two
 * screens is far enough ahead that the new rows are laid out and at their
 * resting width long before they come into view. */
const LOOKAHEAD = 3

/**
 * The wall as one mosaic you scroll INTO, rather than one card at a time.
 *
 * Each row sits wider than the screen and the section clips it. Scrolling
 * grows every row from 125% to 500%, so the tiles nearest the middle rush
 * forward while the edges leave the frame. The reference this is modelled on
 * did that with photographs.
 *
 * We zoom into TEXT instead, which is a deliberate change rather than a
 * compromise. Only about 40% of articles carry an image and the gaps cluster
 * by publisher, so a photo grid would have whole outlets missing. Headlines
 * exist for every source, and they reward the zoom: a tile that is texture at
 * rest becomes something you can actually read on the way in. Tile text is
 * sized in container units, so it scales with the tile rather than staying
 * put while the tile grows around it.
 */
export const WallZoom = ({
  ids,
  metas,
}: {
  ids: readonly string[]
  metas: readonly NewsSourceMeta[] | undefined
}) => {
  const sectionRef = useRef<HTMLElement>(null)
  const rowsRef = useRef<HTMLDivElement[]>([])
  const { data } = useWallBatch(ids, true)
  const mobile = useIsMobileMedia()
  const locale = useLocale()
  const perRow = mobile ? PER_ROW.mobile : PER_ROW.desktop

  // Muted words apply here exactly as they do on a card: a word the reader
  // muted must not come back just because the wall is being read as a mosaic.
  const mutedWords = useSyncExternalStore(
    subscribeMutedWords,
    getMutedWords,
    getMutedWordsServerSnapshot,
  )
  const sources = useMemo(() => {
    const all = data ?? []
    // Back into the reader's card order. The batch route answers from a cache
    // and makes no promise about order, and the middle column of the wall IS
    // that order - the country card first, then whatever they follow next.
    const byId = new Map(all.map((source) => [source.id, source]))
    const ordered = ids
      .map((id) => byId.get(id))
      .filter((source): source is (typeof all)[number] => source !== undefined)
    if (mutedWords.length === 0) return ordered
    return ordered.map((source) => ({
      ...source,
      items: (source.items ?? []).filter(
        (item) => !isMuted(item.title, mutedWords),
      ),
    }))
  }, [data, ids, mutedWords])

  // The wall goes on rather than starting over.
  //
  // It used to loop: reach the last row and the scroll jumped back to the top
  // with a fresh deal. However carefully the jump was timed it was still a cut,
  // and a cut in the middle of a scroll reads as a flash. So the wall grows
  // instead - another page of rows is laid down below before the reader gets
  // near the bottom, and the oldest page is cut away above them, off screen,
  // with the scroll moved by exactly the height that left. Nothing under the
  // reader's eye moves, and there is no end to arrive at.
  //
  // Each page is a pass through the sources at a different starting headline,
  // so what arrives from below has never been seen.
  // Opens on two pages. The wall used to open on one and lay a second above it
  // a frame after the first paint, which meant moving the scroll to hide it -
  // the flash on opening. With a page already in hand there is room to read
  // back from the start, and the next one is laid when the reader actually
  // moves, with a scroll event to hang it on.
  const [pages, setPages] = useState<number[]>([0, 1])
  const nextPage = useRef(2)
  const appending = useRef(false)
  /** Rows added above, waiting to be added to the scroll. */
  const prepending = useRef<number | null>(null)
  const prevPage = useRef(-1)
  /** The first page whose tiles are rendered. Pages outside the window keep
   * their rows and lose their tiles, which is what bounds the memory without
   * ever changing the height of the document. */
  const [live, setLive] = useState(0)
  const liveRef = useRef(0)
  /** Frozen row heights for pages whose tiles are gone, keyed by page and row
   * so a prepend cannot shuffle them. */
  const [frozen, setFrozen] = useState<Record<string, number>>({})
  const pagesRef = useRef<number[]>([])
  /** True while a compensating jump is being made. Moving the scroll makes the
   * smooth-scroll library emit a scroll event straight back at us, and the
   * handler is what asked for the jump in the first place - so without this it
   * answers its own event, asks for another page, and React tears the tree
   * down with "Maximum update depth exceeded". Seen in production. */
  const settling = useRef(false)

  const pageTiles = useMemo(
    () =>
      pages.map((page) => buildTiles(sources, metas ?? [], perRow, ROWS, page)),
    [pages, sources, metas, perRow],
  )

  /** Geometry the scroll loop reads every frame. A ref, not state: it changes
   * with the viewport, never with a render, and touching state here would put
   * a React update between the scroll and the paint. */
  const geometry = useRef({
    rest: REST.desktop,
    zoomed: ZOOMED.desktop,
    span: 1,
    step: 1,
    /** The scroll position at which the FIRST row on the page starts growing.
     * Moves when a page is cut from the top, by exactly enough to leave every
     * remaining row at the width it already had. */
    origin: 0,
  })
  const lenisRef = useRef<Lenis | null>(null)
  /** True from the render where the wall has headlines, which is the render
   * where its rows first exist in the document. The scroll loop waits for it,
   * rather than starting on an empty section and never looking again. */
  const ready = (pageTiles[0]?.length ?? 0) > 0

  // The tile the reader opened, brought to the middle of the screen with the
  // things a card gives a headline: summary, share, unfollow, the link.
  const [focus, setFocus] = useState<Tile | null>(null)
  const { menuElement, openMenu } = useHeadlineMenu()
  const metaById = useMemo(
    () => new Map((metas ?? []).map((m) => [m.id, m])),
    [metas],
  )
  const focusSource: NewsSourceMeta | null = focus
    ? (metaById.get(focus.id) ?? {
        id: focus.id,
        name: focus.source,
        color: focus.color,
        logo: focus.logo,
        interval: 0,
      })
    : null

  /** Write every row's width for a scroll position. Reads nothing from the
   * DOM, so no write can force the browser to redo layout mid-frame. */
  const apply = (scroll: number) => {
    const { rest, zoomed, span, step, origin } = geometry.current
    const rows = rowsRef.current
    for (let i = 0; i < rows.length; i += 1) {
      const row = rows[i]
      if (!row) continue
      const progress = Math.max(
        0,
        Math.min(1, (scroll - (origin + i * step)) / span),
      )
      const width = Math.round((rest + (zoomed - rest) * progress) * 10) / 10
      if (row.dataset.w === String(width)) continue
      row.dataset.w = String(width)
      row.style.width = `${width}%`
    }
  }

  const rowGap = () => {
    const section = sectionRef.current
    return section ? parseFloat(getComputedStyle(section).rowGap) || 0 : 0
  }

  // Rows come and go, so the list is rebuilt from the DOM whenever the pages
  // change - including the render where the wall's headlines first arrive,
  // which is when the rows exist at all. A layout effect, so it has run before
  // the scroll loop's effect below looks for them.
  useLayoutEffect(() => {
    const section = sectionRef.current
    if (!section) return
    rowsRef.current = Array.from(
      section.querySelectorAll<HTMLDivElement>('.zoom-row'),
    )

    /** Move the scroll to hide a change in the rows above, deaf to the scroll
     * events that move causes, until the next frame. */
    const settle = (at: number) => {
      settling.current = true
      apply(at)
      const lenis = lenisRef.current
      if (lenis) lenis.scrollTo(at, { immediate: true, force: true })
      else window.scrollTo(0, at)
      requestAnimationFrame(() => {
        settling.current = false
        appending.current = false
      })
    }

    // Rows arrived ABOVE the reader. They are past the top of the screen, so
    // they paint fully grown, which means the page grew by exactly their grown
    // pitch - scroll down by that much and nothing under the eye has moved.
    // The schedule needs no shift for the same reason: the rows below keep
    // their progress when index and scroll rise together by the same amount.
    const grown = prepending.current
    if (grown !== null) {
      prepending.current = null
      const g = geometry.current
      const from = lenisRef.current?.scroll ?? window.scrollY
      const origin = g.origin
      const gap = rowGap()

      // How much taller the page just got. It cannot be assumed: rows arriving
      // above are only fully grown when the reader is far enough down the
      // wall, and near the top the last of them are still part grown - assume
      // otherwise and the scroll overshoots by the difference, which lands the
      // reader in a stretch where every row has fallen back to resting width.
      //
      // So measure it, and let the schedule follow: shifting the origin by the
      // same amount is what leaves every row already on screen at exactly the
      // width it had. The measurement depends on the widths it produces, so it
      // settles in two passes rather than one.
      let added = grown * g.step
      for (let pass = 0; pass < 2; pass += 1) {
        g.origin = origin + added - grown * g.step
        apply(from + added)
        let height = 0
        for (let i = 0; i < grown; i += 1) {
          height += (rowsRef.current[i]?.offsetHeight ?? 0) + gap
        }
        if (Math.abs(height - added) < 1) break
        added = height
      }
      settle(from + added)
      return
    }

    // The document just changed height. Tell Lenis now - `dimensions` alone,
    // which measures without touching the scroll - so its limit is right in
    // this very frame. See the note on `autoResize` where Lenis is created.
    lenisRef.current?.dimensions.resize()

    // Rows that just arrived carry the resting width the stylesheet gives
    // them until the next scroll event. Put them on the schedule now, so a
    // page that lands while the wall is still does not sit there at the wrong
    // size waiting to be told.
    apply(window.scrollY)
    appending.current = false
  }, [pages, pageTiles])

  useEffect(() => {
    if (!ready) return
    const section = sectionRef.current
    if (!section || rowsRef.current.length === 0) return

    const reduced = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches

    // A row's growth is scheduled against the scroll position. Reading it off
    // the rows' live positions made each width depend on the layout it was
    // itself producing, and the rows nearest the bottom always lost.
    const measure = () => {
      const g = geometry.current
      g.rest = mobile ? REST.mobile : REST.desktop
      g.zoomed = mobile ? ZOOMED.mobile : ZOOMED.desktop
      const first = rowsRef.current[0]
      if (!first) return
      const held = first.style.width
      first.style.width = `${g.zoomed}%`
      const grown = first.offsetHeight
      first.style.width = held
      // One row's pitch once grown. Using it as the stagger is what makes a
      // page cut from the top cost the schedule exactly the height it costs
      // the page, so the two cancel.
      g.step = grown + rowGap()
      g.span = g.step / (mobile ? STAGGER.mobile : STAGGER.desktop)
      g.origin = (lenisRef.current?.scroll ?? window.scrollY) - g.span * HEAD
    }

    measure()
    // Paint the schedule before the first scroll, or the wall opens with every
    // row at its resting width - ninety tiles of colour and no headline.
    apply(window.scrollY)
    const onResize = () => {
      measure()
      lenisRef.current?.dimensions.resize()
      apply(lenisRef.current?.scroll ?? window.scrollY)
    }
    window.addEventListener('resize', onResize)

    if (reduced) {
      apply(Number.MAX_SAFE_INTEGER)
      return () => window.removeEventListener('resize', onResize)
    }

    // Lenis, not a hand-rolled wheel lerp.
    //
    // Mine called scrollTo every frame, which fights the browser's own scroll
    // rather than riding it. Lenis wraps native scroll, so sticky positioning
    // and accessibility keep working, and it keeps the DOM in step with scroll
    // frame for frame - the async gap between the two is where scroll-linked
    // animation jank actually comes from.
    // `syncTouch` is what makes a phone behave like a desktop here.
    //
    // Left off, a finger scrolls the page natively and the browser's own
    // momentum carries on long after the finger has gone. This view moves the
    // scroll to hide the pages it cuts from above, and moving the scroll does
    // not move that momentum with it - the fling resumes from where it was and
    // drags the reader back, so reading down got nowhere. A wheel has no
    // momentum of its own, which is why the desktop was always fine.
    //
    // Switched on, touch goes through the same path the wheel does: the
    // library owns the position, there is no native momentum to fight, and one
    // set of rules covers both.
    // `syncTouch` is what makes a phone behave like a desktop here, and Lenis
    // documents it as required on touch devices for a scroll that never ends.
    //
    // Left off, a finger scrolls the page natively and the browser's own
    // momentum carries on long after the finger has gone, which put the
    // library's idea of the position and the browser's out of step - the next
    // touch resynced them with a visible snap. Everything else is left at its
    // default; a multiplier of my own only made the touch feel wrong.
    // `autoResize` is OFF, and the wall measures for Lenis itself the moment
    // it changes the document. Left on, Lenis watches the document with a
    // ResizeObserver debounced by 250ms, and two things follow from that:
    //
    // - Its scroll LIMIT is stale for a quarter of a second after a page is
    //   laid below. A fling toward the bottom is clamped to the old end, so
    //   the wall stops dead there and the reader has to scroll again. That is
    //   the stall on a desktop.
    // - When the debounce fires, `resize()` snaps its target to wherever the
    //   scroll actually is, which throws away any inertia still in flight. On
    //   a phone that is the jolt at the very moment more of the wall arrives.
    const lenis = new Lenis({ syncTouch: true, autoResize: false })
    lenisRef.current = lenis

    // Housekeeping that has to MOVE the scroll to stay invisible: cutting the
    // oldest page from above, and laying a new one there. Both are done only
    // once the scroll has gone quiet.
    //
    // On a phone the page is scrolled by the browser's own momentum, and a
    // finger's fling is still travelling long after it has left the glass.
    // Moving the scroll in the middle of that does not move the momentum with
    // it, so the fling carries on from where it was and yanks the reader
    // straight back - which is why reading DOWN got nowhere while reading up,
    // where the cut almost never falls, was fine. A wheel has no momentum of
    // its own, which is why it never showed up on a desktop.
    let quiet = 0
    const housekeep = () => {
      if (settling.current || appending.current) return
      const scroll = lenis.scroll ?? window.scrollY

      // Which page the reader is in: the first row still on screen. Queried
      // fresh, not taken from the cached list - that list is rebuilt only when
      // the pages change, and a page appended a moment ago would be missing
      // from it. A page missed here is a page emptied with no height to hold,
      // which collapses it to nothing and drags the wall up by its full
      // height.
      const rows = Array.from(
        section.querySelectorAll<HTMLDivElement>('.zoom-row'),
      )
      let at = 0
      for (let i = 0; i < rows.length; i += 1) {
        if ((rows[i]?.getBoundingClientRect().bottom ?? 0) > 0) {
          at = Math.floor(i / ROWS)
          break
        }
      }
      const from = Math.max(0, at - KEPT_BEHIND)
      if (from !== liveRef.current) {
        // Pages leaving the window keep their ROWS - only their tiles go. The
        // row heights are frozen at what they are worth right now, so the
        // document does not change size by a single pixel and there is nothing
        // to compensate: no scroll to move, no index to shift, nothing for a
        // phone to paint a frame late. Every row above the reader is fully
        // grown, so the height it is frozen at is the height it would keep.
        const held: Record<string, number> = {}
        let covered = true
        for (let i = 0; i < from * ROWS; i += 1) {
          const cycle = pagesRef.current[Math.floor(i / ROWS)]
          const height = rows[i]?.offsetHeight
          if (cycle === undefined || !height) {
            covered = false
            break
          }
          held[`${cycle}-${i % ROWS}`] = height
        }
        // Only move the window once every row it leaves behind has a height to
        // hold. Emptying one that has not been measured is the collapse above.
        if (covered) {
          liveRef.current = from
          setFrozen((was) => ({ ...was, ...held }))
          setLive(from)
        }
      }

      // Reading back up the wall is endless too: a page arrives above before
      // the reader reaches the top, and the oldest page at the BOTTOM goes to
      // pay for it.
      if (scroll < window.innerHeight * LOOKAHEAD) {
        prepending.current = ROWS
        appending.current = true
        startTransition(() => setPages((p) => [prevPage.current--, ...p]))
      }
    }

    const onScroll = (scroll: number) => {
      apply(scroll)
      window.clearTimeout(quiet)
      quiet = window.setTimeout(housekeep, QUIET_MS)
      // Widths still track the position, but no new page is asked for while a
      // compensating jump is in flight - that is the loop this guards.
      if (settling.current || appending.current) return

      // Adding a page BELOW moves nothing, so it needs no compensation and can
      // happen mid-fling. This is the half that keeps reading down endless.
      const reach = window.innerHeight * LOOKAHEAD
      if (scroll + reach < document.documentElement.scrollHeight) return
      appending.current = true
      startTransition(() => setPages((p) => [...p, nextPage.current++]))
    }
    lenis.on('scroll', ({ scroll }: { scroll: number }) => onScroll(scroll))

    let frame = 0
    const raf = (time: number) => {
      lenis.raf(time)
      frame = requestAnimationFrame(raf)
    }
    frame = requestAnimationFrame(raf)

    return () => {
      window.clearTimeout(quiet)
      cancelAnimationFrame(frame)
      lenis.destroy()
      lenisRef.current = null
      window.removeEventListener('resize', onResize)
    }
  }, [ready, mobile])

  if (!ready) return null

  return (
    <section ref={sectionRef} className="zoom-wall">
      {pageTiles.map((tiles, pageIndex) =>
        Array.from({ length: ROWS }, (_, rowIndex) => (
          <div
            key={`${pages[pageIndex]}-${rowIndex}`}
            className="zoom-row"
            // A page outside the window keeps this row and loses its tiles,
            // holding the height they were worth. The row stays in the
            // document and in the schedule, so nothing below it moves and no
            // index shifts - there is simply nothing left to paint in it.
            style={
              pageIndex >= live
                ? undefined
                : { height: frozen[`${pages[pageIndex]}-${rowIndex}`] ?? 0 }
            }
          >
            {(pageIndex < live
              ? []
              : tiles.slice(rowIndex * perRow, (rowIndex + 1) * perRow)
            ).map((tile) => (
              <a
                key={tile.key}
                href={tile.href}
                target="_blank"
                rel="noopener noreferrer"
                className="zoom-tile"
                style={{ backgroundColor: tile.color }}
                title={tile.title}
                // Same bargain the card rows strike: a plain left click
                // brings the headline forward with its summary, while a
                // modified click (new tab, middle click) and the right-click
                // menu keep working as the browser and the cards define them.
                onClick={(e) => {
                  if (
                    e.metaKey ||
                    e.ctrlKey ||
                    e.shiftKey ||
                    e.altKey ||
                    e.button !== 0
                  )
                    return
                  if (!isSummarizable(tile.href)) return
                  e.preventDefault()
                  setFocus(tile)
                }}
                onContextMenu={(e) =>
                  openMenu(
                    e,
                    { id: tile.itemId, title: tile.title, url: tile.href },
                    { id: tile.id, name: tile.source },
                  )
                }
              >
                {/* SourceBadge, not a bare <img>: it already owns the
                      fallback chain for ~15 third-party logo hosts, so a dead
                      URL degrades to the bundled icon instead of an invisible
                      square. Fixed size on purpose - the tile grows 4x and the
                      logo should NOT grow with it. A mark blown up is exactly
                      the blurry result that argued against building this out
                      of pictures. */}
                <span className="zoom-tile-logo">
                  <SourceBadge id={tile.id} logo={tile.logo} size={18} />
                </span>
                <span className="zoom-tile-title">{tile.title}</span>
                <span className="zoom-tile-source">
                  {tile.source}
                  {/* The row kicker a card gives every headline. Same
                      component, same locale, same rounding. */}
                  {tile.pubDate ? (
                    <span className="zoom-tile-time">
                      <OutceptionTimeAgo
                        date={tile.pubDate}
                        locale={locale}
                        minPeriod={60}
                      />
                    </span>
                  ) : null}
                </span>
              </a>
            ))}
          </div>
        )),
      )}
      {focus && focusSource ? (
        <WallZoomFocus
          // Keyed by headline: opening another tile while one is open must
          // start a fresh summary, not keep writing the previous one.
          key={focus.key}
          title={focus.title}
          href={focus.href}
          source={focusSource}
          pubDate={focus.pubDate}
          updated={focus.updated}
          onClose={() => setFocus(null)}
        />
      ) : null}
      {menuElement}
    </section>
  )
}
