import { getQueryClient } from '@/utils/api/query'
import { api } from '@/utils/client'
import { schemas, unwrap } from '@outception-com/client'
import { useMutation, useQuery } from '@tanstack/react-query'
import { defaultRetry } from './retry'

export type Launch = schemas['LaunchRead']
export type MyLaunch = schemas['LaunchMine']
export type LaunchCreate = schemas['LaunchCreate']
export type LaunchEdit = schemas['LaunchEdit']
export type LaunchApprove = schemas['LaunchApprove']

const invalidate = () =>
  getQueryClient().invalidateQueries({ queryKey: ['launches'] })

export const useLaunchArchive = () =>
  useQuery({
    queryKey: ['launches', 'archive'],
    queryFn: () => unwrap(api.GET('/v1/launches')),
    staleTime: 60_000,
    retry: defaultRetry,
  })

export const useMyLaunches = (enabled = true) =>
  useQuery({
    queryKey: ['launches', 'mine'],
    queryFn: () => unwrap(api.GET('/v1/launches/mine')),
    enabled,
    retry: defaultRetry,
  })

export const useReviewQueue = (enabled = true) =>
  useQuery({
    queryKey: ['launches', 'review'],
    queryFn: () => unwrap(api.GET('/v1/launches/review')),
    enabled,
    retry: defaultRetry,
  })

export const useSubmitLaunch = () =>
  useMutation({
    mutationFn: (body: LaunchCreate) => api.POST('/v1/launches', { body }),
    onSuccess: (result) => {
      if (!result.error) void invalidate()
    },
  })

export const useWithdrawLaunch = () =>
  useMutation({
    mutationFn: (id: string) =>
      api.DELETE('/v1/launches/{id}', { params: { path: { id } } }),
    onSuccess: (result) => {
      if (!result.error) void invalidate()
    },
  })

export const useApproveLaunch = () =>
  useMutation({
    mutationFn: ({ id, body }: { id: string; body: LaunchApprove }) =>
      api.POST('/v1/launches/{id}/approve', {
        params: { path: { id } },
        body,
      }),
    onSuccess: (result) => {
      if (!result.error) void invalidate()
    },
  })

export const useRejectLaunch = () =>
  useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) =>
      api.POST('/v1/launches/{id}/reject', {
        params: { path: { id } },
        body: { note },
      }),
    onSuccess: (result) => {
      if (!result.error) void invalidate()
    },
  })

export const useEditLaunch = () =>
  useMutation({
    mutationFn: ({ id, body }: { id: string; body: LaunchEdit }) =>
      api.POST('/v1/launches/{id}/edit', { params: { path: { id } }, body }),
    onSuccess: (result) => {
      if (!result.error) void invalidate()
    },
  })
