/* global process */
import path from 'node:path'
import createMDX from '@next/mdx'
import { withSentryConfig } from '@sentry/nextjs'
import { themeConfig } from './shiki.config.mjs'

const PREVIEW_BUILD = process.env.OUTCEPTION_PREVIEW_BUILD === '1'

// Optional PR-preview builds: derive basePath + API URL from the PR number.
// Inert in production (no-op unless the preview env vars below are set).
let previewBasePath = ''
if (
  process.env.VERCEL_GIT_PULL_REQUEST_ID &&
  process.env.OUTCEPTION_PREVIEW_BACKEND_HOST
) {
  const prNum = parseInt(process.env.VERCEL_GIT_PULL_REQUEST_ID)
  previewBasePath = `/pr-${prNum}`
  const baseUrl = `https://${process.env.OUTCEPTION_PREVIEW_BACKEND_HOST}${previewBasePath}`
  process.env.NEXT_PUBLIC_API_URL = baseUrl
  process.env.NEXT_PUBLIC_FRONTEND_BASE_URL = baseUrl
}

// Mirrors src/utils/features.ts — next.config can't import from src/.
const ACCOUNTS_ENABLED = false

const OUTCEPTION_AUTH_COOKIE_KEY =
  process.env.OUTCEPTION_AUTH_COOKIE_KEY || 'outception_session'
const ENVIRONMENT =
  process.env.VERCEL_ENV || process.env.NEXT_PUBLIC_VERCEL_ENV || 'development'

const defaultFrontendHostname = process.env.NEXT_PUBLIC_FRONTEND_BASE_URL
  ? new URL(process.env.NEXT_PUBLIC_FRONTEND_BASE_URL).hostname
  : 'outception.com'

const S3_PUBLIC_IMAGES_BUCKET_ORIGIN = process.env
  .S3_PUBLIC_IMAGES_BUCKET_HOSTNAME
  ? `${process.env.S3_PUBLIC_IMAGES_BUCKET_PROTOCOL || 'https'}://${process.env.S3_PUBLIC_IMAGES_BUCKET_HOSTNAME}${process.env.S3_PUBLIC_IMAGES_BUCKET_PORT ? `:${process.env.S3_PUBLIC_IMAGES_BUCKET_PORT}` : ''}`
  : ''
const baseCSP = `
    default-src 'self';
    connect-src 'self' ${process.env.NEXT_PUBLIC_API_URL} ${process.env.S3_UPLOAD_ORIGINS} https://maps.googleapis.com https://*.google-analytics.com;
    frame-src 'self';
    script-src 'self' ${ENVIRONMENT === 'development' ? "'unsafe-eval'" : ''} 'unsafe-inline' https://maps.googleapis.com https://www.googletagmanager.com;
    style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
    img-src 'self' blob: data: https://www.gravatar.com https://img.logo.dev https://lh3.googleusercontent.com https://avatars.githubusercontent.com ${S3_PUBLIC_IMAGES_BUCKET_ORIGIN} https://uploads.outception.com https://upload.wikimedia.org https://commons.wikimedia.org https://cdn.jsdelivr.net https://flagcdn.com https://icons.duckduckgo.com https://*.gstatic.com https://static.finnhub.io https://static2.finnhub.io https://coin-images.coingecko.com https://assets.coingecko.com https://crests.football-data.org https://a.espncdn.com https://cdn.cloudflare.steamstatic.com;
    font-src 'self';
    object-src 'none';
    base-uri 'self';
    ${ENVIRONMENT !== 'development' ? 'upgrade-insecure-requests;' : ''}
`
const nonEmbeddedCSP = `
  ${baseCSP}
  form-action 'self' ${process.env.NEXT_PUBLIC_API_URL} outception:;
  frame-ancestors 'none';
`
// Don't add form-action to the OAuth2 authorize page, as it blocks the OAuth2 redirection
// 10-years old debate about whether to block redirects with form-action or not: https://github.com/w3c/webappsec-csp/issues/8
const oauth2CSP = `
  ${baseCSP}
  frame-ancestors 'none';
`

// The mini-games (public/cube|crossword|sudoku|solitaire) render inside the wall's own
// iframe, so they must be same-origin embeddable — everything else keeps
// frame-ancestors 'none'. Self-contained pages: local scripts, inline style
// blocks, data:-embedded fonts; the crossword additionally fetches its daily
// puzzle from the API.
const gamesCSP = `
  default-src 'self';
  connect-src 'self' ${process.env.NEXT_PUBLIC_API_URL};
  script-src 'self' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data:;
  font-src 'self' data:;
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'self';
`

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Emit a self-contained server bundle (.next/standalone) so the app can be
  // run as a plain Node server (node server.js) in a container, instead of on
  // Vercel. See the production web Dockerfile.
  output: 'standalone',
  // The monorepo root is two levels up; tracing from there bundles the
  // workspace deps the standalone server needs.
  outputFileTracingRoot: path.join(import.meta.dirname, '../../'),
  allowedDevOrigins: ['127.0.0.1'],
  reactStrictMode: true,
  transpilePackages: ['shiki', '@outception-com/orbit'],
  pageExtensions: ['js', 'jsx', 'md', 'mdx', 'ts', 'tsx'],

  ...(previewBasePath && {
    basePath: previewBasePath,
    env: {
      OUTCEPTION_API_URL: `https://${process.env.OUTCEPTION_PREVIEW_BACKEND_HOST}:8443${previewBasePath}`,
    },
  }),

  ...(PREVIEW_BUILD && {
    typescript: { ignoreBuildErrors: true },
    eslint: { ignoreDuringBuilds: true },
  }),

  // This is required to support PostHog trailing slash API requests
  skipTrailingSlashRedirect: true,

  // Docs/handbook routes read MDX + the OpenAPI spec from `content/` via fs at
  // request time (dynamic fallbacks, the handbook search index). Trace those
  // files into the serverless bundle so they exist at runtime on Vercel.
  outputFileTracingIncludes: {
    '/docs/[[...slug]]': ['./content/docs/**', './content/openapi.yaml'],
    '/handbook/[[...slug]]': ['./content/handbook/**'],
    '/docs/llms.txt': ['./content/docs/**'],
    '/docs/llms-full.txt': ['./content/docs/**'],
    '/docs/search-index.json': ['./content/docs/**'],
    '/handbook/search-index.json': ['./content/handbook/**'],
    '/sitemap.xml': ['./content/docs/**'],
  },

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
      ...(process.env.S3_PUBLIC_IMAGES_BUCKET_HOSTNAME
        ? [
            {
              protocol: process.env.S3_PUBLIC_IMAGES_BUCKET_PROTOCOL || 'https',
              hostname: process.env.S3_PUBLIC_IMAGES_BUCKET_HOSTNAME,
              port: process.env.S3_PUBLIC_IMAGES_BUCKET_PORT || '',
              pathname: process.env.S3_PUBLIC_IMAGES_BUCKET_PATHNAME || '**',
            },
          ]
        : []),
      {
        protocol: 'https',
        hostname: 'avatars.githubusercontent.com',
        port: '',
        pathname: '**',
      },
    ],
  },

  async rewrites() {
    const apiUrl =
      process.env.OUTCEPTION_API_URL || process.env.NEXT_PUBLIC_API_URL
    return [
      ...(PREVIEW_BUILD && apiUrl
        ? [
            {
              source: '/v1/:path*',
              destination: `${apiUrl}/v1/:path*`,
            },
            {
              source: '/healthz',
              destination: `${apiUrl}/healthz`,
            },
            {
              source: '/openapi.json',
              destination: `${apiUrl}/openapi.json`,
            },
          ]
        : []),
      {
        source: '/ingest/static/:path*',
        destination: 'https://eu-assets.i.posthog.com/static/:path*',
      },
      {
        source: '/ingest/:path*',
        destination: 'https://eu.i.posthog.com/:path*',
      },
      {
        source: '/ingest/decide',
        destination: 'https://eu.i.posthog.com/decide',
      },
    ]
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
      {
        source: '/llms.txt',
        destination: 'https://outception.com/docs/llms.txt',
        permanent: true,
        has: [
          {
            type: 'host',
            value: 'outception.com',
          },
        ],
      },
      {
        source: '/llms-full.txt',
        destination: 'https://outception.com/docs/llms-full.txt',
        permanent: true,
        has: [
          {
            type: 'host',
            value: 'outception.com',
          },
        ],
      },

      // Legacy documentation redirects (migrated from the former Mintlify
      // docs.json). Stale, unmaintained SDK/adapter targets that don't exist in
      // this docs set were dropped; the rest map to real pages under /docs.
      { source: '/api', destination: '/docs/api-reference', permanent: true },
      {
        // Excludes this app's own route handlers (/api/blob/*):
        // redirects run BEFORE filesystem routes, so a blanket /api/:path*
        // makes them unreachable — and a 308 preserves the method, so the
        // blob upload POST re-posts to an HTML page.
        source: '/api/:path((?!blob).*)',
        destination: '/docs/api-reference',
        permanent: true,
      },
      {
        source: '/docs/api',
        destination: '/docs/api-reference',
        permanent: true,
      },
      {
        source: '/docs/api/:path*',
        destination: '/docs/api-reference',
        permanent: true,
      },
      {
        source: '/developers/webhooks',
        destination: '/docs/integrate/webhooks/endpoints',
        permanent: true,
      },
      {
        source: '/docs/developers/webhooks',
        destination: '/docs/integrate/webhooks/endpoints',
        permanent: true,
      },
      {
        source: '/developers/:path*',
        destination: '/docs/integrate/authentication',
        permanent: true,
      },
      {
        source: '/docs/developers/:path*',
        destination: '/docs/integrate/authentication',
        permanent: true,
      },
      {
        source: '/onboarding',
        destination: '/docs/introduction',
        permanent: true,
      },
      {
        source: '/docs/onboarding',
        destination: '/docs/introduction',
        permanent: true,
      },
      {
        source: '/documentation/support',
        destination: '/docs/support',
        permanent: true,
      },
      {
        source: '/documentation/integration-guides/webhooks',
        destination: '/docs/integrate/webhooks/endpoints',
        permanent: true,
      },
      {
        source: '/documentation/:path*',
        destination: '/docs/introduction',
        permanent: true,
      },

      // Logged-in user redirections. Only while accounts exist: with them off,
      // /start bounces back to / and anyone still holding a session cookie is
      // stuck in an infinite redirect and can't reach the site at all.
      ...(ACCOUNTS_ENABLED
        ? [
            {
              source: '/',
              destination: '/start',
              has: [
                {
                  type: 'cookie',
                  key: OUTCEPTION_AUTH_COOKIE_KEY,
                },
                {
                  type: 'host',
                  value: defaultFrontendHostname,
                },
              ],
              permanent: false,
            },
          ]
        : []),

      // Redirect /dashboard to correct domain if on a different domain name
      // Skip in preview builds — preview env uses a single domain via Caddy proxy
      ...(!previewBasePath
        ? [
            {
              source: '/dashboard/:path*',
              destination: `https://${defaultFrontendHostname}/dashboard/:path*`,
              missing: [
                {
                  type: 'host',
                  value: defaultFrontendHostname,
                },
                {
                  type: 'header',
                  key: 'x-forwarded-host',
                  value: defaultFrontendHostname,
                },
              ],
              permanent: false,
            },
          ]
        : []),

      {
        source: '/maintainer',
        destination: '/dashboard',
        permanent: true,
      },
      {
        source: '/maintainer/:path(.*)',
        destination: '/dashboard/:path(.*)',
        permanent: true,
      },
      {
        source: '/dashboard/:organization/overview',
        destination: '/dashboard/:organization',
        permanent: true,
      },

      // Account Settings Redirects
      {
        source: '/settings',
        destination: '/dashboard/account/preferences',
        permanent: true,
      },

      // Access tokens redirect
      {
        source: '/settings/tokens',
        destination: '/dashboard/account/developer',
        permanent: false,
      },

      // Old blog redirects

      // Fallback blog redirect
      {
        source: '/:path*',
        destination: 'https://outception.com/outception',
        has: [
          {
            type: 'host',
            value: 'blog.outception.com',
          },
        ],
        permanent: false,
      },

      // CLI Install Script
      {
        source: '/install.sh',
        destination:
          'https://raw.githubusercontent.com/outception/cli/main/install.sh',
        permanent: false,
      },

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
        key: 'Content-Security-Policy',
        value: nonEmbeddedCSP.replace(/\n/g, ''),
      },
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
        source: '/((?!oauth2|cube|crossword|sudoku|solitaire).*)',
        headers: baseHeaders,
      },
      {
        source: '/:game(cube|crossword|sudoku|solitaire)/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: gamesCSP.replace(/\n/g, ''),
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
      {
        // The game's engine/style files are effectively versionless static
        // assets — cache them for a year so repeat visits skip the ~550 KB
        // re-download entirely. index.html stays on a short cache below so
        // page-level changes still roll out.
        source: '/cube/:file((?:cube|three)\\.js|styles\\.css)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        // Game pages mount inside the wall's iframes: a short fresh window +
        // a day of stale-while-revalidate makes remounts instant (the wall
        // prefetches these) while deploys still propagate within minutes.
        source: '/:game(cube|crossword|sudoku|solitaire)/index.html',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=300, stale-while-revalidate=86400',
          },
        ],
      },
      {
        source: '/oauth2/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: oauth2CSP.replace(/\n/g, ''),
          },
          {
            key: 'Permissions-Policy',
            value:
              'payment=(), publickey-credentials-get=(), camera=(), microphone=(), geolocation=(self)',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
        ],
      },
    ]
  },
}

const createConfig = async () => {
  const withMDX = createMDX({
    options: {
      remarkPlugins: ['remark-frontmatter', 'remark-gfm'],
      rehypePlugins: [
        'rehype-slug',
        [
          '@shikijs/rehype',
          {
            themes: themeConfig,
          },
        ],
      ],
    },
  })

  let conf = withMDX(nextConfig)

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

    // Enables automatic instrumentation of Vercel Cron Monitors. (Does not yet work with App Router route handlers.)
    // See the following for more information:
    // https://docs.sentry.io/product/crons/
    // https://vercel.com/docs/cron-jobs
    automaticVercelMonitors: true,
  })

  return conf
}

export default createConfig
