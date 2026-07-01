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
import { Star } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { twMerge } from 'tailwind-merge'
import { useNewsColumn } from './NewsColumnContext'

const topicLabel = (id: string) => id.charAt(0).toUpperCase() + id.slice(1)

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

  return (
    <Dialog open={searchOpen} onOpenChange={setSearchOpen}>
      <DialogContent
        className="glass-search h-[52vh] max-h-[85vh] min-h-[400px] w-full max-w-xl overflow-hidden rounded-3xl border-0 p-0 sm:rounded-3xl md:h-[62vh] md:min-h-[500px]"
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
            wrapperClassName="border-gray-100 px-4 dark:border-neutral-800"
            className="border-0 bg-transparent shadow-none ring-0 focus:border-0 focus:ring-0 focus:outline-none"
          />

          <div className="flex flex-wrap items-center gap-1.5 border-b border-gray-100 px-3 py-2 dark:border-neutral-800">
            <button
              type="button"
              onClick={() => setTopics([])}
              disabled={topics.length === 0}
              className="rounded-full px-2 py-1 text-xs font-medium text-gray-500 hover:text-black disabled:opacity-40 dark:text-neutral-400 dark:hover:text-white"
            >
              {t('news.search.all')}
            </button>
            <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-neutral-700" />
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
                      ? 'bg-red-500 text-white'
                      : 'glass-hover text-gray-500 dark:text-neutral-400',
                  )}
                >
                  {topicLabel(id)}
                </button>
              )
            })}
          </div>

          <CommandList className="max-h-none flex-1">
            <CommandEmpty>{t('news.search.empty')}</CommandEmpty>
            {results.map((s) => {
              const followed = isFocused(s.id)
              return (
                <CommandItem
                  key={s.id}
                  value={s.id}
                  onSelect={() => toggleFocus(s.id)}
                  className="mx-1 cursor-pointer rounded-xl px-3 py-2 data-[selected=true]:!bg-neutral-500/10 data-[selected=true]:!text-current"
                >
                  <span
                    className="mr-2 h-5 w-5 rounded-full bg-cover"
                    style={{
                      backgroundImage: `url(/news-icons/${s.id.split('-')[0]}.png)`,
                    }}
                  />
                  <span>{s.name}</span>
                  {s.title && (
                    <span className="ml-2 text-xs text-gray-500 dark:text-neutral-500">
                      {s.title}
                    </span>
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
