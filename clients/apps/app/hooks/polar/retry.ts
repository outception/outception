import {
  ClientResponseError,
  NotFoundResponseError,
  UnauthorizedResponseError,
} from '@outception-com/client'

const authenticatingRetry = (
  failureCount: number,
  error:
    | ClientResponseError
    | UnauthorizedResponseError
    | NotFoundResponseError,
): boolean => {
  if (error instanceof UnauthorizedResponseError) {
    return false
  }

  if (error instanceof NotFoundResponseError) {
    return false
  }

  if (failureCount > 2) {
    return false
  }

  return true
}

export const defaultRetry = authenticatingRetry
