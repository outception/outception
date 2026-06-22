'use client'

import type { PromotionAnalytics } from '@/utils/promotions'
import { Text } from '@polar-sh/orbit'
import { Box } from '@polar-sh/orbit/Box'
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const formatDay = (timestamp: string) =>
  new Date(timestamp).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })

/** Daily spend (bars, left axis) with impressions and clicks (lines, right
 * axis). Impressions/clicks are only non-zero when analytics are sourced from
 * Tinybird; the chart still renders spend otherwise. */
export const PromotionAnalyticsChart = ({
  analytics,
}: {
  analytics: PromotionAnalytics
}) => {
  if (!analytics.periods.length) {
    return null
  }

  const data = analytics.periods.map((period) => ({
    date: formatDay(period.timestamp),
    spend: (period.spend_cents ?? 0) / 100,
    impressions: period.impressions ?? 0,
    clicks: period.clicks ?? 0,
  }))

  return (
    <Box
      flexDirection="column"
      rowGap="m"
      padding="l"
      borderRadius="l"
      backgroundColor="background-card"
    >
      <Text variant="body" as="h2">
        Last 30 days
      </Text>
      <Box height={280} width="100%">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={data}
            margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#88888822" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: '#888' }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              yAxisId="spend"
              tick={{ fontSize: 11, fill: '#888' }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value: number) => `$${value}`}
            />
            <YAxis
              yAxisId="engagement"
              orientation="right"
              tick={{ fontSize: 11, fill: '#888' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar
              yAxisId="spend"
              dataKey="spend"
              name="Spend"
              fill="#6366f1"
              radius={[4, 4, 0, 0]}
              maxBarSize={28}
            />
            <Line
              yAxisId="engagement"
              type="monotone"
              dataKey="impressions"
              name="Impressions"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
            />
            <Line
              yAxisId="engagement"
              type="monotone"
              dataKey="clicks"
              name="Clicks"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </Box>
    </Box>
  )
}

export default PromotionAnalyticsChart
