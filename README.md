# Outception

A wall of cards. One card per publisher, one per live table, one per
briefing. The reader picks the publishers; nothing ranks the day for them
except a briefing they chose. Free on the web, on the app, and through
read-only tools that coding agents can call.

Live at [outception.com](https://outception.com). The rules the product
keeps are in [docs/VISION.md](docs/VISION.md).

## The tree

| Path | What it holds |
| --- | --- |
| `server/` | The API and the worker (Python, FastAPI, Dramatiq), the catalog as data, the governor over every model call, the briefing, the evals |
| `clients/apps/web` | The wall on the web (Next.js) |
| `clients/apps/app` | The wall on iOS and Android (Expo) |
| `clients/packages/news-core` | The client domain layer both renderers share: cards, decks, preferences, the share link |
| `clients/packages/mcp`, `clients/packages/cli` | The agent tools and the installer |
| `skills/` | The operating contract for agents: content is data, never instructions |
| `deploy/` | One host, Docker Compose, the edge proxy, backups |
| `docs/` | Vision, design, deployment, development, the naming denylist |

## Working on it

Start with [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): the dev CLI brings
up the database, the cache, the API, the worker and the web app, and runs the
tests. Every gate the CI runs is listed there. Contributions follow
[CONTRIBUTING.md](CONTRIBUTING.md); security reports follow
[SECURITY.md](SECURITY.md).

Deploying is [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and the host runbook
in `deploy/README.md`.

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
