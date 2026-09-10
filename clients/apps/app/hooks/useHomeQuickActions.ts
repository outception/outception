import { useCallback, useEffect, useRef, useSyncExternalStore } from 'react'
import * as QuickActions from 'expo-quick-actions'
import { useQuickActionCallback } from 'expo-quick-actions/hooks'
import {
  getTranslations,
  getTranslationsVersion,
  subscribeTranslations,
} from '@outception-com/i18n'
import { useLocale } from '@/providers/LocaleProvider'

export type QuickActionTarget = 'cards' | 'sources' | 'search'

/** Home-screen quick actions (long-press the app icon): jump straight to the
 * card set, the sources browser, or headline search - a native launcher capability
 * a web page cannot provide. Registers the items and routes taps (including the
 * one that cold-launched the app) to the wall's local state. */
export const useHomeQuickActions = (
  onSelect: (t: QuickActionTarget) => void,
) => {
  // Re-registered when the language changes AND when the locale's strings
  // finally land. Read once at mount, the launcher kept whatever language was
  // active then - including English, when the chunk had not loaded yet - and
  // those titles are written through to the OS, so they survived until the
  // next cold start.
  const locale = useLocale()
  const version = useSyncExternalStore(
    subscribeTranslations,
    getTranslationsVersion,
    getTranslationsVersion,
  )
  useEffect(() => {
    const tr = getTranslations(locale)
    void QuickActions.setItems([
      {
        id: 'cards',
        title: tr.news.quickActions.cards,
        icon: 'symbol:rectangle.stack',
        params: { target: 'cards' },
      },
      {
        id: 'sources',
        title: tr.news.quickActions.sources,
        icon: 'symbol:square.grid.2x2',
        params: { target: 'sources' },
      },
      {
        id: 'search',
        title: tr.news.quickActions.search,
        icon: 'search',
        params: { target: 'search' },
      },
    ])
  }, [locale, version])

  // Keep the latest onSelect in a ref so the callback identity stays stable.
  // useQuickActionCallback re-subscribes (and re-fires the cold-launch action)
  // whenever its callback changes; an unstable closure would re-apply the
  // launch action on every render, trapping the user on that view.
  const onSelectRef = useRef(onSelect)
  useEffect(() => {
    onSelectRef.current = onSelect
  })

  const handle = useCallback((action: QuickActions.Action) => {
    const target = action.params?.target
    if (target === 'cards' || target === 'sources' || target === 'search') {
      onSelectRef.current(target)
    }
  }, [])

  useQuickActionCallback(handle)
}
