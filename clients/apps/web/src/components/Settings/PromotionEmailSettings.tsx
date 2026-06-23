'use client'

import { useAuth } from '@/hooks'
import { useUpdateUser } from '@/hooks/queries/user'
import { Switch, Text } from '@polar-sh/orbit'
import { Box } from '@polar-sh/orbit/Box'
import { useState } from 'react'

export const PromotionEmailSettings = () => {
  const { currentUser } = useAuth()
  const updateUser = useUpdateUser()
  const [enabled, setEnabled] = useState(
    currentUser?.promotion_emails_enabled ?? true,
  )

  const onToggle = (checked: boolean) => {
    setEnabled(checked)
    updateUser.mutate(
      { promotion_emails_enabled: checked },
      { onError: () => setEnabled(!checked) },
    )
  }

  return (
    <Box
      alignItems="center"
      justifyContent="between"
      columnGap="l"
      borderRadius="l"
      backgroundColor="background-card"
      borderWidth={1}
      borderStyle="solid"
      borderColor="border-primary"
      padding="l"
    >
      <Box flexDirection="column" rowGap="xs">
        <Text>Lifecycle emails</Text>
        <Text color="muted" variant="caption">
          Get emailed when your promotions go live, are queued, or end.
        </Text>
      </Box>
      <Switch checked={enabled} onCheckedChange={onToggle} />
    </Box>
  )
}

export default PromotionEmailSettings
