'use client'

import {
  useMyPromotions,
  usePromotionAnalytics,
} from '@/hooks/queries/promotions'
import { topicLabel } from '@/utils/promotions'
import { Pill, Spinner, Text } from '@polar-sh/orbit'
import { Box } from '@polar-sh/orbit/Box'
import { PromotionAnalyticsChart } from './PromotionAnalyticsChart'

const formatCents = (cents: number) => `$${(cents / 100).toFixed(2)}`

const KpiCard = ({ label, value }: { label: string; value: string }) => (
  <Box
    flexDirection="column"
    rowGap="xs"
    padding="l"
    borderRadius="l"
    backgroundColor="background-card"
  >
    <Text variant="caption" color="muted">
      {label}
    </Text>
    <Text variant="heading-xs" as="span">
      {value}
    </Text>
  </Box>
)

const statusColor = (
  status: string,
): 'green' | 'blue' | 'gray' | 'yellow' => {
  if (status === 'active') return 'green'
  if (status === 'queued') return 'blue'
  if (status === 'pending_payment') return 'yellow'
  return 'gray'
}

/** Promoter-facing analytics + promotion list, scoped to the signed-in user. */
export const PromotionsDashboard = () => {
  const { data: analytics, isLoading: analyticsLoading } =
    usePromotionAnalytics(30)
  const { data: promotions, isLoading: promotionsLoading } = useMyPromotions()

  return (
    <Box flexDirection="column" rowGap="xl" padding="xl">
      <Box flexDirection="column" rowGap="xs">
        <Text variant="heading-s" as="h1">
          Promotions
        </Text>
        <Text color="muted">
          Your featured-slot purchases and how they&apos;re performing.
        </Text>
      </Box>

      {analyticsLoading ? (
        <Box justifyContent="center" padding="l">
          <Spinner />
        </Box>
      ) : (
        <Box
          display="grid"
          gridTemplateColumns={{
            base: '1fr',
            sm: 'repeat(2, 1fr)',
            lg: 'repeat(4, 1fr)',
          }}
          gap="m"
        >
          <KpiCard
            label="Total spend (lifetime)"
            value={formatCents(analytics?.total_spend_cents ?? 0)}
          />
          <KpiCard
            label="Impressions"
            value={(analytics?.total_impressions ?? 0).toLocaleString()}
          />
          <KpiCard
            label="Clicks"
            value={(analytics?.total_clicks ?? 0).toLocaleString()}
          />
          <KpiCard
            label="CTR"
            value={`${((analytics?.ctr ?? 0) * 100).toFixed(1)}%`}
          />
        </Box>
      )}

      {analytics && <PromotionAnalyticsChart analytics={analytics} />}

      <Box flexDirection="column" rowGap="m">
        <Text variant="body" as="h2">
          Your promotions
        </Text>
        {promotionsLoading ? (
          <Box justifyContent="center" padding="l">
            <Spinner />
          </Box>
        ) : !promotions?.length ? (
          <Box
            flexDirection="column"
            alignItems="center"
            paddingVertical="3xl"
            rowGap="s"
          >
            <Text color="muted">No promotions yet.</Text>
            <Text variant="caption" color="muted">
              Promote a post from the news wall to get started.
            </Text>
          </Box>
        ) : (
          <Box flexDirection="column" rowGap="s">
            {promotions.map((p) => (
              <Box
                key={p.id}
                flexDirection="row"
                alignItems="center"
                justifyContent="between"
                columnGap="m"
                padding="l"
                borderRadius="l"
                backgroundColor="background-card"
              >
                <Box flexDirection="column" rowGap="xs" flexShrink={1}>
                  <Text variant="body">{p.title}</Text>
                  <Box flexDirection="row" alignItems="center" columnGap="s">
                    <Pill color="gray">{topicLabel(p.category)}</Pill>
                    <Pill color={statusColor(p.status)}>{p.status}</Pill>
                  </Box>
                </Box>
                <Text variant="caption" color="muted">
                  {p.duration_minutes} min
                </Text>
              </Box>
            ))}
          </Box>
        )}
      </Box>
    </Box>
  )
}

export default PromotionsDashboard
