// Claude-backed translation for UI strings. Used by translate.ts when
// ANTHROPIC_API_KEY is set (CI secret); Google remains the keyless fallback.
// UI labels are short and context-poor - a model that understands "Save" is a
// button beats word-for-word MT here.

const API_URL = 'https://api.anthropic.com/v1/messages'
const MODEL = 'claude-haiku-4-5-20251001'
const CHUNK_SIZE = 60
/** Attempts per chunk before it is split. */
const MAX_ATTEMPTS = 4

export const claudeEnabled = (): boolean => !!process.env.ANTHROPIC_API_KEY

const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms))

/** Thrown for a status worth waiting out (rate limit, overload, 5xx) rather
 * than treating as a bad reply. Carries the server's own `retry-after` when it
 * sent one. */
class RetryableStatus extends Error {
  constructor(
    readonly status: number,
    readonly retryAfterMs: number | null,
  ) {
    super(`Anthropic API ${status}`)
  }
}

const retryDelayMs = (error: unknown, attempt: number): number | null => {
  // Only wait out transport and server-side errors. A shape mismatch is the
  // model's reply being wrong, and waiting cannot change that - that case
  // still retries once and then splits the chunk.
  if (error instanceof RetryableStatus) {
    // Exponential with jitter, capped, unless the server named a delay.
    return (
      error.retryAfterMs ??
      Math.min(2 ** attempt * 1_000, 30_000) + Math.random() * 1_000
    )
  }
  if (error instanceof TypeError) return Math.min(2 ** attempt * 1_000, 30_000)
  return null
}

async function requestChunk(
  texts: string[],
  language: string,
): Promise<string[]> {
  const res = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'x-api-key': process.env.ANTHROPIC_API_KEY ?? '',
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 8000,
      system:
        'You translate user-interface strings for a news reader app from' +
        ` English to ${language}. The input is a JSON array of strings.` +
        ' Reply with ONLY a JSON array of the translations, same length,' +
        ' same order. Keep [[0]]-style tokens exactly as they appear. Use' +
        ' the short, natural phrasing a native app would use for UI labels.' +
        ' No explanations, no markdown.',
      messages: [{ role: 'user', content: JSON.stringify(texts) }],
    }),
  })
  if (!res.ok) {
    if (res.status === 429 || res.status === 529 || res.status >= 500) {
      const header = res.headers.get('retry-after')
      const seconds = header === null ? Number.NaN : Number(header)
      throw new RetryableStatus(
        res.status,
        Number.isFinite(seconds) ? seconds * 1_000 : null,
      )
    }
    throw new Error(`Anthropic API ${res.status}`)
  }
  const data = (await res.json()) as { content?: { text?: string }[] }
  const raw = (data.content ?? []).map((b) => b.text ?? '').join('')
  const start = raw.indexOf('[')
  const end = raw.lastIndexOf(']')
  if (start === -1 || end === -1 || end <= start) {
    throw new Error('no JSON array in response')
  }
  const parsed = JSON.parse(raw.slice(start, end + 1)) as unknown
  if (
    !Array.isArray(parsed) ||
    parsed.length !== texts.length ||
    !parsed.every((s): s is string => typeof s === 'string')
  ) {
    throw new Error('response shape mismatch')
  }
  return parsed
}

// A malformed response (truncation, stray prose, unescaped quote) retries
// once, then splits the chunk in half - one bad string can't sink a locale.
//
// A rate limit or an overloaded server is NOT a malformed response, and
// splitting on one makes things worse: the halves hit the same limit, split
// again, and a throttled run degenerates into a storm of single-string
// requests. Those wait for the server's own `retry-after` (or a backoff)
// and retry the chunk whole, which is what turned hour-long runs into
// multi-hour ones.
async function translateChunk(
  texts: string[],
  language: string,
  attempt = 0,
): Promise<string[]> {
  try {
    return await requestChunk(texts, language)
  } catch (error) {
    const delay = retryDelayMs(error, attempt)
    if (delay !== null) {
      // Splitting cannot help a throttled server, so give up on the chunk
      // rather than turning one limit into a burst of smaller requests.
      if (attempt >= MAX_ATTEMPTS) throw error
      await sleep(delay)
      return translateChunk(texts, language, attempt + 1)
    }
    if (attempt === 0) return translateChunk(texts, language, 1)
    if (texts.length > 1) {
      const mid = Math.ceil(texts.length / 2)
      return [
        ...(await translateChunk(texts.slice(0, mid), language, 1)),
        ...(await translateChunk(texts.slice(mid), language, 1)),
      ]
    }
    throw error
  }
}

export async function claudeTranslateBatch(
  texts: string[],
  language: string,
): Promise<string[]> {
  const out: string[] = []
  for (let i = 0; i < texts.length; i += CHUNK_SIZE) {
    out.push(
      ...(await translateChunk(texts.slice(i, i + CHUNK_SIZE), language)),
    )
  }
  return out
}
