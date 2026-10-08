# Security and vulnerability reporting

Outception keeps very little about its readers on purpose: no tracking
profile, no account to read, device-local preferences. What it does hold
(accounts that submit products, the follows of a signed-in reader, the
feedback people send) deserves care, and so does the product itself.

## Making a report

Report a vulnerability privately through the repository's security advisory
form at <https://github.com/outception/outception/security/advisories/new>.
Include:

- a clear summary of the issue and its potential impact
- the steps to reproduce it
- the environment (browser, OS, app version)
- a proof of concept when you have one

You will hear back within a few days. Please give us reasonable time to fix
the issue before you talk about it in public.

## What matters most

- Authentication bypass and privilege escalation.
- Exposure of personal data: an email address, a submitted product's contact,
  the sender of a feedback message.
- Anything that lets a reader see or change another reader's follows.
- Server-side requests to arbitrary hosts through a submitted link or a feed.
- Injection through publisher content: a headline or summary that changes
  what the product or the agent tools do.

## Out of scope

- Rate limits on public endpoints working as documented.
- Content published by the outlets themselves.
- Reports from automated scanners without a working reproduction.

## Secrets

Secrets live only in `.env` files and the host's `deploy/secrets/`; a
scanner runs on every push. If you find one in the tree or its history, treat
it as a vulnerability and report it the same way.
