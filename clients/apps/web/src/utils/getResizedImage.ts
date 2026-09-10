const S3_HOST = 'outception-public-files.s3.amazonaws.com'
const CDN_HOST = 'uploads.outception.com'

// Must match the backend defined list in lambda/image-resizer/handler.py
const SUPPORTED_WIDTHS = [
  48, 64, 96, 128, 192, 256, 384, 512, 768, 1024, 1440, 1920,
]

function getHostname(url: string): string | null {
  try {
    return new URL(url).hostname
  } catch {
    return null
  }
}

export function getResizedImage(
  url: string | null | undefined,
  approximateWidth: number,
): string {
  if (!url) return ''

  const hostname = getHostname(url)
  if (hostname !== S3_HOST) return url

  // Assume 2x displays: this also runs in SSR and email where the real DPR is unknown.
  const retinaWidth = approximateWidth * 2
  const width =
    SUPPORTED_WIDTHS.find((w) => w >= retinaWidth) ??
    SUPPORTED_WIDTHS[SUPPORTED_WIDTHS.length - 1]

  const cdnUrl = url.replace(S3_HOST, CDN_HOST)
  return `${cdnUrl}${cdnUrl.includes('?') ? '&' : '?'}width=${width}`
}
