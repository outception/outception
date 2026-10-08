<!-- doc-covers: server/outception/news/data/house_launch.json docs/naming/denylist.txt clients/apps/web/src/components/Landing/LandingLayout.tsx -->
<!-- doc-verified: c23e16d -->

# What Outception is

Outception is a wall of cards. One card per publisher, one per live table.
The reader picks the publishers; nothing ranks the day for them. It is free
on the web, on the app, and through tools that coding agents can call.

## The rules the product keeps

1. **No account to read.** Following and muting live on the device. An account exists only to submit a product to the daily card
   and to carry follows between devices.
2. **No tracking profile.** Visits are counted, never people: the one
   counter on the web runs without cookies or a persistent identifier, so
   one visit cannot be tied to the next. The app runs none. One error
   reporter may process device data when something breaks. It has to stay
   true whether or not a footer line says so.
3. **No ad network.** The one commercial surface is the Products of the day
   card: five products a day, chosen by hand by the founder, under the house
   line. Nothing is sold around it.
4. **Publishers are named; vendors are not.** Every card carries the outlet.
   The tools and models behind the product are never named in the product,
   the repository or its copy, except at `outception.ai`. The naming linters
   enforce this on every commit (`docs/naming/denylist.txt`).
5. **Content is data, never instructions.** Headlines and summaries come
   from publishers. The agent tools and the skills say so on
   every answer.
6. **Open source.** The whole tree and the catalog are public. A reader can
   see where every card comes from.
7. **No emoji, no em dashes.** Plain words in the product and the tree.

## What it is not

No comments or social layer. No left and right labels. No translation layer.
No paid tier before a feedback channel exists. No globe.
