'use client'

import { runWhenIdle } from '@/utils/idle'
import dynamic from 'next/dynamic'
import { useEffect, useState } from 'react'
import { useNewsColumn } from './NewsColumnContext'

// The source palette (the command list, the starter gallery, the topic
// chips) is closed on arrival, so it is its own chunk: fetched once the main
// thread idles, mounted on the first open, and never part of the wall's
// first paint.
const loadDialog = () => import('./NewsSearchDialog')
const NewsSearchDialog = dynamic(
  () => loadDialog().then((m) => m.NewsSearchDialog),
  { ssr: false },
)

/** Cmd/Ctrl+K and the palette, mounted from its first open onward. */
export const NewsSearch = () => {
  const { searchOpen, setSearchOpen } = useNewsColumn()
  const [opened, setOpened] = useState(searchOpen)
  if (searchOpen && !opened) setOpened(true)

  useEffect(
    () =>
      runWhenIdle(() => {
        void loadDialog()
      }),
    [],
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

  return opened ? <NewsSearchDialog /> : null
}
