/**
 * Defense in depth for news links: items come from untrusted external
 * feeds, so only an absolute http(s) URL ever reaches an href or the OS link
 * opener. The server neutralizes these too; this is the second line.
 */

const HTTP_URL = /^https?:\/\/\S+$/i
const HOST = /^https?:\/\/([^/:?#]+)/i

/** Only absolute http(s) URLs leave the client. */
export const isHttpUrl = (url: string | null | undefined): url is string =>
  !!url && HTTP_URL.test(url)

/** The URL when it is safe to link, else undefined so the anchor renders
 * without an href and a `javascript:` or `data:` URL cannot be clicked. */
export const safeExternalHref = (
  url: string | null | undefined,
): string | undefined => (isHttpUrl(url) ? url : undefined)

export const hostOf = (url: string | null | undefined): string | null =>
  (isHttpUrl(url) && HOST.exec(url)?.[1]?.toLowerCase()) || null

/** Hosts whose pages are never the article (video players), so the summary
 * endpoint refuses them and a tap opens the link instead. Aggregator links
 * resolve server-side, so they try. */
export const UNSUMMARIZABLE_HOSTS: ReadonlySet<string> = new Set([
  'youtube.com',
  'www.youtube.com',
  'm.youtube.com',
  'youtu.be',
])

export const isSummarizable = (url: string | null | undefined): boolean => {
  const host = hostOf(url)
  return !!host && !UNSUMMARIZABLE_HOSTS.has(host)
}
