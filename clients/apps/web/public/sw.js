/* Offline fallback only: precache the branded offline page (plus the fonts it
 * uses) and serve it when a page navigation fails with no connection. All
 * other requests pass straight through to the network - no app caching, so
 * deploys behave exactly as before. */
const CACHE = 'outception-offline-v2'
const ASSETS = [
  '/offline.html',
  '/fonts/Geist-Variable.woff2',
  '/fonts/HankenGrotesk-Variable.woff2',
  '/fonts/GeistMono-Variable.woff2',
  '/assets/brand/top-spin.webp',
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() =>
        caches
          .match('/offline.html')
          .then((cached) => cached ?? Response.error()),
      ),
    )
    return
  }
  // The offline page's own fonts must resolve while disconnected.
  if (ASSETS.includes(new URL(request.url).pathname)) {
    event.respondWith(
      caches.match(request).then((cached) => cached ?? fetch(request)),
    )
  }
})

/* The morning briefing push: one notification a day per chosen briefing,
 * carrying the lead story. The payload is JSON from our own server; a push
 * without a readable payload shows nothing. */
self.addEventListener('push', (event) => {
  let data = null
  try {
    data = event.data ? event.data.json() : null
  } catch {
    data = null
  }
  if (!data || !data.title) return
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body || '',
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      tag: data.profile ? `briefing-${data.profile}` : 'briefing',
      data: { url: data.url || '/' },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = new URL(
    (event.notification.data && event.notification.data.url) || '/',
    self.location.origin,
  ).href
  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((windows) => {
        for (const client of windows) {
          if (client.url === url && 'focus' in client) return client.focus()
        }
        return self.clients.openWindow(url)
      }),
  )
})
