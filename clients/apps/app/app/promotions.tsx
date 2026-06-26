import { PromotionAnalytics } from '@/components/Promotions/PromotionAnalytics'
import { Box } from '@/components/Shared/Box'
import { Button } from '@/components/Shared/Button'
import { Pill } from '@/components/Shared/Pill'
import { Text } from '@/components/Shared/Text'
import { useTheme } from '@/design-system/useTheme'
import { topicLabel, useMyPromotions } from '@/hooks/outception/promotions'
import { useSession } from '@/providers/SessionProvider'
import { Redirect, useRouter } from 'expo-router'
import { ActivityIndicator, ScrollView } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

type PillColor = 'green' | 'blue' | 'yellow' | 'gray'

const statusColor = (status: string): PillColor => {
  if (status === 'active') return 'green'
  if (status === 'queued') return 'blue'
  if (status === 'pending_payment') return 'yellow'
  return 'gray'
}

export default function Promotions() {
  const theme = useTheme()
  const router = useRouter()
  const { session } = useSession()
  const { data: promotions, isLoading } = useMyPromotions(!!session)

  if (!session) {
    return <Redirect href="/login" />
  }

  return (
    <SafeAreaView style={{ flex: 1 }} edges={['bottom']}>
      <ScrollView
        contentContainerStyle={{
          padding: theme.spacing['spacing-16'],
          gap: theme.spacing['spacing-16'],
        }}
      >
        <Box
          flexDirection="row"
          alignItems="center"
          justifyContent="space-between"
        >
          <Text variant="titleLarge">Promotions</Text>
          <Button size="small" onPress={() => router.push('/promote')}>
            New
          </Button>
        </Box>

        <PromotionAnalytics />

        <Text variant="title">Your promotions</Text>
        {isLoading ? (
          <ActivityIndicator />
        ) : !promotions?.length ? (
          <Text variant="caption" color="subtext">
            No promotions yet. Tap New to promote a post.
          </Text>
        ) : (
          <Box gap="spacing-8">
            {promotions.map((p) => (
              <Box
                key={p.id}
                gap="spacing-8"
                padding="spacing-16"
                borderRadius="border-radius-16"
                backgroundColor="card"
              >
                <Text variant="bodyMedium">{p.title}</Text>
                <Box flexDirection="row" alignItems="center" gap="spacing-8">
                  <Pill color="gray">{topicLabel(p.category)}</Pill>
                  <Pill color={statusColor(p.status)}>{p.status}</Pill>
                  <Text variant="caption" color="subtext">
                    {p.duration_minutes} min
                  </Text>
                </Box>
                <Text variant="caption" color="subtext">
                  {p.impressions.toLocaleString()} views ·{' '}
                  {p.clicks.toLocaleString()} clicks
                </Text>
              </Box>
            ))}
          </Box>
        )}
      </ScrollView>
    </SafeAreaView>
  )
}
