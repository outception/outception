# Stage 1: Build the email renderer binary
FROM node:22-slim AS build-emails-bin

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable
WORKDIR /app

COPY ./emails/pnpm-lock.yaml .
COPY ./emails/package.json .
RUN pnpm install --frozen-lockfile

COPY ./emails/src src/
COPY ./emails/tsconfig.json .
COPY ./emails/tsup.config.js .

RUN pnpm run build

# Stage 2: Final production image
FROM --platform=$BUILDPLATFORM python:3.14-slim AS production
LABEL org.opencontainers.image.source=https://github.com/outception/outception
LABEL org.opencontainers.image.description="Outception"
LABEL org.opencontainers.image.licenses=Apache-2.0
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_CACHE=1
ENV UV_NO_SYNC=1
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app/server

RUN --mount=type=bind,source=uv.lock,target=uv.lock \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  apt-get update \
  && apt-get install -y \
  git \
  build-essential \
  redis \
  libpq-dev \
  && uv sync --no-group dev --frozen \
  && uv tool install tinybird --python 3.13 \
  && apt-get autoremove -y build-essential

ADD . /app/server/

COPY --from=build-emails-bin /app/bin/react-email-pkg /app/server/
ENV OUTCEPTION_EMAIL_RENDERER_BINARY_PATH=/app/server/react-email-pkg

ARG RELEASE_VERSION
ENV RELEASE_VERSION=${RELEASE_VERSION}

# Drop privileges: run the app as a non-root user so an RCE / container escape
# doesn't start as uid 0. The app only needs read/exec on /app (and a
# world-writable tmp for the prometheus multiproc dir), so own /app to the user.
RUN groupadd --system --gid 1001 outception \
  && useradd --system --uid 1001 --gid outception --home-dir /app outception \
  && chown -R outception:outception /app
USER outception

CMD ["uv", "run", "uvicorn", "outception.app:app", "--host", "0.0.0.0", "--port", "10000", "--limit-max-requests", "50000", "--limit-max-requests-jitter", "10000", "--timeout-graceful-shutdown", "30"]

# Stage 3: AWS Lambda image (SQS-driven background tasks, POC)
FROM production AS lambda

RUN uv pip install awslambdaric

ENTRYPOINT ["uv", "run", "python", "-m", "awslambdaric"]
CMD ["outception.worker.aws_lambda.handler"]
