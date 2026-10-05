<!-- doc-covers: server/tests/conftest.py clients/apps/web/vitest.config.ts clients/packages/news-core/vitest.config.ts -->
<!-- doc-verified: 06ea109 -->

# Coverage

What the tests cover, by area, and what they deliberately do not. There is
no numeric threshold in CI: a number invites tests that assert nothing.
Coverage is reviewed by reading this page against a change.

## Server

| Area | Covered by | Notes |
| --- | --- | --- |
| Catalog | `tests/news/catalog`, parity fixtures | Every id referenced resolves; the roster, the search index and the default deck match the live tree's fixtures with one declared addition |
| Deck composer | `tests/cards/test_deck.py` | The precedence rule, the country swaps and injections, the shared fixture with the client |
| Cards and story | `tests/cards`, `tests/news/test_endpoints.py` | The envelope per kind, the signal state, the strip, the story route |
| Summaries and the governor | `tests/news/summaries` | Key pools, cooldowns, caps, provider classes, chains, shadow decisions |
| Tables and live signals | `tests/news/heatmap` | Every provider on recorded responses with an injected fetch; the signals stay dark |
| Clusters and the briefing | `tests/news/clusters`, `tests/news/briefing` | The URL key, the MinHash, the scorer on saved answers, the builder, the routes |
| Launches and feedback | `tests/launches`, `tests/feedback` | Submit, review, the day roll, the digest, the scrubber on every field |
| Auth and OAuth | `tests/auth`, `tests/oauth2` | Codes, sessions, factors, the bot check, the provider flow |
| Health and jobs | `tests/health`, `tests/jobs` | Every reason code, the heartbeat, the run records |
| Discipline | `tests/scripts`, `tests/test_openapi_surface.py`, `tests/test_publication_boundary.py` | The linters, the additive API surface, the boundary |

Not covered on purpose: the real upstreams (every provider is recorded or
faked), the email renderer binary (mocked in CI), and the worker's wall-clock
scheduling.

## Clients

| Area | Covered by |
| --- | --- |
| news-core | Every module has a test beside it: the deck fixture, the preference reducers and store, slots and dwell, the swipe and clip rules, muted words, link safety, the share link and its frozen tokens, editions and looks, the split-flap, holds, auto-play, the briefing helpers, the list stores |
| Web | The card header's state line, the share link builder, the deck's keyboard moves, the split-flap under reduced motion, the auto-play control on fake timers, the launch copy helpers, the changelog parser, the proxy and auth helpers, the theme swatches |
| App | The auth refresher and middleware, the news helpers, the lint rules |
| Agent tools | Every tool's limits and validation, the cached-summary rule, the installer's merges and dry run |

Not covered on purpose: pixel output (the screenshots on the rig are the
gate), gestures on a device, and the production build's runtime, which the
deploy's health gate covers.
