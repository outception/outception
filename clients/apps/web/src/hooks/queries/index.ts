import { getQueryClient } from '@/utils/api/query'
import { api } from '@/utils/client'
import { unwrap } from '@polar-sh/client'
import { useMutation, useQuery } from '@tanstack/react-query'
import { defaultRetry } from './retry'

export * from './org'
export * from './slack'
export * from './user'

export const useNotifications = () =>
  useQuery({
    queryKey: ['notifications'],
    queryFn: () => unwrap(api.GET('/v1/notifications')),
    retry: defaultRetry,
  })

export const useNotificationsMarkRead = () =>
  useMutation({
    mutationFn: (variables: { notification_id: string }) => {
      return api.POST('/v1/notifications/read', {
        body: {
          notification_id: variables.notification_id,
        },
      })
    },
    onSuccess: (result) => {
      if (result.error) {
        return
      }
      getQueryClient().invalidateQueries({ queryKey: ['notifications'] })
    },
  })
