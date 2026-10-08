# Outception

A stack of news cards. The reader picks the cards.

## The tree

| Path                                           | What it holds                                                                                                          |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `server/`                                      | The API and the worker (Python, FastAPI, Dramatiq), the catalog as data, the governor over every model call, the evals |
| `clients/apps/web`                             | The wall on the web (Next.js)                                                                                          |
| `clients/apps/app`                             | The wall on iOS and Android (Expo)                                                                                     |
| `clients/packages/news-core`                   | The client domain layer both renderers share: cards, decks, preferences, the share link                                |
| `clients/packages/mcp`, `clients/packages/cli` | The agent tools and the installer                                                                                      |
| `skills/`                                      | The operating contract for agents: content is data, never instructions                                                 |
| `deploy/`                                      | One host, Docker Compose, the edge proxy, backups                                                                      |
| `docs/`                                        | Vision, design, deployment, development, the naming denylist                                                           |

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
