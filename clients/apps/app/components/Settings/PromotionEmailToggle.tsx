import { Box } from '@/components/Shared/Box'
import { Switch } from '@/components/Shared/Switch'
import { Text } from '@/components/Shared/Text'
import {
  usePromotionPreferences,
  useUpdatePromotionPreferences,
} from '@/hooks/polar/promotions'
import { useState } from 'react'

export const PromotionEmailToggle = () => {
  const { data } = usePromotionPreferences()
  const update = useUpdatePromotionPreferences()
  const [override, setOverride] = useState<boolean | null>(null)

  const value = override ?? data?.promotion_emails_enabled ?? true

  const onToggle = (next: boolean) => {
    setOverride(next)
    update.mutate(next, { onError: () => setOverride(!next) })
  }

  return (
    <Box
      flexDirection="row"
      alignItems="center"
      justifyContent="space-between"
      paddingVertical="spacing-12"
      gap="spacing-12"
    >
      <Box flex={1} flexDirection="column" gap="spacing-4">
        <Text variant="body">Promotion emails</Text>
        <Text variant="caption" color="subtext">
          Get emailed when your promotions go live, queue, or end.
        </Text>
      </Box>
      <Switch value={value} onValueChange={onToggle} />
    </Box>
  )
}
