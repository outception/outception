<!-- doc-covers: server/outception/news/summaries/providers/own.py deploy/docker-compose.prod.yml -->
<!-- doc-verified: 06ea109 -->

# The engine profile and the checkpoint runbook

The house decision model answers the typed questions behind the briefing:
score, category, route and resolve. It runs as its own container on the
internal network, under the `engine` compose profile, and the server reaches
it through `OUTCEPTION_ENGINE_URL`. Without the profile every decision chain
ends at the model rendering, and nothing changes shape on the API.

## Routes the server expects

| Route | Purpose |
| --- | --- |
| `GET /health` | 200 when a checkpoint is loaded; the health report raises `engine_unreachable` otherwise |
| `POST /decide` | A typed question with its options; the answer carries the chosen option and a calibrated confidence |

The client (`server/outception/news/summaries/providers/own.py`) sends
`OUTCEPTION_ENGINE_API_KEY` as a bearer token and waits
`OUTCEPTION_ENGINE_TIMEOUT_S`.

## Switching it on

1. Place the checkpoint on the host: `docker volume create outception_engine_models`,
   then copy the files into `/models/current` through a throwaway container.
   A missing or partial checkpoint raises `engine_model_missing`.
2. Set `ENGINE_IMAGE` (and `ENGINE_MEMORY`) in `deploy/.env.prod`, and
   `OUTCEPTION_ENGINE_URL=http://engine:8080`, `OUTCEPTION_ENGINE_API_KEY=<key>`.
3. Start it: `docker compose --env-file .env.prod -f docker-compose.prod.yml --profile engine up -d engine`.
4. Shadow first: `OUTCEPTION_DECISION_SHADOW=true` asks the engine beside
   every rendered answer without using it, and keeps a thirty-day tally and
   a sample per task. A day of builds, then
   `python -m scripts.decisions report --task score` prints the total, the
   agreement (every chosen answer the same), the error rate, the engine's
   mean latency and the Brier score of its probabilities against the
   rendered choice (0 is perfect, lower is better).
5. Flip one task at a time: `OUTCEPTION_DECISION_CHAIN_RESOLVE=own,llm_decider`.
   The rendering stays last in every chain. Set the chain back to restore the
   previous answers; no API response changes shape either way.

## The boundary

A checkpoint reaches production the way a binary does: a named human copies
it, under the same publication boundary as the deploy. CI builds and tests
the server; it never fetches, trains or publishes a model.
