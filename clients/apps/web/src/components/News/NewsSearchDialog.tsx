'use client'

import { useNewsSources } from '@/hooks/queries/news'
import type { NewsSourceMeta } from '@/utils/news'
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from '@outception-com/ui/components/ui/command'
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@outception-com/ui/components/ui/dialog'
import { useT } from '@/providers/locale'
import { NEWS_TOPIC_GROUPS } from '@outception-com/i18n'
import { Star, X } from 'lucide-react'
import {
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react'
import { TemplateGallery } from './TemplateGallery'
import { TopicChips } from './TopicChips'
import { useNewsColumn } from './NewsColumnContext'
import {
  getMutedWords,
  getMutedWordsServerSnapshot,
  removeMutedWord,
  subscribeMutedWords,
} from './mutedWords'
import { followAll, setActiveTemplates, unfollowAll } from './newsPrefsStore'
import { SourceBadge } from './SourceBadge'

// Rows painted in the frame the dialog opens — a viewport-full, so sources
// appear instantly. More load only as the reader scrolls to the end (see the
// sentinel below): mounting the whole 7k-source catalogue up front pegged the
// main thread for seconds on mobile.
const MAX_RENDER = 120
const RENDER_BATCH = 120

type SourceEntry = { source: NewsSourceMeta; haystack: string }

/** The "More" / ⌘K source palette: search the roster, narrow by topic, and
 * follow (star) sources into your deck. Followed sources are device-local
 * (localStorage) so this works without signing in. */
export const NewsSearchDialog = () => {
  const { searchOpen, setSearchOpen, isFocused, toggleFocus } = useNewsColumn()
  // The full roster is only needed once the palette opens; fetching it lazily
  // keeps the multi-megabyte parse off the wall's first paint.
  const { data: sources } = useNewsSources(searchOpen)
  const t = useT()
  const [query, setQuery] = useState('')
  const [topics, setTopics] = useState<string[]>([])
  // Starter decks are the default view: a fresh visitor opening "Sources"
  // lands on the curated bundles, not the raw 8k-source list.
  const [templatesOpen, setTemplatesOpen] = useState(true)

  const presentColumns = useMemo(() => {
    const present = new Set<string>()
    for (const s of sources ?? []) if (s.column) present.add(s.column)
    return present
  }, [sources])

  // A selected chip means its whole group of columns; sub-topic chips
  // contribute single columns (see TopicChips).
  const selectedColumns = useMemo(() => {
    const set = new Set<string>()
    for (const id of topics) {
      const group = NEWS_TOPIC_GROUPS.find((g) => g.id === id)
      if (group) for (const c of group.columns) set.add(c)
      else set.add(id)
    }
    return set
  }, [topics])

  // Precompute each source's lowercased search text once (the catalogue holds
  // thousands of sources); rebuilding it per keystroke is what froze the input.
  const index = useMemo<SourceEntry[]>(
    () =>
      (sources ?? [])
        .filter((s) => !s.redirect)
        .map((s) => {
          const base = `${s.name} ${s.title ?? ''} ${s.id}`.toLowerCase()
          // Collapsed variant so one-word queries match spaced/punctuated
          // names: "laliga" → "La Liga", "seriea" → "Serie A".
          return {
            source: s,
            haystack: `${base} ${base.replace(/[^a-z0-9]/g, '')}`,
          }
        }),
    [sources],
  )

  // Defer the QUERY that drives filtering (not just the rendered results) so
  // typing stays responsive: React runs the heavy filter at a lower priority
  // and lets the keystroke repaint the input first.
  const deferredQuery = useDeferredValue(query)
  const results = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase()
    const hasTopic = topics.length > 0
    const out: NewsSourceMeta[] = []
    for (const { source, haystack } of index) {
      if (hasTopic && (!source.column || !selectedColumns.has(source.column)))
        continue
      if (q && !haystack.includes(q)) continue
      out.push(source)
    }
    return out
  }, [index, deferredQuery, topics, selectedColumns])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        setSearchOpen(!searchOpen)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [searchOpen, setSearchOpen])

  const resultIds = useMemo(() => results.map((s) => s.id), [results])

  // Start with a viewport's worth of rows, then grow only when the reader
  // scrolls the sentinel into view — so the DOM never holds more than what
  // has actually been looked at.
  const [renderLimit, setRenderLimit] = useState(MAX_RENDER)
  const [renderedFor, setRenderedFor] = useState(results)
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  // A new result set starts the window again. Adjusted during render rather
  // than in an effect: an effect would paint the old window first, then
  // immediately re-render with the reset one.
  if (results !== renderedFor) {
    setRenderedFor(results)
    setRenderLimit(MAX_RENDER)
  }
  useEffect(() => {
    const node = sentinelRef.current
    if (!node || renderLimit >= results.length) return
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setRenderLimit((n) => Math.min(n + RENDER_BATCH, results.length))
        }
      },
      { rootMargin: '400px' },
    )
    io.observe(node)
    return () => io.disconnect()
  }, [renderLimit, results.length, searchOpen])
  const visibleResults = results.slice(0, renderLimit)

  // Muted words live in localStorage (see mutedWords.ts); the store snapshot
  // keeps this section in sync when the headline menu adds one mid-session.
  const mutedWords = useSyncExternalStore(
    subscribeMutedWords,
    getMutedWords,
    getMutedWordsServerSnapshot,
  )

  return (
    <Dialog open={searchOpen} onOpenChange={setSearchOpen}>
      <DialogContent
        className="paper-search max-h-[85dvh] w-full max-w-xl overflow-y-auto rounded-2xl border-0 p-0 sm:rounded-2xl"
        aria-describedby={undefined}
      >
        <DialogTitle className="sr-only">
          {t('news.deck.searchTitle')}
        </DialogTitle>
        <Command
          shouldFilter={false}
          className="rounded-3xl bg-transparent text-black dark:text-white"
        >
          <div className="paper-search-header sticky top-0 z-10">
            <CommandInput
              placeholder={t('news.search.placeholder')}
              value={query}
              // Typing means the reader wants the list, not the gallery —
              // leave the Starters view so results are visible immediately.
              onValueChange={(value) => {
                setQuery(value)
                if (value) setTemplatesOpen(false)
              }}
              wrapperClassName="rule-hairline px-4"
              className="border-0 bg-transparent shadow-none ring-0 focus:border-0 focus:ring-0 focus:outline-none"
            />

            <TopicChips
              present={presentColumns}
              topics={topics}
              // Templates and topic filters are exclusive modes: picking a
              // topic leaves the gallery, opening the gallery clears the
              // filter — no stale chip state behind either view.
              onChange={(next) => {
                setTemplatesOpen(false)
                setTopics(next)
              }}
              templatesActive={templatesOpen}
              onToggleTemplates={() => {
                setTemplatesOpen((v) => !v)
                setTopics([])
              }}
            />
          </div>

          {/* Muted words: outside the sticky header so it scrolls away with
              the content; clicking a chip un-mutes the word. */}
          {mutedWords.length > 0 && (
            <div className="rule-hairline flex flex-wrap items-center gap-1.5 px-3 py-2">
              <span className="meta-kicker">{t('news.menu.mutedWords')}</span>
              {mutedWords.map((word) => (
                <button
                  key={word}
                  type="button"
                  onClick={() => removeMutedWord(word)}
                  className="paper-hover flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium text-gray-500 transition-colors dark:text-neutral-400"
                >
                  {word}
                  <X className="h-3 w-3 opacity-60" />
                </button>
              ))}
            </div>
          )}

          {templatesOpen ? (
            <TemplateGallery sources={sources ?? []} open={templatesOpen} />
          ) : (
            <CommandList className="max-h-none overflow-visible">
              <div className="rule-hairline flex items-center gap-3 px-3 py-1.5">
                <button
                  type="button"
                  onClick={() => followAll(resultIds)}
                  disabled={resultIds.length === 0}
                  className="rounded-full px-2 py-1 text-xs font-medium text-gray-500 transition-colors hover:text-black active:text-white active:[background:var(--color-brand-700)] disabled:opacity-40 dark:text-neutral-400 dark:hover:text-white"
                >
                  {t('news.search.selectAll')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    unfollowAll(resultIds)
                    // On the unfiltered view this empties the whole deck, so
                    // the template toggles must reset with it.
                    if (topics.length === 0) setActiveTemplates([])
                  }}
                  disabled={resultIds.length === 0}
                  className="rounded-full px-2 py-1 text-xs font-medium text-gray-500 transition-colors hover:text-black active:text-white active:[background:var(--color-brand-700)] disabled:opacity-40 dark:text-neutral-400 dark:hover:text-white"
                >
                  {t('news.search.deselectAll')}
                </button>
                <span className="meta-kicker ml-auto">{resultIds.length}</span>
              </div>
              <CommandEmpty>{t('news.search.empty')}</CommandEmpty>
              {visibleResults.map((s) => {
                const followed = isFocused(s.id)
                return (
                  <CommandItem
                    key={s.id}
                    value={s.id}
                    onSelect={() => toggleFocus(s.id)}
                    className="mx-1 cursor-pointer rounded-xl px-3 py-2 [contain-intrinsic-size:0px_40px] [content-visibility:auto] data-[selected=true]:!bg-neutral-500/10 data-[selected=true]:!text-current"
                  >
                    <span className="mr-2 inline-flex">
                      <SourceBadge
                        id={s.id}
                        name={s.name}
                        logo={s.logo}
                        size={20}
                      />
                    </span>
                    <span>{s.name}</span>
                    {s.title && (
                      <span className="meta-kicker ml-2">{s.title}</span>
                    )}
                    <Star
                      className={`ml-auto h-4 w-4 ${followed ? 'fill-current' : 'opacity-30'}`}
                    />
                  </CommandItem>
                )
              })}
              <div ref={sentinelRef} aria-hidden />
            </CommandList>
          )}
        </Command>
      </DialogContent>
    </Dialog>
  )
}
