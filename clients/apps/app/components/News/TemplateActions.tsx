import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useT } from '@/providers/LocaleProvider'
import { KICKER_STYLE } from './newsStyles'
import * as Haptics from 'expo-haptics'
import { useEffect, useRef, useState } from 'react'
import type { StyleProp, ViewStyle } from 'react-native'

/** Select/deselect-all row for the Starters view — the same pair (and flash
 * feedback) the roster shows above the source list, acting on every deck. */
export const TemplateActions = ({
  hairline,
  count,
  onSelectAll,
  onDeselectAll,
}: {
  hairline: StyleProp<ViewStyle>
  count: number
  onSelectAll: () => void
  onDeselectAll: () => void
}) => {
  const t = useT()
  const [flash, setFlash] = useState<'select' | 'deselect' | null>(null)
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(
    () => () => {
      if (flashTimer.current) clearTimeout(flashTimer.current)
    },
    [],
  )
  const flashAction = (which: 'select' | 'deselect') => {
    void Haptics.selectionAsync()
    setFlash(which)
    if (flashTimer.current) clearTimeout(flashTimer.current)
    flashTimer.current = setTimeout(() => setFlash(null), 400)
  }
  return (
    <Box
      flexDirection="row"
      alignItems="center"
      gap="spacing-16"
      paddingHorizontal="spacing-16"
      paddingVertical="spacing-6"
      style={hairline}
    >
      <Touchable
        onPress={() => {
          flashAction('select')
          onSelectAll()
        }}
        disabled={count === 0}
      >
        <Box
          paddingVertical="spacing-4"
          paddingHorizontal="spacing-10"
          borderRadius="border-radius-999"
          backgroundColor={flash === 'select' ? 'primaryStrong' : undefined}
        >
          <Text
            variant="caption"
            color={flash === 'select' ? 'onAccent' : 'subtext'}
            style={{ opacity: count === 0 ? 0.4 : 1 }}
          >
            {t('news.search.selectAll')}
          </Text>
        </Box>
      </Touchable>
      <Touchable
        onPress={() => {
          flashAction('deselect')
          onDeselectAll()
        }}
        disabled={count === 0}
      >
        <Box
          paddingVertical="spacing-4"
          paddingHorizontal="spacing-10"
          borderRadius="border-radius-999"
          backgroundColor={flash === 'deselect' ? 'primaryStrong' : undefined}
        >
          <Text
            variant="caption"
            color={flash === 'deselect' ? 'onAccent' : 'subtext'}
            style={{ opacity: count === 0 ? 0.4 : 1 }}
          >
            {t('news.search.deselectAll')}
          </Text>
        </Box>
      </Touchable>
      <Box flex={1} alignItems="flex-end">
        <Text variant="caption" color="subtext" style={KICKER_STYLE}>
          {count}
        </Text>
      </Box>
    </Box>
  )
}
