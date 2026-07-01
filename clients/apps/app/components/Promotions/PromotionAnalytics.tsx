import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { useTheme } from '@/design-system/useTheme'
import { usePromotionAnalytics } from '@/hooks/outception/promotions'
import { ActivityIndicator, useWindowDimensions } from 'react-native'
import Svg, { Line, Polyline } from 'react-native-svg'

const formatCents = (cents: number) => `$${(cents / 100).toFixed(2)}`

const Kpi = ({ label, value }: { label: string; value: string }) => (
  <Box
    flex={1}
    gap="spacing-4"
    padding="spacing-12"
    borderRadius="border-radius-12"
    backgroundColor="card"
  >
    <Text variant="caption" color="subtext">
      {label}
    </Text>
    <Text variant="title">{value}</Text>
  </Box>
)

const Dot = ({ color, label }: { color: string; label: string }) => (
  <Box flexDirection="row" alignItems="center" gap="spacing-4">
    <Box
      width={8}
      height={8}
      borderRadius="border-radius-999"
      style={{ backgroundColor: color }}
    />
    <Text variant="caption" color="subtext">
      {label}
    </Text>
  </Box>
)

/** Promotion KPIs plus a daily impressions/clicks line chart. The series is
 * populated only when analytics are Tinybird-sourced; otherwise the chart shows
 * a note and the KPI totals still render. */
export const PromotionAnalytics = () => {
  const theme = useTheme()
  const { data: analytics, isLoading } = usePromotionAnalytics(30)
  const chartWidth = useWindowDimensions().width - 64
  const chartHeight = 160

  if (isLoading) {
    return (
      <Box paddingVertical="spacing-24" alignItems="center">
        <ActivityIndicator />
      </Box>
    )
  }

  const periods = analytics?.periods ?? []
  const impressions = analytics?.total_impressions ?? 0
  const clicks = analytics?.total_clicks ?? 0
  const ctr = analytics?.ctr ?? 0

  const maxY = Math.max(
    1,
    ...periods.map((p) => Math.max(p.impressions ?? 0, p.clicks ?? 0)),
  )
  const toPoints = (key: 'impressions' | 'clicks') =>
    periods
      .map((p, i) => {
        const x =
          periods.length > 1 ? (i / (periods.length - 1)) * chartWidth : 0
        const y = chartHeight - ((p[key] ?? 0) / maxY) * chartHeight
        return `${x},${y}`
      })
      .join(' ')

  return (
    <Box gap="spacing-16">
      <Box flexDirection="row" gap="spacing-8">
        <Kpi
          label="Spend"
          value={formatCents(analytics?.total_spend_cents ?? 0)}
        />
        <Kpi label="Impressions" value={impressions.toLocaleString()} />
      </Box>
      <Box flexDirection="row" gap="spacing-8">
        <Kpi label="Clicks" value={clicks.toLocaleString()} />
        <Kpi label="CTR" value={`${(ctr * 100).toFixed(1)}%`} />
      </Box>

      <Box
        gap="spacing-12"
        padding="spacing-16"
        borderRadius="border-radius-16"
        backgroundColor="card"
      >
        <Box
          flexDirection="row"
          justifyContent="space-between"
          alignItems="center"
        >
          <Text variant="title">Last 30 days</Text>
          <Box flexDirection="row" gap="spacing-12">
            <Dot color={theme.colors.primary} label="Impressions" />
            <Dot color={theme.colors.statusGreen} label="Clicks" />
          </Box>
        </Box>
        {periods.length > 1 ? (
          <Svg width={chartWidth} height={chartHeight}>
            <Line
              x1={0}
              y1={chartHeight}
              x2={chartWidth}
              y2={chartHeight}
              stroke={theme.colors.border}
              strokeWidth={1}
            />
            <Polyline
              points={toPoints('impressions')}
              fill="none"
              stroke={theme.colors.primary}
              strokeWidth={2}
            />
            <Polyline
              points={toPoints('clicks')}
              fill="none"
              stroke={theme.colors.statusGreen}
              strokeWidth={2}
            />
          </Svg>
        ) : (
          <Text variant="caption" color="subtext">
            Not enough daily data yet. The series fills in as your promotions
            run.
          </Text>
        )}
      </Box>
    </Box>
  )
}

export default PromotionAnalytics
