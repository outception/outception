import { ImageResponse } from 'next/og'

// Per-card social-share image. Rendered on demand for a shared card link — the
// source name (a proper noun, unchanged across languages) plus a subtitle the
// caller already translated to the sharer's language. No runtime font fetch, so
// it always produces a PNG for a crawler.

export const runtime = 'edge'

const SIZE = { width: 1200, height: 630 }

// The brand sparkle mark (same silhouette as LogoIcon), painted in a fixed red
// ramp so the share card matches the app icon / social avatar regardless of the
// per-source accent. Inlined as a self-contained SVG (no CSS tokens) so the OG
// renderer can rasterise it.
const STAR_PATH =
  'M5059 5751 c-93 -30 -117 -61 -228 -285 -158 -319 -317 -543 -555 -782 -255 -255 -523 -440 -866 -597 -113 -52 -151 -81 -181 -139 -44 -87 -33 -186 29 -258 28 -33 68 -57 196 -119 336 -161 579 -332 826 -580 236 -237 396 -462 552 -778 80 -163 108 -210 140 -237 83 -71 213 -71 296 0 32 27 60 74 140 237 156 314 317 542 552 778 246 247 485 416 816 575 137 66 178 91 206 124 78 91 74 223 -10 313 -14 15 -116 72 -226 126 -319 158 -544 317 -782 555 -236 236 -397 463 -552 775 -105 212 -125 242 -185 272 -44 23 -128 33 -168 20z'

const gemSvg = `<svg width="120" height="120" viewBox="288 160 448 448" xmlns="http://www.w3.org/2000/svg"><defs><radialGradient id="d" cx="0.5" cy="0.28" r="0.5"><stop offset="0" stop-color="#ff9d97"/><stop offset="0.32" stop-color="#e5271f"/><stop offset="0.75" stop-color="#c01717"/><stop offset="1" stop-color="#9c1212"/></radialGradient><linearGradient id="t" x1="0" y1="384" x2="0" y2="578" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#760d0d"/><stop offset="0.3" stop-color="#9c1212"/><stop offset="1" stop-color="#f5645c"/></linearGradient><clipPath id="c"><path transform="translate(0,768) scale(0.1,-0.1)" d="${STAR_PATH}"/></clipPath></defs><g clip-path="url(#c)"><rect x="288" y="160" width="448" height="448" fill="url(#d)"/><path d="M296 374 Q512 450 728 374 L728 624 L296 624 Z" fill="url(#t)"/><path d="M322 384 Q512 436 702 384" stroke="#560909" stroke-width="4" fill="none" opacity="0.45"/><path d="M330 380 Q512 426 694 380" stroke="#ffd0cd" stroke-width="3" fill="none" opacity="0.55"/></g></svg>`

const gemDataUri = `data:image/svg+xml;base64,${btoa(gemSvg)}`

export function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const title = (searchParams.get('title') || 'Outception').slice(0, 80)
  const subtitle = (searchParams.get('subtitle') || 'Live on Outception').slice(
    0,
    120,
  )
  const accent = /^#[0-9a-fA-F]{3,8}$/.test(searchParams.get('color') || '')
    ? (searchParams.get('color') as string)
    : '#e5271f'

  return new ImageResponse(
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        width: '100%',
        height: '100%',
        backgroundColor: '#09090b',
        backgroundImage: `radial-gradient(900px 520px at 82% 8%, ${accent}55, transparent 60%), radial-gradient(760px 520px at 0% 108%, ${accent}22, transparent 58%)`,
        padding: '72px',
        fontFamily: 'sans-serif',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={gemDataUri} width={64} height={64} alt="" />
        <div
          style={{
            display: 'flex',
            color: '#ffffff',
            fontSize: '40px',
            fontWeight: 700,
            letterSpacing: '-1px',
          }}
        >
          Outception
        </div>
        <div
          style={{
            display: 'flex',
            marginLeft: '4px',
            color: '#a1a1aa',
            fontSize: '28px',
          }}
        >
          · Live news wall
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div
          style={{
            fontSize: '104px',
            fontWeight: 700,
            color: '#ffffff',
            lineHeight: 1.02,
            letterSpacing: '-3px',
            maxWidth: '1040px',
          }}
        >
          {title}
        </div>
        <div
          style={{
            fontSize: '44px',
            color: '#d4d4d8',
            maxWidth: '940px',
            lineHeight: 1.3,
          }}
        >
          {subtitle}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div
          style={{
            width: '18px',
            height: '18px',
            borderRadius: '9999px',
            backgroundColor: accent,
          }}
        />
        <div style={{ display: 'flex', color: '#a1a1aa', fontSize: '32px' }}>
          outception.com
        </div>
      </div>
    </div>,
    SIZE,
  )
}
