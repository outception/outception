import { getQueryClient } from '@/utils/api/query'
import { api } from '@/utils/client'
import { schemas } from '@outception-com/client'
import { useMutation } from '@tanstack/react-query'

export const useUpdateUser = () =>
  useMutation({
    mutationFn: (body: schemas['UserUpdate']) => {
      return api.PATCH('/v1/users/me', { body })
    },
    onSuccess: (result) => {
      if (result.error) {
        return
      }
      getQueryClient().invalidateQueries({ queryKey: ['user'] })
    },
  })

export const useDeleteUser = () =>
  useMutation({
    mutationFn: () => {
      return api.DELETE('/v1/users/me')
    },
  })
