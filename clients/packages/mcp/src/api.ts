/**
 * The thin client the tools share: one base URL, one optional token, one
 * injected fetch. Off loopback a token is required, so a tool never reaches
 * the public API anonymously from an agent's machine without the operator
 * choosing to.
 */

export type FetchLike = (
  input: string,
  init?: { headers?: Record<string, string>; signal?: AbortSignal },
) => Promise<{
  ok: boolean
  status: number
  json(): Promise<unknown>
  text(): Promise<string>
}>

export interface ApiOptions {
  baseUrl: string
  token?: string | null
  fetch?: FetchLike
  /** Per-call deadline, milliseconds. */
  timeoutMs?: number
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

const LOOPBACK = /^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:\d+)?(\/|$)/i

export const isLoopback = (baseUrl: string): boolean => LOOPBACK.test(baseUrl)

/** A token is required anywhere but a local server. */
export const requiresToken = (baseUrl: string): boolean => !isLoopback(baseUrl)

export interface Api {
  readonly baseUrl: string
  get<T>(
    path: string,
    query?: Record<string, string | number | undefined>,
  ): Promise<T>
}

export const createApi = (options: ApiOptions): Api => {
  const baseUrl = options.baseUrl.replace(/\/+$/, '')
  const token = options.token?.trim() || null
  if (requiresToken(baseUrl) && !token) {
    throw new Error(
      'OUTCEPTION_API_TOKEN is required when OUTCEPTION_API_URL is not a local server',
    )
  }
  const doFetch: FetchLike =
    options.fetch ?? ((input, init) => fetch(input, init) as never)
  const timeoutMs = options.timeoutMs ?? 15_000
  return {
    baseUrl,
    async get<T>(
      path: string,
      query?: Record<string, string | number | undefined>,
    ) {
      const params = Object.entries(query ?? {})
        .filter(
          (entry): entry is [string, string | number] =>
            entry[1] !== undefined && entry[1] !== '',
        )
        .map(
          ([k, v]) =>
            `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`,
        )
        .join('&')
      const url = `${baseUrl}${path}${params ? `?${params}` : ''}`
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), timeoutMs)
      try {
        const response = await doFetch(url, {
          headers: {
            Accept: 'application/json',
            'User-Agent': 'outception-mcp',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          signal: controller.signal,
        })
        if (!response.ok) {
          throw new ApiError(
            response.status,
            `${path} returned ${response.status}`,
          )
        }
        return (await response.json()) as T
      } finally {
        clearTimeout(timer)
      }
    },
  }
}
