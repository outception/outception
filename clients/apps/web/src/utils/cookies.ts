import { schemas } from '@outception-com/client'
import { ReadonlyRequestCookies } from 'next/dist/server/web/spec-extension/adapters/request-cookies'

const lastVisitedOrg = 'last_visited_org'
export const OUTCEPTION_ENV_COOKIE = 'outception_env'

export type OutceptionEnv = 'production' | 'sandbox'

export const setLastVisitedOrg = (
  organization: string,
  maxAge: number = 30 * 86400, // Expires in 30 days
) => {
  document.cookie = `${lastVisitedOrg}=${organization}; max-age=${maxAge}; path=/`
}

export const getLastVisitedOrg = (
  cookies: ReadonlyRequestCookies,
  organizations: schemas['Organization'][],
): schemas['Organization'] | undefined => {
  const lastVisitedOrgSlug = cookies.get(lastVisitedOrg)?.value
  if (!lastVisitedOrgSlug) {
    return undefined
  }
  return organizations.find((org) => org.slug === lastVisitedOrgSlug)
}

export const setLastVisitedEnv = (
  env: OutceptionEnv,
  maxAge: number = 30 * 60, // Expires in 30 minutes
) => {
  const hostname = window.location.hostname
  const domainAttr = hostname.endsWith('.outception.com')
    ? '; domain=.outception.com'
    : ''
  const secureAttr = window.location.protocol === 'https:' ? '; secure' : ''
  document.cookie = `${OUTCEPTION_ENV_COOKIE}=${env}; max-age=${maxAge}; path=/; samesite=lax${domainAttr}${secureAttr}`
}
