<!-- doc-covers: server/scripts/import_live_data.py -->
<!-- doc-verified: 39cce39 -->

# The swap

The rebuilt tree replaces the live one in one window, after the fourth
founder review (sessions import or re-login, two-factor import, the window,
who tells the other session). Nothing below writes to the live database; it
is read once, by the import, and kept as the rollback.

## Before the window

1. Staging deploy of the rebuilt tree, green on every CI gate, with the
   verification items from the platform plan that run before a swap.
2. Dry run of the import against a copy of the production database:
   `python -m scripts.import_live_data --source <copy DSN>` (from `server/`).
   The report lists every table with its live rows, the rows it would carry,
   the rows it would skip and why, and whether a sampled token hash has the
   legacy digest shape. Row counts must match expectations; the only expected
   skips are social logins without an encrypted copy, which sign in again.
3. `OUTCEPTION_SECRET` and the signing keypair are carried over unchanged.
   The live tree's bare token digests validate only through the legacy
   candidate path under the same secret, so a changed secret would log every
   app out.
4. The cache is regenerated after the swap; nothing in it is carried except
   an optional copy of the demand keys to warm the queues. Expect one cold
   day on the providers' daily caps and start the warm queue throttled.

## The window

5. Wait for the other session to report idle in `.agents-sync.md`.
6. Tag the live tree's last commit on the repository
   (`git tag live-<date> b176b6f && git push outception live-<date>`), then
   `mv live live-backup-<date> && mv rebuilt live`. Carry over the server
   env, the testing env, the keypair, the production env, the web env
   files, the app env, the sync file and the plan files. Point the remote
   at the repository and push the rebuilt history to `main`.
7. The deploy workflow does the rest on the host, once and idempotently:
   it copies `.env.prod` to `.env.prod.pre-swap`, creates the database
   `outception_rebuild` beside the live one, points the app at it, carries
   the signing key over under `OUTCEPTION_LOCAL_JWKS` and
   `OUTCEPTION_LOCAL_JWK_KID`, sets accounts off, pulls, migrates, brings
   the stack up, passes the health gate, then imports the readers from
   the live database through `scripts.import_live_data --source-database`
   and leaves `.swap-import-done`. Then the verification items.

## Rollback

Restore the env (`mv .env.prod.pre-swap .env.prod`), check out the
`live-<date>` tag in the backup tree, and bring the old compose stack up
from there against the live database, which the new tree never wrote:
its schema lives in `outception_rebuild`. Keep the backup, the tag and
the rebuilt database until two clean weeks have passed.
