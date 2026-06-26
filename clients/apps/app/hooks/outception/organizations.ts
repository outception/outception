import { useOutceptionClient } from '@/providers/OutceptionClientProvider'
import { unwrap } from '@outception-com/client'
import * as Sentry from '@sentry/react-native'
import { useQuery } from '@tanstack/react-query'

export const useOrganizations = (
  {
    enabled = true,
  }: {
    enabled?: boolean
  } = { enabled: true },
) => {
  const { outception } = useOutceptionClient()

  return useQuery({
    queryKey: ['organizations'],
    queryFn: async () => {
      try {
        return await unwrap(
          outception.GET('/v1/organizations/', {
            params: {
              query: {
                limit: 100,
              },
            },
          }),
        )
      } catch (error) {
        Sentry.captureException(error, {
          tags: { context: 'useOrganizations' },
        })
        throw error
      }
    },
    enabled,
  })
}
