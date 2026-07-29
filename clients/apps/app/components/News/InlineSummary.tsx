import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useOutceptionClient } from '@/providers/OutceptionClientProvider'
import { useLocale, useT } from '@/providers/LocaleProvider'
import { newsApi, openExternalUrl } from '@/utils/news'
import { KICKER_STYLE } from './newsStyles'
import { useEffect, useRef, useState } from 'react'
import { ScrollView } from 'react-native'

// A first-ever tap generates the summary live server-side; nobody should sit
// on a skeleton that whole time. Past this budget the panel STAYS and offers
// the article (generation continues server-side, so the NEXT tap serves from
// cache) — yanking the reader into the browser mid-wait lost their place on
// the wall, which the web version never did.
const SUMMARY_WAIT_MS = 10_000
// The web streams and types the summary out; the app fetches in one piece,
// so the same liveliness comes from typing the landed text over this budget.
const TYPE_OUT_MAX_MS = 600
// Long summaries scroll inside the panel instead of being sliced by the
// card's overflow (mirrors the web's maxHeight + overflow-y auto).
const MAX_PANEL_HEIGHT = 240

type State =
  | { kind: 'loading' }
  | { kind: 'slow' }
  | { kind: 'writing'; text: string }
  | { kind: 'done'; text: string; teaser: boolean; source?: string }

/** The AI summary, expanded inline right under the tapped headline — the
 * app twin of the web's InlineSummary: typed out as it "arrives", capped and
 * scrollable when long, and patient when generation is slow. Only a summary
 * that is unavailable before anything is shown sends the reader straight to
 * the article (same as the web's availability pre-check). */
export const InlineSummary = ({
  url,
  sourceName,
  onClose,
}: {
  url: string
  sourceName?: string
  onClose: () => void
}) => {
  const t = useT()
  const locale = useLocale()
  const { outception } = useOutceptionClient()
  const [state, setState] = useState<State>({ kind: 'loading' })
  // Per-run token: each effect run claims the next id, and every async
  // continuation checks it still holds the CURRENT id before touching state —
  // a shared boolean can't tell "this run was cancelled" from "a newer run
  // started", so a stale continuation could leak into the new run's panel.
  const runId = useRef(0)
  const typer = useRef<number | null>(null)

  useEffect(() => {
    const run = ++runId.current
    let deadline: ReturnType<typeof setTimeout> | undefined
    const openArticle = () => {
      if (runId.current !== run) return
      // Retire this run: nothing after the hand-off may touch the panel.
      runId.current++
      openExternalUrl(url)
      onClose()
    }
    const typeOut = (text: string, teaser: boolean) => {
      const started = Date.now()
      const step = () => {
        if (runId.current !== run) return
        const shown = Math.min(
          text.length,
          Math.ceil((Date.now() - started) / (TYPE_OUT_MAX_MS / text.length)),
        )
        if (shown >= text.length) {
          setState({ kind: 'done', text, teaser, source: sourceName })
          return
        }
        setState({ kind: 'writing', text: text.slice(0, shown) })
        typer.current = requestAnimationFrame(step)
      }
      typer.current = requestAnimationFrame(step)
    }
    const load = () => {
      const api = newsApi(outception)
      let landed = false
      deadline = setTimeout(() => {
        if (runId.current === run) setState({ kind: 'slow' })
      }, SUMMARY_WAIT_MS)
      // Both requests go out together, like the web does. Awaiting the
      // pre-check first spent a whole round trip before the server started
      // any work, and a known-unavailable article costs it nothing on the
      // summary route. The check is now only an early bail-out.
      api
        .summary(url, locale)
        .then((d) => {
          if (runId.current !== run) return
          if (deadline) clearTimeout(deadline)
          landed = true
          typeOut(d.summary, d.kind === 'teaser')
        })
        .catch(() => {
          if (deadline) clearTimeout(deadline)
          // The panel is already open: keep the reader's place and offer the
          // article instead of hijacking the tap into the browser.
          if (runId.current === run) setState({ kind: 'slow' })
        })
      api
        .summaryAvailable(url, locale)
        .then((avail) => {
          // A summary already on screen outranks a prognosis that said there
          // would be none; only a "no" that arrives first sends the reader on.
          if (!avail.available && !landed) openArticle()
        })
        .catch(() => {
          // The pre-check is an optimisation; the summary request decides.
        })
    }
    load()
    return () => {
      // Invalidate this run's continuations (a fresh run claims a new id).
      // The rule assumes refs hold DOM nodes; this one IS the live token —
      // bumping the current value at cleanup time is the entire mechanism.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      runId.current++
      if (deadline) clearTimeout(deadline)
      if (typer.current !== null) cancelAnimationFrame(typer.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, locale])

  const fullArticleChip = (
    <Touchable
      onPress={() => openExternalUrl(url)}
      accessibilityLabel={t('news.summary.readFull')}
    >
      <Box
        paddingVertical="spacing-4"
        paddingHorizontal="spacing-12"
        borderRadius="border-radius-999"
        borderWidth={1}
        borderColor="border"
        alignSelf="flex-start"
      >
        <Text variant="caption" color="text">
          {t('news.summary.readFull')}
        </Text>
      </Box>
    </Touchable>
  )

  return (
    <Box gap="spacing-4" paddingVertical="spacing-8">
      {state.kind === 'loading' ? (
        <Box
          gap="spacing-8"
          paddingVertical="spacing-4"
          accessible
          accessibilityRole="progressbar"
          accessibilityLabel={t('news.summary.loading')}
        >
          {[0, 1, 2].map((i) => (
            <Box
              key={i}
              height={10}
              borderRadius="border-radius-999"
              backgroundColor="border"
              style={{ width: `${92 - i * 14}%` }}
            />
          ))}
        </Box>
      ) : state.kind === 'slow' ? (
        <>
          <Text variant="caption" color="subtext" style={KICKER_STYLE}>
            {t('news.summary.title').toUpperCase()}
          </Text>
          <Text variant="bodySerif" color="subtext">
            {t('news.summary.slow')}
          </Text>
          {fullArticleChip}
        </>
      ) : state.kind === 'writing' ? (
        <>
          <Text variant="caption" color="subtext" style={KICKER_STYLE}>
            {t('news.summary.title').toUpperCase()}
          </Text>
          <Text variant="bodySerif">{state.text}</Text>
        </>
      ) : (
        <>
          <Text variant="caption" color="subtext" style={KICKER_STYLE}>
            {(state.teaser && state.source
              ? t('news.summary.fromPublisher', { source: state.source })
              : t('news.summary.title')
            ).toUpperCase()}
          </Text>
          <ScrollView
            style={{ maxHeight: MAX_PANEL_HEIGHT }}
            showsVerticalScrollIndicator
            persistentScrollbar
            nestedScrollEnabled
          >
            <Text variant="bodySerif">{state.text}</Text>
          </ScrollView>
          <Box
            flexDirection="row"
            alignItems="center"
            gap="spacing-8"
            paddingTop="spacing-4"
          >
            {fullArticleChip}
            <Box flex={1}>
              <Text variant="caption" color="subtext">
                {state.teaser
                  ? t('news.summary.publisherByline')
                  : t('news.summary.byline')}
              </Text>
            </Box>
          </Box>
        </>
      )}
    </Box>
  )
}
