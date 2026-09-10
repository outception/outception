import * as Haptics from 'expo-haptics'
import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import type { NewsSourceMeta } from '@/hooks/outception/news'
import { toggleFocus } from '@/utils/focusedSources'
import { SourceBadge } from './SourceBadge'
import { KICKER_STYLE } from './newsStyles'
import MaterialIcons from '@expo/vector-icons/MaterialIcons'
import { memo } from 'react'

/** One roster row: source icon, name, optional kicker, and a follow star.
 * Memoized so only rows whose follow state actually flips re-render when the
 * list repaints on a toggle. */
export const RosterRow = memo(
  ({ source, followed }: { source: NewsSourceMeta; followed: boolean }) => {
    const theme = useTheme()
    return (
      <Touchable
        onPress={() => {
          void Haptics.selectionAsync()
          toggleFocus(source.id)
        }}
      >
        <Box
          flexDirection="row"
          alignItems="center"
          gap="spacing-12"
          paddingVertical="spacing-8"
          paddingHorizontal="spacing-12"
          borderRadius="border-radius-12"
        >
          <SourceBadge
            id={source.id}
            name={source.name}
            logo={source.logo}
            size={20}
          />
          <Text variant="body" numberOfLines={1} style={{ flexShrink: 1 }}>
            {source.name}
          </Text>
          {source.title ? (
            <Text
              color="subtext"
              numberOfLines={1}
              style={[KICKER_STYLE, { flexShrink: 1 }]}
            >
              {source.title}
            </Text>
          ) : null}
          <Box flex={1} alignItems="flex-end">
            {/* Web: lucide Star, filled when followed, 30% outline otherwise. */}
            <MaterialIcons
              name={followed ? 'star' : 'star-border'}
              size={16}
              color={theme.colors.text}
              style={{ opacity: followed ? 1 : 0.3 }}
            />
          </Box>
        </Box>
      </Touchable>
    )
  },
)
RosterRow.displayName = 'RosterRow'

// Web chips: quiet transparent text, accent fill only when active.
export const RosterChip = ({
  label,
  active,
  onPress,
}: {
  label: string
  active: boolean
  onPress: () => void
}) => (
  <Touchable onPress={onPress}>
    <Box
      paddingVertical="spacing-4"
      paddingHorizontal="spacing-10"
      borderRadius="border-radius-6"
      backgroundColor={active ? 'primaryStrong' : undefined}
    >
      <Text variant="caption" color={active ? 'onAccent' : 'subtext'}>
        {label}
      </Text>
    </Box>
  </Touchable>
)
