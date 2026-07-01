import { operations } from '@outception-com/client'

export type AuthorizeResponse =
  operations['oauth2:authorize']['responses']['200']['content']['application/json']
