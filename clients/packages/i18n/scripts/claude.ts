// Claude-backed translation for UI strings. Used by translate.ts when
// ANTHROPIC_API_KEY is set (CI secret); Google remains the keyless fallback.
// UI labels are short and context-poor — a model that understands "Save" is a
// button beats word-for-word MT here.

const API_URL = 'https://api.anthropic.com/v1/messages'
const MODEL = 'claude-haiku-4-5-20251001'
const CHUNK_SIZE = 60

export const claudeEnabled = (): boolean => !!process.env.ANTHROPIC_API_KEY

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
  if (!res.ok) throw new Error(`Anthropic API ${res.status}`)
  const data = (await res.json()) as { content?: { text?: string }[] }
  const raw = (data.content ?? []).map((b) => b.text ?? '').join('')
  const start = raw.indexOf('[')
  const end = raw.lastIndexOf(']')
  if (start === -1 || end <= start) throw new Error('no JSON array in response')
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
// once, then splits the chunk in half — one bad string can't sink a locale.
async function translateChunk(
  texts: string[],
  language: string,
  attempt = 0,
): Promise<string[]> {
  try {
    return await requestChunk(texts, language)
  } catch (error) {
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
