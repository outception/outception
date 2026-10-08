<!-- doc-covers: .github/workflows/test_server.yaml .github/workflows/test_client.yaml server/pyproject.toml -->
<!-- doc-verified: d5090b2 -->

# Testing

Every gate below runs in CI: the server gates on a pull request that touches `server/`, `docs/`, `deploy/` or the workflows (the boundary, env and naming checks read those), the client gates on one that touches `clients/`. Every action those workflows call is pinned to a commit, and each job declares only the permissions it needs. Run them locally before
pushing; the staged-file hooks (`.lefthook.yml`) run the fast ones on commit.

## Server (`server/`)

| Gate                 | Command                                                                          | What it catches                                                                                                               |
| -------------------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Tests                | `OUTCEPTION_ENV=testing uv run python -m pytest tests -q`                        | Behaviour: every endpoint, service and task, against a real database and a fake cache                                         |
| Types                | `uv run task lint_types`                                                         | mypy over the package, the scripts and the tests                                                                              |
| Lint and format      | `uv run task lint_check`                                                         | ruff, plus the custom AST rules                                                                                               |
| Env contract         | `uv run python -m scripts.check_env_vars`                                        | Settings and the two env examples drifting apart                                                                              |
| Env examples         | `uv run python -m scripts.env_examples --check` and `tests/test_env_examples.py` | A typed setting without a value in a production example, or an example that does not load                                     |
| Migrations           | `uv run task check_migrations`                                                   | More than one head, or a migration filed out of order                                                                         |
| Naming               | `uv run python -m scripts.linters.names --strict`                                | A third party named outside the allowlisted paths                                                                             |
| Key boundary         | `uv run python -m scripts.linters.llm_key_boundary`                              | A model key read outside the provider modules                                                                                 |
| Evals                | `uv run python -m evals.run --suite scrub`                                       | The scrubber's recall and false positives; the other suites run on saved outputs or live under their own cap                  |
| OpenAPI              | `uv run python -m scripts.api_docs --check`                                      | The committed public schema and reference drifting from the routes; the client regeneration check covers the generated client |
| Publication boundary | `tests/test_publication_boundary.py`                                             | A deploy or binary job leaving the protected environment                                                                      |
| Deck parity          | `tests/cards/test_deck.py` and `news-core/src/deck.test.ts`                      | The server and client composers disagreeing on a shared fixture                                                               |

Tests use `server/.env.testing`, create their own database per worker, and
never reach the network: every provider takes an injected fetch.

## Clients (`clients/`)

| Gate                | Command                                                                                  | What it catches                                                                                                            |
| ------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Lint and boundaries | `pnpm lint`                                                                              | oxlint, and news-core importing a renderer or an app importing the other                                                   |
| Format              | `pnpm format:check`                                                                      | oxfmt, Markdown included                                                                                                   |
| Types               | `pnpm typecheck`                                                                         | tsc in every package and app                                                                                               |
| Web tests           | `pnpm --filter web test`                                                                 | vitest with jsdom: the card family, the deck, the share link, the auto-play control, the keyboard and reduced-motion rules |
| App tests           | `pnpm --filter @outception-com/app test`                                                 | jest: the auth refresher and middleware, the news helpers, the lint rules                                                  |
| news-core           | `pnpm --filter @outception-com/news-core test`                                           | The reducers and helpers, in node, with the shared deck fixture                                                            |
| Agent tools         | `pnpm --filter @outception-com/mcp test` and `--filter @outception-com/cli test`         | Every tool's limits and validation; the installer's merges                                                                 |
| Strings             | `pnpm --filter @outception-com/i18n check-keys`                                          | A key used but missing                                                                                                     |
| Naming              | `pnpm exec tsx scripts/check-names.ts --strict`                                          | A third party named outside the allowlisted paths                                                                          |
| Build and budget    | `pnpm --filter web exec next build --turbopack && pnpm exec tsx scripts/check-budget.ts` | A build failure, or the wall's scripts over budget                                                                         |
| Doctor              | `cd apps/app && npx expo-doctor`                                                         | The app's dependencies out of step with the SDK                                                                            |
| Docs                | `node scripts/check-doc-freshness.mts --check` (repository root)                         | A spec whose covered paths changed since it was verified                                                                   |

## On the rig

Two gates need a device or a browser and run by hand before a review:
screenshots of the wall, the hand, a table, a feed and the Products card in both tones and both looks, and the Android dev build
walkthrough (login with a code, the wall, a summary, the first-launch
welcome).
