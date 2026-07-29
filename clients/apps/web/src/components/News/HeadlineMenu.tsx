'use client'

import { useT } from '@/providers/locale'
import { safeExternalHref, type NewsItem } from '@/utils/news'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { useCallback, useEffect, useState } from 'react'
import { hideSource } from './newsPrefsStore'

type MenuState = { item: NewsItem; x: number; y: number } | null

/** Right-click menu for a headline: open / share / copy — and hide the whole
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
      <Box
        as="ul"
        position="fixed"
        zIndex={91}
        flexDirection="column"
        rowGap="none"
        padding="xs"
        borderRadius="m"
        borderWidth={1}
        borderStyle="solid"
        borderColor="border-primary"
        backgroundColor="background-card"
        boxShadow="l"
        style={{ top: y, left: x, width: 224, listStyle: 'none', margin: 0 }}
      >
        <MenuRow
          label={t('news.menu.open')}
          onSelect={run(() => window.open(url, '_blank', 'noopener'))}
        />
        <MenuRow label={t('news.menu.share')} onSelect={run(share)} />
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
      </Box>
    </>
  )
}
