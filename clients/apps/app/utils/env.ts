/**
 * The two deployment URLs, resolved once.
 *
 * These used to be inlined at every call site with inconsistent fallbacks:
 * `https://api.outception.com` in the API client, weather and the users hook,
 * but `http://127.0.0.1:3000` for the web URL and the OAuth endpoints. A build
 * missing the env vars was therefore half-wired - API calls went to production
 * while legal links and token requests pointed at a localhost that Android's
 * cleartext policy blocks, failing opaquely.
 *
 * Now there is one rule: dev falls back to localhost, a release build falls
 * back to production. Deliberately NOT a hard throw - the API client already
 * defaulted to production and worked, so failing startup here would turn a
 * previously-fine build into one that won't launch.
 */
const resolve = (value: string | undefined, dev: string, release: string) =>
  value || (__DEV__ ? dev : release)

export const API_URL = resolve(
  process.env.EXPO_PUBLIC_OUTCEPTION_SERVER_URL,
  'http://127.0.0.1:8000',
  'https://api.outception.com',
)

export const WEB_URL = resolve(
  process.env.EXPO_PUBLIC_OUTCEPTION_WEB_URL,
  'http://127.0.0.1:3000',
  'https://outception.com',
)
