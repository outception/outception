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
6. `mv live live-backup-<date> && mv rebuilt live`. Carry over the server
   env, the testing env, the keypair, the production env, the web env files,
   the app env, the sync file and the plan files. Point the remote at the
   repository and push.
7. Deploy through the deploy workflow; the migrate service brings the
   schema to head; then the import with `--commit` against the production
   database; then the verification items.

## Rollback

Stop the new compose stack and start the old one from the backup directory
against the untouched old database and cache. The old database is never
migrated or written by the new tree. Keep the backup until two clean weeks
have passed.
