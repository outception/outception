'use client'

import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { Document } from 'flexsearch'
import { Search } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useRef, useState } from 'react'

interface SearchEntry {
  title: string
  href: string
  description?: string
  content?: string
}

type DocsIndex = Document

const createIndex = (entries: SearchEntry[]): DocsIndex => {
  const index: DocsIndex = new Document({
    tokenize: 'forward',
    document: {
      id: 'href',
      index: ['title', 'description', 'content'],
      store: ['title', 'href', 'description'],
    },
  })
  entries.forEach((entry) =>
    index.add({
      ...entry,
      description: entry.description ?? '',
      content: entry.content ?? '',
    }),
  )
  return index
}

type EnrichedGroup = { result: { id: string; doc?: SearchEntry }[] }

const queryIndex = (index: DocsIndex, query: string): SearchEntry[] => {
  const groups = index.search(query, {
    enrich: true,
    limit: 8,
    suggest: true,
  }) as unknown as EnrichedGroup[]
  const seen = new Set<string>()
  const results: SearchEntry[] = []
  for (const group of groups) {
    for (const item of group.result) {
      const entry = item.doc
      if (!entry || seen.has(entry.href)) continue
      seen.add(entry.href)
      results.push(entry)
    }
  }
  return results
}

export function DocsSearch({
  set,
  basePath,
}: {
  set: string
  basePath: string
}) {
  void set
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchEntry[]>([])
  const indexRef = useRef<DocsIndex | null>(null)

  const ensureIndex = useCallback(async () => {
    if (indexRef.current) return
    const response = await fetch(`${basePath}/search-index.json`)
    const entries = (await response.json()) as SearchEntry[]
    indexRef.current = createIndex(entries)
  }, [basePath])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setOpen((value) => !value)
      } else if (event.key === 'Escape') {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    if (open) void ensureIndex()
  }, [open, ensureIndex])

  const onChange = (value: string) => {
    setQuery(value)
    const index = indexRef.current
    setResults(index && value.trim() ? queryIndex(index, value) : [])
  }

  const go = (href: string) => {
    setOpen(false)
    setQuery('')
    setResults([])
    router.push(href)
  }

  return (
    <>
      <Box
        as="label"
        role="button"
        onClick={() => setOpen(true)}
        alignItems="center"
        columnGap="s"
        minWidth={200}
        paddingVertical="xs"
        paddingHorizontal="m"
        borderRadius="m"
        borderWidth={1}
        borderStyle="solid"
        borderColor="border-primary"
        backgroundColor={{
          base: 'background-secondary',
          hover: 'background-card',
        }}
        color="text-secondary"
        cursor="pointer"
      >
        <Search size={16} />
        <Box flexGrow={1}>
          <span className="text-sm">Search…</span>
        </Box>
        <kbd className="text-xs opacity-60">⌘K</kbd>
      </Box>

      {open ? (
        <div
          className="fixed inset-0 z-50 flex justify-center bg-black/40 pt-24"
          onClick={() => setOpen(false)}
        >
          <Box
            flexDirection="column"
            width="100%"
            maxWidth={560}
            maxHeight="60vh"
            marginHorizontal="l"
            borderRadius="l"
            borderWidth={1}
            borderStyle="solid"
            borderColor="border-primary"
            backgroundColor="background-primary"
            boxShadow="xl"
            overflow="hidden"
            onClick={(event) => event.stopPropagation()}
          >
            <Box
              alignItems="center"
              columnGap="s"
              paddingHorizontal="l"
              paddingVertical="m"
              borderBottomWidth={1}
              borderStyle="solid"
              borderColor="border-primary"
            >
              <Search size={18} />
              <input
                autoFocus
                value={query}
                onChange={(event) => onChange(event.target.value)}
                placeholder="Search documentation…"
                className="flex-1 bg-transparent text-base outline-none"
              />
            </Box>
            <Box flexDirection="column" overflowY="auto">
              {results.map((entry) => (
                <Box
                  as="label"
                  key={entry.href}
                  role="button"
                  onClick={() => go(entry.href)}
                  flexDirection="column"
                  rowGap="xs"
                  paddingHorizontal="l"
                  paddingVertical="m"
                  cursor="pointer"
                  backgroundColor={{ hover: 'background-secondary' }}
                >
                  <Text variant="label" color="default">
                    {entry.title}
                  </Text>
                  {entry.description ? (
                    <Text variant="caption" color="muted">
                      {entry.description}
                    </Text>
                  ) : null}
                </Box>
              ))}
              {query.trim() && results.length === 0 ? (
                <Box paddingHorizontal="l" paddingVertical="l">
                  <Text variant="caption" color="muted">
                    No results for “{query}”.
                  </Text>
                </Box>
              ) : null}
            </Box>
          </Box>
        </div>
      ) : null}
    </>
  )
}
