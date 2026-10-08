# Stage 1: build the email renderer binary
FROM node:24-slim AS build-emails-bin

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable
WORKDIR /app

COPY emails/pnpm-lock.yaml emails/package.json emails/pnpm-workspace.yaml ./
RUN --mount=type=cache,target=/pnpm/store \
  pnpm install --frozen-lockfile --store-dir=/pnpm/store

COPY emails/src src/
COPY emails/tsconfig.json emails/tsup.config.js ./
RUN pnpm run build

# Stage 2: the production image. One image runs migrate, api and worker; the
# compose file picks the command. The stage name is what the production
# compose targets, so it stays `production`.
FROM --platform=$BUILDPLATFORM python:3.14-slim AS production

LABEL org.opencontainers.image.source=https://github.com/outception/outception \
  org.opencontainers.image.description="Outception" \
  org.opencontainers.image.licenses=Apache-2.0

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
  UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_NO_SYNC=1 \
  UV_FROZEN=1 \
  PATH="/root/.local/bin:$PATH"

WORKDIR /app/server

RUN --mount=type=bind,source=uv.lock,target=uv.lock \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  --mount=type=cache,target=/root/.cache/uv \
  apt-get update \
  && apt-get install -y build-essential curl git libpq5 \
  && uv sync --no-group dev --frozen \
  && apt-get autoremove -y build-essential \
  && rm -rf /var/lib/apt/lists/*

# The renderer binary in its own layer before the source, so it keeps its
# digest and is not re-uploaded when only the source changes.
COPY --from=build-emails-bin /app/bin/react-email-pkg /app/server/
COPY . /app/server/

ARG RELEASE_VERSION
ENV RELEASE_VERSION=${RELEASE_VERSION} \
  OUTCEPTION_EMAIL_RENDERER_BINARY_PATH=/app/server/react-email-pkg

# Drop privileges: run the app as a non-root user so a container escape does
# not start as uid 0. The code stays owned by root and read-only to that
# user, so a compromised process cannot rewrite what runs next; it needs
# read and exec on /app, and only tmp (the prometheus multiprocess directory,
# the package manager's cache) is writable.
RUN groupadd --system --gid 1001 outception \
  && useradd --system --uid 1001 --gid outception --home-dir /tmp --no-create-home outception \
  && python -m compileall -q /app/server/outception \
  && chmod -R a+rX /app \
  && mkdir -p /tmp/uv-cache /data/media \
  && chown outception:outception /tmp/uv-cache /data/media
ENV UV_CACHE_DIR=/tmp/uv-cache \
  UV_NO_SYNC=1 \
  UV_FROZEN=1
USER outception

# No --limit-max-requests: uvicorn runs here without a process manager, so
# reaching the limit would exit the process and take the container down
# rather than recycle a worker.
CMD ["uv", "run", "uvicorn", "outception.app:app", \
  "--host", "0.0.0.0", "--port", "10000", \
  "--timeout-graceful-shutdown", "30"]
