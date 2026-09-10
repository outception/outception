import { getQueryClient } from '@/utils/api/query'
import { api } from '@/utils/client'
import { operations, schemas, unwrap } from '@outception-com/client'
import { useMutation, useQuery } from '@tanstack/react-query'
import { defaultRetry } from './retry'

export const useListOrganizations = (
  params: operations['organizations:list']['parameters']['query'],
  enabled: boolean = true,
) =>
  useQuery({
    queryKey: ['organizations', params],
    queryFn: () =>
      unwrap(api.GET('/v1/organizations/', { params: { query: params } })),
    retry: defaultRetry,
    enabled,
  })

export const useOrganizationAccessTokens = (
  organization_id: string,
  params?: Omit<
    NonNullable<
      operations['organization_access_tokens:list']['parameters']['query']
    >,
    'organization_id'
  >,
) =>
  useQuery({
    queryKey: [
      'organization_access_tokens',
      { organization_id, ...(params || {}) },
    ],
    queryFn: () =>
      unwrap(
        api.GET('/v1/organization-access-tokens/', {
          params: {
            query: {
              organization_id,
              limit: 100,
              ...(params || {}),
            },
          },
        }),
      ),
    retry: defaultRetry,
  })

export const useCreateOrganizationAccessToken = (organization_id: string) =>
  useMutation({
    mutationFn: (
      body: Omit<schemas['OrganizationAccessTokenCreate'], 'organization_id'>,
    ) => {
      return api.POST('/v1/organization-access-tokens/', {
        body: {
          ...body,
          organization_id,
        },
      })
    },
    onSuccess: (result) => {
      const { error } = result
      if (error) {
        return
      }
      getQueryClient().invalidateQueries({
        queryKey: ['organization_access_tokens', { organization_id }],
      })
    },
  })

export const useUpdateOrganizationAccessToken = (id: string) =>
  useMutation({
    mutationFn: (body: schemas['OrganizationAccessTokenUpdate']) => {
      return api.PATCH('/v1/organization-access-tokens/{id}', {
        params: { path: { id } },
        body,
      })
    },
    onSuccess: (result) => {
      const { data, error } = result
      if (error) {
        return
      }
      getQueryClient().invalidateQueries({
        queryKey: [
          'organization_access_tokens',
          { organization_id: data.organization_id },
        ],
      })
    },
  })

export const useDeleteOrganizationAccessToken = () =>
  useMutation({
    mutationFn: (variables: schemas['OrganizationAccessToken']) => {
      return api.DELETE('/v1/organization-access-tokens/{id}', {
        params: { path: { id: variables.id } },
      })
    },
    onSuccess: (result, variables) => {
      const { error } = result
      if (error) {
        return
      }
      getQueryClient().invalidateQueries({
        queryKey: [
          'organization_access_tokens',
          { organization_id: variables.organization_id },
        ],
      })
    },
  })
