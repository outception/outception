import type { MetadataRoute } from 'next'

// Web app manifest — makes "Add to Home Screen" install as a standalone app
// with the Outception name and icon. iOS uses app/apple-icon.png + the
// apple-mobile-web-app meta (see layout.tsx); Android uses these icons.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Outception',
    short_name: 'Outception',
    description: 'A live news wall with pay-to-promote.',
    start_url: '/',
    display: 'standalone',
    background_color: '#fdf4ec',
    theme_color: '#fdf4ec',
    icons: [
      { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      {
        src: '/icon-512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'any',
      },
    ],
  }
}
