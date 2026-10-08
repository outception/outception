import { getQueryClient } from '@/utils/api/query'
import { CONFIG } from '@/utils/config'
import { api } from '@/utils/client'
import { schemas, unwrap } from '@outception-com/client'
import { useMutation, useQuery } from '@tanstack/react-query'
import { defaultRetry } from './retry'

export type Launch = schemas['LaunchRead']
export type MyLaunch = schemas['LaunchMine']
export type LaunchCreate = schemas['LaunchCreate']
export type LaunchEdit = schemas['LaunchEdit']
export type LaunchApprove = schemas['LaunchApprove']
export type LaunchUpdate = schemas['LaunchUpdate']
export type Race = schemas['Race']

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

/** One product; listed ones are public, the rest only for their
 * submitter and the admin list. */
export const useLaunch = (id: string | null) =>
  useQuery({
    queryKey: ['launches', 'one', id],
    queryFn: () =>
      unwrap(api.GET('/v1/launches/{id}', { params: { path: { id: id! } } })),
    enabled: !!id,
    retry: false,
  })

/** The reader's products as a bar chart race, every day of the window. */
export const useMyRace = (enabled = true) =>
  useQuery({
    queryKey: ['launches', 'race', 'mine'],
    queryFn: () => unwrap(api.GET('/v1/launches/mine/race')),
    enabled,
    staleTime: 60_000,
    retry: false,
  })

/** Site visits by page or by visitor country, for the admin list. */
export const useVisitsRace = (dimension: 'path' | 'country', enabled = true) =>
  useQuery({
    queryKey: ['launches', 'race', 'visits', dimension],
    queryFn: () =>
      unwrap(
        api.GET('/v1/launches/visits/race', {
          params: { query: { dimension } },
        }),
      ),
    enabled,
    staleTime: 60_000,
    retry: false,
  })

export const useWithdrawLaunch = () =>
  useMutation({
    mutationFn: (id: string) =>
      api.POST('/v1/launches/{id}/withdraw', { params: { path: { id } } }),
    onSuccess: (result) => {
      if (!result.error) void invalidate()
    },
  })

export const useUpdateLaunch = () =>
  useMutation({
    mutationFn: ({ id, body }: { id: string; body: LaunchUpdate }) =>
      api.PATCH('/v1/launches/{id}', { params: { path: { id } }, body }),
    onSuccess: (result) => {
      if (!result.error) void invalidate()
    },
  })

export const useDeleteLaunch = () =>
  useMutation({
    mutationFn: (id: string) =>
      api.DELETE('/v1/launches/{id}', { params: { path: { id } } }),
    onSuccess: (result) => {
      if (!result.error) void invalidate()
    },
  })

/** The counting redirect a listed product opens through. */
export const launchGoHref = (id: string): string =>
  `${CONFIG.BASE_URL}/v1/launches/${id}/go`

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
