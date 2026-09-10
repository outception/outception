import { useCallback, useEffect, useRef } from 'react'
import * as QuickActions from 'expo-quick-actions'
import { useQuickActionCallback } from 'expo-quick-actions/hooks'
import { getTranslations } from '@outception-com/i18n'

export type QuickActionTarget = 'cards' | 'sources' | 'search'

/** Home-screen quick actions (long-press the app icon): jump straight to the
 * card set, the sources browser, or headline search - a native launcher capability
 * a web page cannot provide. Registers the items and routes taps (including the
 * one that cold-launched the app) to the wall's local state. */
export const useHomeQuickActions = (
  onSelect: (t: QuickActionTarget) => void,
) => {
  useEffect(() => {
    const tr = getTranslations()
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
  }, [])

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
