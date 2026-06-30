import { useAuth } from '@/hooks/auth'

// Permissions derive directly from organization membership: any member is
// granted organization permissions.
export type OrganizationPermission = string

export const useHasPermission = (
  organizationId: string | undefined,
  _permission: OrganizationPermission,
): boolean | undefined => {
  const { userOrganizations } = useAuth()
  if (!organizationId) return false
  return userOrganizations.some((o) => o.id === organizationId)
}
