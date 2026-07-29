'use client'

import { useLocale, useT } from '@/providers/locale'
import { safeExternalHref } from '@/utils/news'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { useEffect, useRef, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

// A first-ever tap on an article makes the server fetch + summarize it, which
// can run long; nobody should watch a blinking caret that whole time. Past
// this budget with nothing written yet, the panel offers the article link
// instead (generation continues server-side, so the NEXT tap is instant).
const SUMMARY_WAIT_MS = 10_000

// A whole result (cache hit, publisher teaser) is typed out rather than
// dropped in at once, so every tap reads the same way: about half a second
// for a typical summary, never longer than this.
const TYPE_OUT_MAX_MS = 600

type Event =
  | { text: string; kind?: string }
  | { delta: string }
  | { done: true; kind?: string }
  | { error: string }

/** Read a server-sent-event body and hand each JSON event to `onEvent`. */
const readEvents = async (
  body: ReadableStream<Uint8Array>,
  onEvent: (event: Event) => void,
) => {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let end = buffer.indexOf('\n\n')
    while (end !== -1) {
      const frame = buffer.slice(0, end)
      buffer = buffer.slice(end + 2)
      for (const line of frame.split('\n')) {
        if (line.startsWith('data: ')) onEvent(JSON.parse(line.slice(6)))
      }
      end = buffer.indexOf('\n\n')
    }
  }
}

// The availability pre-check answers from what the server already knows, in
// a few milliseconds; nothing is drawn under the headline until it has. If
// it is slower than this the panel opens anyway rather than leaving the tap
// looking ignored.
const AVAILABILITY_WAIT_MS = 400

// How the expanded panel shares the card with the rest of the list. The app
// keeps reading down the headlines under its summary; a web card that gave the
// panel every remaining pixel read as though the story list had vanished. So
// the panel yields enough space for this many whole headlines below it…
const ROWS_BELOW = 2
// …but is never squeezed under this (short cards would leave a panel too small
// to read; it scrolls internally instead)…
const MIN_PANEL_PX = 140
// …nor stretched past this on a tall card, where the extra height would buy
// nothing but a longer wall of text.
const MAX_PANEL_PX = 240

/** The AI summary, expanded inline right under the tapped headline. The tap
 * first asks whether a summary can be expected at all; articles known to be
 * unavailable (videos, paywalls and bot walls seen before, exhausted budget)
 * open directly, without a loading state that ends in a redirect. Otherwise
 * the summary loads under the headline — and when it still fails there is no
 * apology message: the reader gets the article. When it merely takes too
 * long, the panel stays put with the article link (navigating the tab away
 * that long after the tap would yank the reader off the wall). */
export const InlineSummary = ({
  url,
  sourceName,
  onClose,
}: {
  url: string
  sourceName: string
  /** Called when the panel gives up and opens the article, so the row can
   * collapse and the next tap starts fresh. */
  onClose?: () => void
}) => {
  const t = useT()
  const locale = useLocale()
  const [state, setState] = useState<
    | { kind: 'checking' }
    // The panel's last word without a summary: the stream ran out of time,
    // or the server said no after the reader had already settled in.
    | { kind: 'slow' }
    | { kind: 'unavailable' }
    // `writing` while text is still arriving (caret shown); `done` once final.
    | { kind: 'writing' | 'done'; text: string; teaser: boolean }
    | { kind: 'failed' }
  >({ kind: 'checking' })

  // Latest callback without re-running the fetch effect when the parent
  // re-renders with a new closure.
  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    let alive = true
    let settled = false
    let loadingShown = false
    const controller = new AbortController()
    const openArticle = () => {
      // Once the panel has had its last word the link is already on screen;
      // a late failure must not navigate the reader away.
      if (!alive || settled) return
      if (loadingShown) {
        // The reader has been watching "Summarizing…": a verdict now is a
        // message with the link, not a jump to another tab seconds after
        // the tap.
        settled = true
        setState({ kind: 'unavailable' })
        return
      }
      alive = false
      setState({ kind: 'failed' })
      onCloseRef.current?.()
      // Feed URLs are untrusted: only http(s) ever reaches navigation.
      const href = safeExternalHref(url)
      if (!href) return
      // window.open can be blocked this long after the tap, so fall back to
      // same-tab navigation.
      const win = window.open(href, '_blank', 'noopener,noreferrer')
      if (!win) window.location.assign(href)
    }
    let typer: number | null = null
    const showLoading = () => {
      if (!alive) return
      loadingShown = true
      setState((s) =>
        s.kind === 'checking'
          ? { kind: 'writing', text: '', teaser: false }
          : s,
      )
    }
    const showSlow = () => {
      if (!alive) return
      settled = true
      setState((s) => (s.kind === 'writing' && s.text ? s : { kind: 'slow' }))
    }
    // Whole results are typed out; streamed ones arrive piece by piece.
    const typeOut = (text: string, teaser: boolean) => {
      const started = performance.now()
      const duration = Math.min(TYPE_OUT_MAX_MS, text.length * 1.5)
      const reduced = window.matchMedia(
        '(prefers-reduced-motion: reduce)',
      ).matches
      const step = () => {
        if (!alive) return
        const shown = reduced
          ? text.length
          : Math.round(
              Math.min(1, (performance.now() - started) / duration) *
                text.length,
            )
        if (shown >= text.length) {
          setState({ kind: 'done', text, teaser })
          return
        }
        setState({ kind: 'writing', text: text.slice(0, shown), teaser })
        typer = requestAnimationFrame(step)
      }
      step()
    }
    const deadline = setTimeout(showSlow, SUMMARY_WAIT_MS)
    const checkDeadline = setTimeout(showLoading, AVAILABILITY_WAIT_MS)
    const params = new URLSearchParams({ url, lang: locale })
    const { signal } = controller
    // Both requests go out together: a known-unavailable article costs the
    // server nothing on the summary route, and a summarizable one is not made
    // to wait for the check.
    fetch(`${API}/v1/news/summary/available?${params}`, {
      signal,
      credentials: 'include',
    })
      .then(async (r) => {
        if (!r.ok) throw new Error(String(r.status))
        const d = (await r.json()) as { available: boolean }
        clearTimeout(checkDeadline)
        if (d.available) showLoading()
        else openArticle()
      })
      .catch(() => {
        clearTimeout(checkDeadline)
        showLoading()
      })
    let written = ''
    fetch(`${API}/v1/news/summary/stream?${params}`, {
      signal,
      credentials: 'include',
    })
      .then(async (r) => {
        if (!r.ok || !r.body) throw new Error(String(r.status))
        await readEvents(r.body, (event) => {
          if (!alive) return
          clearTimeout(checkDeadline)
          if ('error' in event) {
            // An explicit error event after deltas means the server REJECTED
            // what it streamed (mixed script, no article) — keeping it on
            // screen shipped the exact garbage the validators exist to stop.
            // Only a silent connection drop keeps partial text below.
            written = ''
            throw new Error(event.error)
          }
          if ('text' in event) {
            clearTimeout(deadline)
            written = event.text
            typeOut(event.text, event.kind === 'teaser')
            return
          }
          if ('delta' in event) {
            clearTimeout(deadline)
            written += event.delta
            setState({ kind: 'writing', text: written, teaser: false })
            return
          }
          if ('done' in event) {
            setState({ kind: 'done', text: written, teaser: false })
          }
        })
        if (alive && !written) throw new Error('empty')
      })
      .catch(() => {
        clearTimeout(deadline)
        // Text already on screen stays; only an empty panel sends the reader on.
        if (written) setState({ kind: 'done', text: written, teaser: false })
        else openArticle()
      })
    return () => {
      alive = false
      clearTimeout(deadline)
      clearTimeout(checkDeadline)
      if (typer !== null) cancelAnimationFrame(typer)
      // Collapsing the row (or a new url) must not leave the old requests
      // racing to set state on a panel that no longer exists.
      controller.abort()
    }
  }, [url, locale])

  // The deck card is a fixed-height clip box, so a summary opened under a
  // headline near its bottom would be cut off. On expand, scroll the card so
  // the tapped headline sits at the top (hidden rows keep their layout height,
  // so there is always room to scroll) and cap the summary to the space that
  // remains — it scrolls internally beyond that. Collapse restores the top.
  const rootRef = useRef<HTMLDivElement>(null)
  const scrollerRef = useRef<HTMLElement | null>(null)
  useEffect(() => {
    const content = rootRef.current?.firstElementChild
    if (!(content instanceof HTMLElement)) return
    const row = content.closest('li')
    // The card's clip box is the nearest ancestor that actually clips
    // (overflow hidden/auto/scroll); intermediate wrappers overflow visibly
    // and cannot scroll.
    let scroller = scrollerRef.current
    if (!scroller) {
      scroller = row?.parentElement ?? null
      while (
        scroller &&
        !/hidden|auto|scroll/.test(getComputedStyle(scroller).overflowY)
      ) {
        scroller = scroller.parentElement
      }
    }
    if (!row || !scroller) return
    scrollerRef.current = scroller
    const scrollerTop = scroller.getBoundingClientRect().top
    scroller.scrollTop += row.getBoundingClientRect().top - scrollerTop
    const room =
      scroller.getBoundingClientRect().bottom -
      content.getBoundingClientRect().top -
      8
    // Capped (like the app) rather than taking ALL remaining card space:
    // letting the panel fill the card hid every headline below it, so the
    // card read as summary-only. The reserve is measured from the rows that
    // will ACTUALLY sit under the panel — not a median of the whole list. A
    // median-sized reserve left the last visible row missing the card edge by
    // a few pixels, so the clip hook hid it whole and its layout ghost read
    // as a dead blank strip above the footer. Sizing against the real next
    // rows lands the panel's budget flush on a row boundary. (Hidden rows
    // keep their layout box, so they still measure.)
    const following: HTMLElement[] = []
    for (
      let sibling = row.nextElementSibling;
      sibling instanceof HTMLElement && following.length < ROWS_BELOW;
      sibling = sibling.nextElementSibling
    ) {
      if (sibling.getBoundingClientRect().height > 0) following.push(sibling)
    }
    const last = following[following.length - 1]
    const reserve = last
      ? last.getBoundingClientRect().bottom -
        following[0].getBoundingClientRect().top +
        12 // the list gap between the panel and its first following row
      : 0
    content.style.maxHeight = `${Math.max(
      MIN_PANEL_PX,
      Math.min(MAX_PANEL_PX, Math.round(room - reserve), Math.round(room)),
    )}px`
    // A capped summary scrolls inside the panel, but a razor clip through a
    // text line just looks broken (and nothing says "there is more"). The
    // fade over the last line is the cue; it lifts once the reader reaches
    // the end.
    const fade =
      'linear-gradient(to bottom, black calc(100% - 32px), transparent 100%)'
    const applyFade = () => {
      const overflowing = content.scrollHeight - content.clientHeight > 1
      const atEnd =
        content.scrollTop + content.clientHeight >= content.scrollHeight - 4
      const mask = overflowing && !atEnd ? fade : ''
      content.style.maskImage = mask
      content.style.webkitMaskImage = mask
    }
    applyFade()
    content.addEventListener('scroll', applyFade, { passive: true })
    // While the text is still typing out, it grows past the cap without a
    // scroll event ever firing — watch the content itself so the fade
    // appears the moment the first hidden line exists.
    const growth = new MutationObserver(applyFade)
    growth.observe(content, {
      childList: true,
      characterData: true,
      subtree: true,
    })
    // The clip hook re-measures on child-list changes and on scroll — never on
    // the style set above. Without this nudge the rows it hid while the panel
    // was at its full height stay hidden, and the space just freed for them
    // reads as blank card.
    scroller.dispatchEvent(new Event('scroll'))
    return () => {
      growth.disconnect()
      content.removeEventListener('scroll', applyFade)
      if (scrollerRef.current) scrollerRef.current.scrollTop = 0
    }
  }, [state.kind])

  if (state.kind === 'failed' || state.kind === 'checking') return null
  return (
    /* display:contents marker div — carries the attribute the row-clip hook
       uses to exempt the expanded row (Box has no data-attr passthrough). */
    <div ref={rootRef} data-inline-summary style={{ display: 'contents' }}>
      <Box
        flexDirection="column"
        rowGap="xs"
        paddingTop="s"
        // A step more than the top: the next headline's timestamp kicker sits
        // directly below, and with the panel scrolled (faded last line) the
        // two read as one crowded block without this.
        paddingBottom="m"
        minHeight={88}
        overflowY="auto"
      >
        {state.kind === 'slow' || state.kind === 'unavailable' ? (
          <>
            <span className="meta-kicker">{t('news.summary.title')}</span>
            <Text variant="caption" color="muted">
              {t(
                state.kind === 'slow'
                  ? 'news.summary.slow'
                  : 'news.summary.failed',
              )}
            </Text>
            <Box flexDirection="row" alignItems="center" paddingTop="xs">
              <a
                href={safeExternalHref(url)}
                target="_blank"
                rel="noopener noreferrer"
                className="ghost-pill"
              >
                {t('news.summary.readFull')}
              </a>
            </Box>
          </>
        ) : (
          <>
            <span className="meta-kicker">
              {state.teaser
                ? t('news.summary.fromPublisher', { source: sourceName })
                : t('news.summary.title')}
            </span>
            {/* One quiet line while the article is being read, then the
                text as it is written, with a caret until it is final —
                no skeleton bars. */}
            {state.kind === 'writing' && !state.text ? (
              <Text as="p" variant="caption" color="muted" aria-live="polite">
                {t('news.summary.loading')}
                <span className="type-caret" />
              </Text>
            ) : (
              <Text
                as="p"
                aria-live="polite"
                aria-busy={state.kind === 'writing'}
              >
                {state.text}
                {state.kind === 'writing' && (
                  <span
                    className="type-caret"
                    aria-label={t('news.summary.loading')}
                  />
                )}
              </Text>
            )}
            {state.kind === 'done' && (
              <Box
                flexDirection="row"
                alignItems="center"
                columnGap="m"
                paddingTop="xs"
              >
                <a
                  href={safeExternalHref(url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ghost-pill"
                >
                  {t('news.summary.readFull')}
                </a>
                <Text variant="caption" color="muted">
                  {state.teaser
                    ? t('news.summary.publisherByline')
                    : t('news.summary.byline')}
                </Text>
              </Box>
            )}
          </>
        )}
      </Box>
    </div>
  )
}
