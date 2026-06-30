# Production image for the Next.js web app (clients/apps/web).
# Build context MUST be the `clients/` directory (the pnpm workspace root):
#   docker build -f deploy/web.Dockerfile clients/
# Produces a self-contained Node server from Next's `output: 'standalone'`.

# ---- Builder ----------------------------------------------------------------
FROM node:24-slim AS builder
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
# sharp / native deps need these at build time.
RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 build-essential \
  && rm -rf /var/lib/apt/lists/* \
  && corepack enable
WORKDIR /app

# Copy the whole workspace (turbo prunes/builds only what web needs).
COPY . .

RUN pnpm install --frozen-lockfile

# NEXT_PUBLIC_* are inlined into the client bundle at build time.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_FRONTEND_BASE_URL
ARG NEXT_PUBLIC_ENVIRONMENT=production
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_FRONTEND_BASE_URL=${NEXT_PUBLIC_FRONTEND_BASE_URL}
ENV NEXT_PUBLIC_ENVIRONMENT=${NEXT_PUBLIC_ENVIRONMENT}
ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm turbo run build --filter=web

# ---- Runner -----------------------------------------------------------------
FROM node:24-slim AS runner
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
WORKDIR /app

RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 nextjs

# Standalone output is traced from the monorepo root (outputFileTracingRoot),
# so server.js lives at apps/web/server.js inside the standalone bundle.
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

USER nextjs
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
