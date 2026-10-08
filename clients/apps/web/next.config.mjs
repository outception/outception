/* global process */
import path from 'node:path'
import { withSentryConfig } from '@sentry/nextjs/config'

// Mirrors src/utils/features.ts (next.config cannot import from src/); a
// test keeps the two equal. With accounts off this must be false, or a
// reader still holding a session cookie is bounced between / and /start
// forever.

const ENVIRONMENT = process.env.NEXT_PUBLIC_ENVIRONMENT || 'development'

// The Content Security Policy is built per request in src/proxy.ts (a
// nonce for every inline script); only the static headers live here.

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Emit a self-contained server bundle (.next/standalone) so the app can be
  // run as a plain Node server (node server.js) in a container. See the
  // production web Dockerfile.
  output: 'standalone',
  // The visit counter's client sends trailing-slash requests to /ingest/.
  skipTrailingSlashRedirect: true,
  // The monorepo root is two levels up; tracing from there bundles the
  // workspace deps the standalone server needs.
  outputFileTracingRoot: path.join(import.meta.dirname, '../../'),
  allowedDevOrigins: ['127.0.0.1'],
  reactStrictMode: true,
  transpilePackages: ['@outception-com/orbit'],

  // NOTE: the build runs `next build --turbopack`, so this webpack hook is
  // NOT applied. Kept only for a `next build` without the flag; don't add
  // load-bearing config here expecting it to take effect.
  webpack: (config, { dev }) => {
    if (config.cache && !dev) {
      config.cache = Object.freeze({
        type: 'memory',
      })
    }

    return config
  },

  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'avatars.githubusercontent.com',
        port: '',
        pathname: '**',
      },
    ],
  },

  async redirects() {
    return [
      // dashboard.outception.com redirections
      {
        source: '/',
        destination: '/auth',
        has: [
          {
            type: 'host',
            value: 'dashboard.outception.com',
          },
        ],
        permanent: false,
      },
      {
        source: '/:path*',
        destination: 'https://outception.com/:path*',
        has: [
          {
            type: 'host',
            value: 'dashboard.outception.com',
          },
        ],
        permanent: false,
      },
      {
        source: '/legal/terms',
        destination: '/terms',
        permanent: false,
      },
      {
        source: '/legal/privacy',
        destination: '/privacy',
        permanent: false,
      },
      // Account Settings Redirects

      {
        source: '/signup',
        destination: '/auth',
        permanent: false,
      },
    ]
  },
  async headers() {
    const baseHeaders = [
      {
        key: 'Permissions-Policy',
        value:
          'payment=(), publickey-credentials-get=(), camera=(), microphone=(), geolocation=(self)',
      },
      {
        key: 'X-Frame-Options',
        value: 'DENY',
      },
      {
        key: 'X-Content-Type-Options',
        value: 'nosniff',
      },
      {
        key: 'Referrer-Policy',
        value: 'strict-origin-when-cross-origin',
      },
      // HSTS only in deployed environments (never on plain-http localhost).
      ...(ENVIRONMENT !== 'development'
        ? [
            {
              key: 'Strict-Transport-Security',
              value: 'max-age=63072000; includeSubDomains; preload',
            },
          ]
        : []),
    ]

    return [
      {
        // Segment-bounded exclusions: bare prefixes also matched any FUTURE
        // route merely starting with these strings (say /oauth2-help), which
        // would silently lose every base security header.
        source: '/((?!(?:oauth2)(?:/|$)).*)',
        headers: baseHeaders,
      },
      {
        // Apple's universal-links manifest has no file extension, so Next
        // would serve it as octet-stream; Apple's CDN requires JSON.
        source: '/.well-known/apple-app-site-association',
        headers: [
          {
            key: 'Content-Type',
            value: 'application/json',
          },
        ],
      },
      {
        // The service worker and the offline page it serves must revalidate on
        // every load - a long-cached worker would pin an old offline page (and
        // an old fetch handler) for days.
        source: '/:file(sw\\.js|offline\\.html)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, max-age=0, must-revalidate',
          },
        ],
      },
      {
        source: '/oauth2/:path*',
        headers: [
          {
            key: 'Permissions-Policy',
            value:
              'payment=(), publickey-credentials-get=(), camera=(), microphone=(), geolocation=(self)',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
        ],
      },
    ]
  },
}

const createConfig = async () => {
  let conf = nextConfig

  // Injected content via Sentry wizard below

  conf = withSentryConfig(conf, {
    // For all available options, see:
    // https://github.com/getsentry/sentry-webpack-plugin#options

    org: 'outception',
    project: 'javascript-nextjs',

    // Pass the auth token
    authToken: process.env.SENTRY_AUTH_TOKEN,

    // Only print logs for uploading source maps in CI
    silent: !process.env.CI,

    // For all available options, see:
    // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/

    // Upload a larger set of source maps for prettier stack traces (increases build time)
    widenClientFileUpload: true,

    reactComponentAnnotation: {
      enabled: false,
    },

    // Route browser requests to Sentry through a Next.js rewrite to circumvent ad-blockers.
    // This can increase your server load as well as your hosting bill.
    // Note: Check that the configured route will not match with your Next.js middleware, otherwise reporting of client-
    // side errors will fail.
    tunnelRoute: '/monitoring',

    // Hides source maps from generated client bundles
    hideSourceMaps: true,

    // Automatically tree-shake Sentry logger statements to reduce bundle size
    disableLogger: true,
  })

  return conf
}

export default createConfig
