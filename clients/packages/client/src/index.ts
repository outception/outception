import createOpenAPIFetchClient, {
  type FetchResponse,
  type HeadersOptions,
  type ParseAsResponse,
} from 'openapi-fetch'
import type {
  ResponseObjectMap,
  SuccessResponse,
} from 'openapi-typescript-helpers'
import type { components, paths } from './v1'

export const createClient = (
  baseUrl: string,
  token?: string,
  headers?: HeadersOptions,
) => ({
  ...createOpenAPIFetchClient<paths>({
    baseUrl,
    credentials: 'include',
    headers: {
      ...(headers ? headers : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  }),
  baseUrl,
})

export type ClientResponseErrorBody = Record<string, unknown> & {
  message?: string
}

export class ClientResponseError extends Error {
  error: ClientResponseErrorBody
  response: Response

  constructor(error: ClientResponseErrorBody, response: Response) {
    super(error.message)
    this.name = 'ClientResponseError'
    this.error = error
    this.response = response
  }
}

export class UnauthorizedResponseError extends ClientResponseError {
  constructor(error: ClientResponseErrorBody, response: Response) {
    super(error, response)
    this.name = 'UnauthorizedResponseError'
  }
}

export class NotFoundResponseError extends ClientResponseError {
  constructor(error: ClientResponseErrorBody, response: Response) {
    super(error, response)
    this.name = 'NotFoundResponseError'
  }
}

export class TooManyRequestsResponseError extends ClientResponseError {
  constructor(error: ClientResponseErrorBody, response: Response) {
    super(error, response)
    this.name = 'TooManyRequestsResponseError'
  }
}

export const unwrap = async <
  T extends Record<string | number, unknown>,
  Options,
  Media extends `${string}/${string}`,
>(
  p: Promise<FetchResponse<T, Options, Media>>,
  handlers?: {
    [status: number]: (response: Response) => never
  },
): Promise<
  ParseAsResponse<SuccessResponse<ResponseObjectMap<T>, Media>, Options>
> => {
  const { data, error, response } = await p
  if (handlers) {
    const handler = handlers[response.status]
    if (handler) {
      return handler(response)
    }
  }

  if (response.status === 429) {
    throw new TooManyRequestsResponseError(
      { message: 'Too Many Requests' },
      response,
    )
  }

  if (error) {
    if (response.status === 401) {
      throw new UnauthorizedResponseError(error, response)
    } else if (response.status === 404) {
      throw new NotFoundResponseError(error, response)
    }

    throw new ClientResponseError(error, response)
  }

  // Only a genuinely absent body is an error. `!data` also rejected a valid
  // 204 No Content and any endpoint legitimately returning null/0/""/false.
  if (data === undefined) {
    if (response.status !== 204) {
      throw new Error('No data returned')
    }
    // A 204 has no body by definition; the generated types still describe the
    // success payload, so this is the one place the cast is warranted.
    return undefined as ParseAsResponse<
      SuccessResponse<ResponseObjectMap<T>, Media>,
      Options
    >
  }
  return data
}

export const isValidationError = (
  detail: unknown,
): detail is {
  loc: (string | number)[]
  msg: string
  type: string
}[] => {
  // Guard the element access: `[]` made this `undefined.loc` → TypeError. It
  // runs on every retry decision and in the error fallback, i.e. only ever on
  // the error path - so it turned a recoverable API error into a crash.
  return (
    Array.isArray(detail) && detail.length > 0 && detail[0]?.loc !== undefined
  )
}

export type { Middleware } from 'openapi-fetch'
export * as enums from './enums'
export type { components, operations, paths } from './v1'
export type schemas = components['schemas']
export type Client = ReturnType<typeof createClient>
