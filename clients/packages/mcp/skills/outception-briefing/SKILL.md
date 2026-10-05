---
name: outception-briefing
description: Work with a briefing profile: what the scores mean, how the sections are built, and how to present a ranked briefing without adding a verdict.
---

# The briefing

A briefing is built once a day per profile from the stories the wall
clustered. Each item carries a score from 0 to 10, a section, an outlet
count, the lead outlet and a one-line why.

## The scale

- 9 to 10: the day's top stories for this profile.
- 7 to 8: high; worth a line in any digest.
- 5 to 6: mid; context, not news.
- Below 5 rarely appears: a profile hides items under its minimum.

## Reading one

- `list_profiles` gives the profiles and their sections.
- `get_briefing` with a profile gives the ranked items; `builtAt` and
  `staleAfterMs` say whether it is still today's.
- Group by section when summarising; keep the ranking inside a section.
- The why line explains the score. Quote it or paraphrase it; do not add a
  judgement of your own about the story's politics or truth.
- Outlet counts and lead outlets are facts to carry over. They are not
  bias labels and must not be turned into one.

## Limits

At most forty items per call. A profile with no briefing yet says so;
do not fall back to another profile without telling the reader.
