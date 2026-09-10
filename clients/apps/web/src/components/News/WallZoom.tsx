'use client'

import { useWallBatch } from '@/hooks/queries/news'
import Lenis from 'lenis'
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
 * up painted on top of each other. Phones start wider because fewer tiles fit
 * across a narrow screen before they stop reading as a texture. */
const REST = { desktop: 125, mobile: 250 }
const ZOOMED = { desktop: 500, mobile: 750 }
const MOBILE_MAX = 1000

/** Tiles across a row, and rows in the mosaic. 9 x 10 is the density the
 * effect needs: enough that a row overflows the viewport hard at rest, few
 * enough that the DOM stays cheap. */
const PER_ROW = 9
const ROWS = 10

/** How far the top row is already grown when the wall opens, and how much of a
 * row's growth separates it from the row below. The stagger is what makes the
 * rows under the first one step DOWN in size rather than sitting at their
 * resting width in a block. */
const HEAD = 0.65
const STAGGER = 0.25

/** Pages of rows kept in the document. Three is two more than the reader can
 * see: one being read, one already passed, one coming. Past that the oldest is
 * cut away, which is what keeps the DOM the same size however long the reader
 * scrolls. */
const KEEP_PAGES = 3

/** Append another page once the reader is within this much of the bottom. Two
 * screens is far enough ahead that the new rows are laid out and at their
 * resting width long before they come into view. */
const LOOKAHEAD = 2

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

  // Muted words apply here exactly as they do on a card: a word the reader
  // muted must not come back just because the wall is being read as a mosaic.
  const mutedWords = useSyncExternalStore(
    subscribeMutedWords,
    getMutedWords,
    getMutedWordsServerSnapshot,
  )
  const sources = useMemo(() => {
    const all = data ?? []
    if (mutedWords.length === 0) return all
    return all.map((source) => ({
      ...source,
      items: (source.items ?? []).filter(
        (item) => !isMuted(item.title, mutedWords),
      ),
    }))
  }, [data, mutedWords])

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
  const [pages, setPages] = useState<number[]>([0])
  const nextPage = useRef(1)
  const appending = useRef(false)
  /** Pages currently in the document, readable from the scroll loop. */
  const pageCount = useRef(1)
  /** Height removed from above, waiting to be taken off the scroll. */
  const trimming = useRef<{ rows: number; height: number } | null>(null)

  const pageTiles = useMemo(
    () =>
      pages.map((page) =>
        buildTiles(sources, metas ?? [], PER_ROW * ROWS, page),
      ),
    [pages, sources, metas],
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
    appending.current = false
    pageCount.current = pages.length

    const cut = trimming.current
    if (cut) {
      trimming.current = null
      const lenis = lenisRef.current
      geometry.current.origin += cut.rows * geometry.current.step - cut.height
      const at = (lenis?.scroll ?? window.scrollY) - cut.height
      apply(at)
      if (lenis) lenis.scrollTo(at, { immediate: true, force: true })
      else window.scrollTo(0, at)
      return
    }
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
      const mobile = window.innerWidth < MOBILE_MAX
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
      g.span = g.step / STAGGER
      g.origin = (lenisRef.current?.scroll ?? window.scrollY) - g.span * HEAD
    }

    measure()
    // Paint the schedule before the first scroll, or the wall opens with every
    // row at its resting width - ninety tiles of colour and no headline.
    apply(window.scrollY)
    const onResize = () => {
      measure()
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
    const lenis = new Lenis()
    lenisRef.current = lenis
    lenis.on('scroll', ({ scroll }: { scroll: number }) => {
      apply(scroll)
      if (appending.current || trimming.current) return

      // Cut the oldest page once it is entirely behind the reader. Taking one
      // still on screen would move what they are looking at, which is the very
      // thing the scroll compensation exists to prevent.
      if (pageCount.current > KEEP_PAGES) {
        const last = rowsRef.current[ROWS - 1]
        if (last && last.getBoundingClientRect().bottom < 0) {
          const gap = rowGap()
          let height = 0
          for (let i = 0; i < ROWS; i += 1) {
            height += (rowsRef.current[i]?.offsetHeight ?? 0) + gap
          }
          trimming.current = { rows: ROWS, height }
          setPages((p) => p.slice(1))
          return
        }
      }

      const reach = window.innerHeight * LOOKAHEAD
      if (scroll + reach < document.documentElement.scrollHeight) return
      appending.current = true
      setPages((p) => [...p, nextPage.current++])
    })
    let frame = 0
    const raf = (time: number) => {
      lenis.raf(time)
      frame = requestAnimationFrame(raf)
    }
    frame = requestAnimationFrame(raf)

    return () => {
      cancelAnimationFrame(frame)
      lenis.destroy()
      lenisRef.current = null
      window.removeEventListener('resize', onResize)
    }
  }, [ready])

  if (!ready) return null

  return (
    <section ref={sectionRef} className="zoom-wall">
      {pageTiles.map((tiles, pageIndex) =>
        Array.from({ length: ROWS }, (_, rowIndex) => (
          <div key={`${pages[pageIndex]}-${rowIndex}`} className="zoom-row">
            {tiles
              .slice(rowIndex * PER_ROW, (rowIndex + 1) * PER_ROW)
              .map((tile) => (
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
                  <span className="zoom-tile-source">{tile.source}</span>
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
          onClose={() => setFocus(null)}
        />
      ) : null}
      {menuElement}
    </section>
  )
}
