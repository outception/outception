import { CONFIG } from '@/utils/config'

// Serve /ads.txt from the AdSense publisher id so Google can verify we
// authorized it to sell our inventory. 404 until a publisher id is configured.
// The ads.txt id is the publisher id WITHOUT the "ca-" prefix; f08c47fec0942fa0
// is Google's fixed certification-authority id.
export function GET(): Response {
  const client = CONFIG.ADSENSE_CLIENT
  if (!client) {
    return new Response('', { status: 404 })
  }
  const publisherId = client.replace(/^ca-/, '')
  const body = `google.com, ${publisherId}, DIRECT, f08c47fec0942fa0\n`
  return new Response(body, {
    headers: { 'content-type': 'text/plain; charset=utf-8' },
  })
}
