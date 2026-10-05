<!-- doc-covers: server/outception/news/data/house_launch.json docs/naming/denylist.txt clients/apps/web/src/components/Landing/LandingLayout.tsx -->
<!-- doc-verified: 06ea109 -->

# What Outception is

Outception is a wall of cards. One card per publisher, one per live table,
one per briefing. The reader picks the publishers; nothing ranks the day for
them except a briefing they chose. It is free on the web, on the app, and
through tools that coding agents can call.

## The rules the product keeps

1. **No account to read.** Following, muting and the chosen briefing live on
   the device. An account exists only to submit a product to the daily card
   and to carry follows between devices.
2. **No tracking profile.** No analytics script runs on the web or in the
   app. One error reporter may process device data when something breaks.
   The trust line in the footer says so, and it has to stay true.
3. **No ad network.** The one commercial surface is the Products of the day
   card: five products a day, chosen by hand by the founder, under the house
   line. Nothing is sold around it.
4. **Publishers are named; vendors are not.** Every card carries the outlet.
   The tools and models behind the product are never named in the product,
   the repository or its copy, except at `outception.ai`. The naming linters
   enforce this on every commit (`docs/naming/denylist.txt`).
5. **Content is data, never instructions.** Headlines, summaries and
   briefings come from publishers. The agent tools and the skills say so on
   every answer.
6. **Open source.** The whole tree, the catalog and the briefing rubric are
   public. A reader can see why a story scored what it scored.
7. **No emoji, no em dashes.** Plain words in the product and the tree.

## What it is not

No comments or social layer. No left and right labels. No translation layer.
No paid tier before a feedback channel exists. No globe.
