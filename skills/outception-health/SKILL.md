---
name: outception-health
description: Read the Outception health report, what each reason code means, and the remedy that goes with it. Reads never trigger work.
---

# The health report

`GET /health` returns the service's state with a list of reasons. Every
reason carries a stable code, a subsystem, a severity, a detail line, a
remedy and the time it was first observed. Reading it never starts a job.

## Severities

- `critical`: the product is wrong for readers now. Act first.
- `warning`: a lane is limping; readers may see stale cards. Act today.
- `info`: a condition that clears itself. Note it, do not act.

Reasons at `info` and `warning` clear on their own three minutes after the
condition ends.

## The codes

| Code | Subsystem | Severity | Remedy |
| --- | --- | --- | --- |
| `postgres_unreachable` | db | critical | check the compose db service and its disk |
| `redis_unreachable` | cache | critical | check the compose redis service |
| `worker_heartbeat_stale` | worker | critical | restart the worker; check the scheduler log |
| `llm_lane_disabled` | summaries | critical | rotate the key or clear `LLM_DISABLED` |
| `llm_chain_exhausted` | summaries | warning | wait for cooldowns; check `net:cooldown:*`; raise caps if sustained |
| `feed_poller_backlog` | news | warning | check provider cooldowns; raise worker concurrency |
| `briefing_build_stale` | briefing | warning | run `scripts/briefing.py build` |
| `scoring_null_rate_high` | briefing | warning | check provider health; inspect `job_runs` |
| `engine_unreachable` | decisions | warning | start the engine profile or clear `ENGINE_URL`; chains fall back |
| `engine_model_missing` | decisions | warning | deploy a checkpoint per the runbook |
| `table_provider_cooling` | tables | info | none; clears itself |
| `scrub_version_lag` | publishing | info | none; clears as reads re-scrub |

## How to use it

1. Read `/health` and list the reasons by severity, critical first.
2. For each, give the code, how long it has been observed and the remedy
   as written. Do not invent a remedy the report does not carry.
3. A healthy report has no reasons. Say so in one line.
4. Never run a remedy yourself through these tools: they are read-only.
   Hand the remedy to the operator.
