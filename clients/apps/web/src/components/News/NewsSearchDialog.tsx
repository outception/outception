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
import { Star } from 'lucide-react'
import { useDeferredValue, useEffect, useMemo, useState } from 'react'
import { TopicChips } from './TopicChips'
import { useNewsColumn } from './NewsColumnContext'
import { followAll, unfollowAll } from './newsPrefsStore'
import { SourceBadge } from './SourceBadge'

// How many source rows to paint in the same frame the dialog opens — enough to
// fill the visible viewport so the user sees sources immediately; the rest
// stream in on the next frame.
const MAX_RENDER = 120

type SourceEntry = { source: NewsSourceMeta; haystack: string }

/** The "More" / ⌘K source palette: search the roster, narrow by topic, and
 * follow (star) sources into your deck. Followed sources are device-local
 * (localStorage) so this works without signing in. */
export const NewsSearchDialog = () => {
  const { searchOpen, setSearchOpen, isFocused, toggleFocus } = useNewsColumn()
  const { data: sources } = useNewsSources()
  const t = useT()
  const [query, setQuery] = useState('')
  const [topics, setTopics] = useState<string[]>([])

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
        .map((s) => ({
          source: s,
          haystack: `${s.name} ${s.title ?? ''} ${s.id}`.toLowerCase(),
        })),
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
      if (
        hasTopic &&
        (!source.column || !selectedColumns.has(source.column))
      )
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

  // Cap how many rows mount: the catalogue holds thousands of sources, and
  // mounting them all is what froze the dialog on open. We render at most
  // MAX_RENDER rows; the topic chips and the search field narrow the set, and
  // the count below always reflects the true total.
  const visibleResults = results.slice(0, MAX_RENDER)

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
              onValueChange={setQuery}
              wrapperClassName="rule-hairline px-4"
              className="border-0 bg-transparent shadow-none ring-0 focus:border-0 focus:ring-0 focus:outline-none"
            />

            <TopicChips
              present={presentColumns}
              topics={topics}
              onChange={setTopics}
            />
          </div>

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
                onClick={() => unfollowAll(resultIds)}
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
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  )
}
