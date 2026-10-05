<!-- doc-covers: clients/packages/news-core/src server/outception/cards server/outception/net/state.py -->
<!-- doc-verified: 2579d8a -->

# How the product is shaped

## Seven nouns

| Noun | What it is | Where it lives |
| --- | --- | --- |
| Catalog entry | A publisher, table or signal as data | `server/outception/news/data/*.json` |
| Card | What the reader sees: `{id, kind, meta, state, updatedAt, payload}` | server `cards/`, `news-core/card.ts` |
| Item | One headline on a feed card, with its story id and outlet count when clustered | `CardItem` |
| Cluster | One story across outlets | `news/clusters`, the story route |
| Deck | The ordered card ids for one reader | server `cards/deck.py` for the default, `news-core/deck.ts` for the reader's own |
| Reader | Preferences on the device: follows, hidden cards, Starters, profiles, switches | `news-core/prefs.ts` with the client's storage |
| Signal state | `nominal, loading, degraded, stale, fallback, unavailable`; worst wins on merge | `net/state.py`, `news-core/state.ts` |

## The deck rule

Written once and mirrored on both sides, with a shared fixture test:

1. the shared card when present, else the country card
2. the briefing card for each profile the reader follows
3. the rest in catalog order (follow order for a followed set)
4. dedupe; drop unknown, disabled, hidden and `fallback` ids; cap at 120

Products of the day is an ordinary catalog entry. There is no promoted
splice.

## One card family

Every kind shares a header: badge, name, the updated time flipping like a
departures board, and a tertiary state word when the card is in trouble.
`FeedCard`, `TableCard` and `BriefingCard` differ only in their body; the
weather strip attaches to the country and city cards. The app renders the
same descriptors from the same composer.

## Editions and looks

Five editions (midnight, tide, neon, phosphor, dune), each in both tones.
Two CSS-only looks (noir, night) over images and chrome, never over body
text. The app applies editions and ignores looks.

## The share link

`/?card=<lead>#v=1&c=<cards>&s=<story>&e=<edition>&l=<look>&k=<topic>&at=<seconds>`

The lead stays in the query for the unfurl; the hash never reaches the
server. The token registry is frozen: a token is never renamed or reused.
Restore order: theme, then cards, then the story only once the cards
applied. A shared deck is viewed as sent and never written into the
reader's own card set. `?card=` keeps working forever.

## Reader controls

One row per story by default, with the outlet count linking to the story.
Switches: every outlet, hide read, auto-play. Block a publisher from a card
or from the search palette; mute a word from a headline.
