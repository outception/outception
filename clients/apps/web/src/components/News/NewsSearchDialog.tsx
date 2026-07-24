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
import { NEWS_COLUMN_KEYS } from '@outception-com/i18n'
import { Star } from 'lucide-react'
import { useDeferredValue, useEffect, useMemo, useState } from 'react'
import { twMerge } from 'tailwind-merge'
import { useNewsColumn } from './NewsColumnContext'
import { followAll, unfollowAll } from './newsPrefsStore'

const capitalize = (id: string) => id.charAt(0).toUpperCase() + id.slice(1)

// How many source rows to paint in the same frame the dialog opens — enough to
// fill the visible viewport so the user sees sources immediately; the rest
// stream in on the next frame.
const FIRST_CHUNK = 24

const matches = (
  sources: NewsSourceMeta[],
  query: string,
  topics: string[],
): NewsSourceMeta[] => {
  const q = query.trim().toLowerCase()
  const hasTopic = topics.length > 0
  return sources.filter((s) => {
    if (s.redirect) return false
    if (hasTopic && (!s.column || !topics.includes(s.column))) return false
    if (!q) return true
    return [s.name, s.title ?? '', s.id].join(' ').toLowerCase().includes(q)
  })
}

/** The "More" / ⌘K source palette: search the roster, narrow by topic, and
 * follow (star) sources into your deck. Followed sources are device-local
 * (localStorage) so this works without signing in. */
export const NewsSearchDialog = () => {
  const { searchOpen, setSearchOpen, isFocused, toggleFocus } = useNewsColumn()
  const { data: sources } = useNewsSources()
  const t = useT()
  const [query, setQuery] = useState('')
  const [topics, setTopics] = useState<string[]>([])

  const allTopics = useMemo(() => {
    const set = new Set<string>()
    for (const s of sources ?? []) if (s.column) set.add(s.column)
    return Array.from(set).sort()
  }, [sources])

  const results = useMemo(
    () => matches(sources ?? [], query, topics),
    [sources, query, topics],
  )

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

  const toggleTopic = (id: string) =>
    setTopics((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )

  const columnLabel = (id: string) =>
    id in NEWS_COLUMN_KEYS
      ? t(NEWS_COLUMN_KEYS[id as keyof typeof NEWS_COLUMN_KEYS])
      : capitalize(id)

  const resultIds = useMemo(() => results.map((s) => s.id), [results])

  // Progressive render so the palette never feels laggy on open. The list holds
  // ~250 sources; mounting them all in the commit that opens the dialog blocks
  // first paint. Instead we render just the first screenful (FIRST_CHUNK)
  // synchronously — those rows paint together with the dialog chrome — then bump
  // to the full list on the next frame so the rest stream in without holding up
  // that first paint. (`useDeferredValue` keeps typing responsive; it doesn't
  // help the initial open, which is why the chunking is needed.) Paired with
  // `content-visibility:auto` on each row (below) so off-screen items skip
  // layout/paint and their icon isn't fetched until scrolled into view.
  const deferredResults = useDeferredValue(results)
  const [renderCount, setRenderCount] = useState(FIRST_CHUNK)
  useEffect(() => {
    if (!searchOpen) return
    const id = requestAnimationFrame(() =>
      setRenderCount(Number.POSITIVE_INFINITY),
    )
    // Reset to the first chunk on close so the next open paints instantly again
    // (cleanup covers every close path: button, ⌘K, Escape).
    return () => {
      cancelAnimationFrame(id)
      setRenderCount(FIRST_CHUNK)
    }
  }, [searchOpen])

  return (
    <Dialog open={searchOpen} onOpenChange={setSearchOpen}>
      <DialogContent
        className="paper-search h-[52vh] max-h-[85vh] min-h-[400px] w-full max-w-xl overflow-hidden rounded-2xl border-0 p-0 sm:rounded-2xl md:h-[62vh] md:min-h-[500px]"
        aria-describedby={undefined}
      >
        <DialogTitle className="sr-only">Search sources</DialogTitle>
        <Command
          shouldFilter={false}
          className="h-full rounded-3xl bg-transparent text-black dark:text-white"
        >
          <CommandInput
            placeholder={t('news.search.placeholder')}
            value={query}
            onValueChange={setQuery}
            wrapperClassName="rule-hairline px-4"
            className="border-0 bg-transparent shadow-none ring-0 focus:border-0 focus:ring-0 focus:outline-none"
          />

          <div className="rule-hairline flex flex-wrap items-center gap-1.5 px-3 py-2">
            <button
              type="button"
              onClick={() => setTopics([])}
              disabled={topics.length === 0}
              className="rounded-full px-2 py-1 text-xs font-medium text-gray-500 hover:text-black disabled:opacity-40 dark:text-neutral-400 dark:hover:text-white"
            >
              {t('news.search.all')}
            </button>
            <span className="ink-fill mx-1 h-4 w-px opacity-15" />
            {allTopics.map((id) => {
              const active = topics.includes(id)
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => toggleTopic(id)}
                  aria-pressed={active}
                  className={twMerge(
                    'rounded-full px-2.5 py-1 text-xs font-medium transition-colors',
                    active
                      ? 'text-white [background:var(--color-brand-700)]'
                      : 'paper-hover text-gray-500 dark:text-neutral-400',
                  )}
                >
                  {columnLabel(id)}
                </button>
              )
            })}
          </div>

          <div className="rule-hairline flex items-center gap-3 px-3 py-1.5">
            <button
              type="button"
              onClick={() => followAll(resultIds)}
              disabled={resultIds.length === 0}
              className="text-xs font-medium text-gray-500 hover:text-black disabled:opacity-40 dark:text-neutral-400 dark:hover:text-white"
            >
              {t('news.search.selectAll')}
            </button>
            <button
              type="button"
              onClick={() => unfollowAll(resultIds)}
              disabled={resultIds.length === 0}
              className="text-xs font-medium text-gray-500 hover:text-black disabled:opacity-40 dark:text-neutral-400 dark:hover:text-white"
            >
              {t('news.search.deselectAll')}
            </button>
            <span className="meta-kicker ml-auto">{resultIds.length}</span>
          </div>

          <CommandList className="max-h-none flex-1">
            <CommandEmpty>{t('news.search.empty')}</CommandEmpty>
            {deferredResults.slice(0, renderCount).map((s) => {
              const followed = isFocused(s.id)
              return (
                <CommandItem
                  key={s.id}
                  value={s.id}
                  onSelect={() => toggleFocus(s.id)}
                  className="mx-1 cursor-pointer rounded-xl px-3 py-2 [contain-intrinsic-size:0px_40px] [content-visibility:auto] data-[selected=true]:!bg-neutral-500/10 data-[selected=true]:!text-current"
                >
                  <span
                    className="mr-2 h-5 w-5 rounded-full bg-cover"
                    style={{
                      backgroundImage: `url(/news-icons/${s.id.split('-')[0]}.png)`,
                    }}
                  />
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
