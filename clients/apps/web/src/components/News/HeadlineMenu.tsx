'use client'

import { useLocale, useT } from '@/providers/locale'
import { safeExternalHref, type NewsItem } from '@/utils/news'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { addMutedWord } from './mutedWords'
import { hideSource } from './newsPrefsStore'

type MenuState = { item: NewsItem; x: number; y: number } | null

/** Right-click menu for a headline: open / share / copy - and hide the whole
 * source. Rendered as a fixed-position card; closes on click, Escape, scroll
 * or resize like a native menu. */
export const useHeadlineMenu = (sourceId: string, sourceName: string) => {
  const [menu, setMenu] = useState<MenuState>(null)
  const t = useT()

  const openMenu = useCallback((e: React.MouseEvent, item: NewsItem) => {
    e.preventDefault()
    // Clamp so the menu never renders off the right/bottom edge.
    const x = Math.min(e.clientX, window.innerWidth - 240)
    const y = Math.min(e.clientY, window.innerHeight - 240)
    setMenu({ item, x, y })
  }, [])

  const close = useCallback(() => setMenu(null), [])

  useEffect(() => {
    if (!menu) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    window.addEventListener('keydown', onKey)
    window.addEventListener('scroll', close, true)
    window.addEventListener('resize', close)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('scroll', close, true)
      window.removeEventListener('resize', close)
    }
  }, [menu, close])

  const element = menu ? (
    <HeadlineMenuCard
      item={menu.item}
      x={menu.x}
      y={menu.y}
      sourceId={sourceId}
      sourceName={sourceName}
      onClose={close}
      t={t}
    />
  ) : null

  return { menuElement: element, openMenu }
}

const MenuRow = ({
  label,
  onSelect,
}: {
  label: string
  onSelect: () => void
}) => (
  <Box
    as="li"
    display="block"
    paddingHorizontal="m"
    paddingVertical="s"
    borderRadius="s"
    cursor={{ hover: 'pointer' }}
    backgroundColor={{ hover: 'background-secondary' }}
    onClick={onSelect}
  >
    <Text variant="body" as="span">
      {label}
    </Text>
  </Box>
)

const HeadlineMenuCard = ({
  item,
  x,
  y,
  sourceId,
  sourceName,
  onClose,
  t,
}: {
  item: NewsItem
  x: number
  y: number
  sourceId: string
  sourceName: string
  onClose: () => void
  t: ReturnType<typeof useT>
}) => {
  const url = safeExternalHref(item.url) ?? ''
  const locale = useLocale()
  // Reads the headline aloud via the browser's speech synthesis. The row
  // toggles in place (it must not close the menu - unmount stops speech).
  const [speaking, setSpeaking] = useState(false)
  const canListen = typeof window !== 'undefined' && 'speechSynthesis' in window
  const toggleListen = () => {
    if (!canListen) return
    if (speaking) {
      window.speechSynthesis.cancel()
      setSpeaking(false)
      return
    }
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(item.title)
    utterance.lang = locale
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)
    window.speechSynthesis.speak(utterance)
    setSpeaking(true)
  }
  useEffect(() => {
    return () => {
      if ('speechSynthesis' in window) window.speechSynthesis.cancel()
    }
  }, [])
  // "Mute a word…" swaps the rows to a word picker inside the same card (it
  // must not close the menu - the choice happens on the next click).
  const [pickingWord, setPickingWord] = useState(false)
  const wordChoices = useMemo(() => {
    const seen = new Set<string>()
    const words: string[] = []
    for (const raw of item.title.split(/\s+/)) {
      // Strip leading/trailing punctuation but keep inner marks ("don't",
      // "e-bike") so the muted word still substring-matches headlines.
      const word = raw.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '')
      if (word.length <= 3) continue
      const key = word.toLowerCase()
      if (seen.has(key)) continue
      seen.add(key)
      words.push(word)
      if (words.length === 8) break
    }
    return words
  }, [item.title])
  const run = (fn: () => void) => () => {
    fn()
    onClose()
  }
  const copy = (text: string) => {
    void navigator.clipboard?.writeText(text).catch(() => {})
  }
  const share = () => {
    if (navigator.share) {
      void navigator.share({ title: item.title, url }).catch(() => {})
    } else {
      copy(url)
    }
  }
  return (
    <>
      {/* Invisible backdrop: first click anywhere just closes the menu. */}
      <Box
        position="fixed"
        inset={0}
        zIndex={90}
        onClick={onClose}
        onContextMenu={(e: React.MouseEvent) => {
          e.preventDefault()
          onClose()
        }}
      />
      {/* Plain wrapper for the pointer-derived position: dynamic px values
          aren't Box tokens, and Box takes no style (AGENTS.md escape hatch).
          List reset comes from the global preflight. */}
      <div
        style={{ position: 'fixed', top: y, left: x, width: 224, zIndex: 91 }}
      >
        <Box
          as="ul"
          flexDirection="column"
          rowGap="none"
          padding="xs"
          borderRadius="m"
          borderWidth={1}
          borderStyle="solid"
          borderColor="border-primary"
          backgroundColor="background-card"
          boxShadow="l"
        >
          {pickingWord ? (
            <>
              <MenuRow
                label={t('news.menu.cancel')}
                onSelect={() => setPickingWord(false)}
              />
              <Box
                as="li"
                display="block"
                marginVertical="xs"
                borderTopWidth={1}
                borderStyle="solid"
                borderColor="border-secondary"
              />
              {wordChoices.map((word) => (
                <MenuRow
                  key={word.toLowerCase()}
                  label={word}
                  onSelect={run(() => addMutedWord(word))}
                />
              ))}
            </>
          ) : (
            <>
              <MenuRow
                label={t('news.menu.open')}
                onSelect={run(() => window.open(url, '_blank', 'noopener'))}
              />
              <MenuRow label={t('news.menu.share')} onSelect={run(share)} />
              {canListen && (
                <MenuRow
                  label={
                    speaking
                      ? t('news.menu.stopListening')
                      : t('news.menu.listen')
                  }
                  onSelect={toggleListen}
                />
              )}
              <MenuRow
                label={t('news.menu.copyLink')}
                onSelect={run(() => copy(url))}
              />
              <MenuRow
                label={t('news.menu.copyHeadline')}
                onSelect={run(() => copy(item.title))}
              />
              <Box
                as="li"
                display="block"
                marginVertical="xs"
                borderTopWidth={1}
                borderStyle="solid"
                borderColor="border-secondary"
              />
              <MenuRow
                label={t('news.menu.muteSource', { source: sourceName })}
                onSelect={run(() => hideSource(sourceId))}
              />
              {wordChoices.length > 0 && (
                <MenuRow
                  label={t('news.menu.muteWord')}
                  onSelect={() => setPickingWord(true)}
                />
              )}
            </>
          )}
        </Box>
      </div>
    </>
  )
}
