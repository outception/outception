import { queryClient, QueryClientProvider } from '@/utils/query'
import { useReactQueryDevTools } from '@dev-plugins/react-query'

export function OutceptionQueryClientProvider({
  children,
}: {
  children: React.ReactElement
}) {
  useReactQueryDevTools(queryClient)

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}
