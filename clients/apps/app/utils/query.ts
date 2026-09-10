import { ClientResponseError, isValidationError } from '@outception-com/client'
import { QueryClient } from '@tanstack/react-query'

export { QueryClient, QueryClientProvider } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // With SSR, we usually want to set some default staleTime
      // above 0 to avoid refetching immediately on the client
      staleTime: 60 * 1000,
      // gcTime stays at the 5-minute default: the queries the persister
      // restores opt into PERSISTED_GC_TIME individually (utils/queryPersist.ts)
      // so the rest of the cache doesn't accumulate in memory all session.
      throwOnError: true,
      retry: (failureCount, error) => {
        if (
          error instanceof ClientResponseError &&
          error.response.status >= 400 &&
          error.response.status < 500
        ) {
          return false
        }

        if (isValidationError(error)) {
          return false
        }

        if (failureCount >= 3) {
          return false
        }

        return true
      },
    },
  },
})
