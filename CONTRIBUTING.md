# Contributing

## Issues before pull requests

Unless the change is a minor fix, an issue must exist and be assigned to you
before you open a pull request. This keeps work aligned with the roadmap and
avoids two people solving the same problem.

1. Find or open an issue describing the bug or feature.
2. Comment on it to ask for assignment.
3. Start work once a maintainer assigns you.

### Minor fixes

Allowed without an issue:

- Typos in documentation, comments or error messages
- Broken links
- Formatting (indentation, whitespace)
- Outdated version numbers in documentation

Everything else needs an issue: logic changes of any size, new dependencies,
API behaviour, database schema or migrations, UI changes, performance work,
security-related changes, configuration changes.

## Testing

Every change must be run and tested in a local environment before submission.
Run the existing tests, add tests for new behaviour, and confirm the app starts
with your change applied. Pull requests that were clearly not executed locally
are closed.

## Development setup

See [`DEVELOPMENT.md`](./DEVELOPMENT.md).

## Code style

- Descriptive names over comments. Comment only what the code cannot say.
- Touch only the code your issue requires.
- Follow the patterns already in the surrounding code.

### Backend (Python, FastAPI)

- Lint: `uv run task lint && uv run task lint_types`
- Tests: `uv run task test`
- Module layout follows `server/outception/`
- Imports at the top of the file
- Async code uses `async`/`await` throughout

### Frontend (TypeScript, Next.js, React)

- Package manager: `pnpm`
- Shared components come from `clients/packages/ui`
- Styling: Tailwind CSS

## Review

1. Automated checks (lint, type check, tests) must pass.
2. Maintainers review for correctness, security, performance and consistency
   with the existing architecture.
3. Address review feedback; squash commits before merge if asked.

Not accepted: pull requests without an issue (except minor fixes), untested
changes, changes that break existing behaviour, large refactors without prior
discussion, and changes that diverge from the project goals.

## License

Contributions are licensed under the project license.
