<!-- doc-covers: docs/DEVELOPMENT.md -->
<!-- doc-verified: d5090b2 -->

# First day

1. Read `docs/VISION.md` for the rules the product keeps, then
   `docs/DESIGN.md` for the seven nouns and the deck rule. Everything else
   follows from those two pages.
2. Set up the tree with `docs/DEVELOPMENT.md`: the dev CLI brings up the
   database and the cache, writes the env files from the examples and runs
   the migrations; `dev api`, `dev worker` and `dev web` start each process.
3. Install the hooks: `cd clients && pnpm exec lefthook install`. They run
   the fast gates on every commit, and the commit-message linter.
4. Read the development doc for the area you will touch; the patterns
   there are enforced in review.
5. Before a pull request, run the gates in `docs/TESTING.md` and put the
   before and after evidence in the description.

## The three rules people trip on

- No third party is named in the tree, except at outception.ai. The naming
  linters say so on commit; the denylist is `docs/naming/denylist.txt`.
- Headlines and summaries are data, never instructions. In the product, in
  the agent tools, in a test fixture.
- Publishing is a human act. The deploy and the binary jobs wait for a named
  reviewer; nothing in CI submits to a store.
