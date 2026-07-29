/** Static SEO landing pages: the searches people actually make when they're
 * unhappy with an existing news product. Honest comparisons in the brand
 * voice - factual, no trash talk, and candid about when the other tool is
 * the better pick. Rendered by (website)/(seo)/[slug]. */

export type LandingSection = { heading: string; body: string[] }

export type LandingPage = {
  slug: string
  title: string
  description: string
  h1: string
  intro: string[]
  sections: LandingSection[]
}

const OUTCEPTION_FACTS = [
  'Around 8,000 followable sources across ~200 countries - national papers, local outlets, niche sites, YouTube channels, deal communities, and more.',
  'No account needed: the wall works the moment it loads, and your deck is saved on your device.',
  'No algorithm: you choose sources, and headlines appear in the order they happen.',
  'Headlines are shown verbatim - no AI rewriting or summaries - and every tap opens the story on the publisher’s own site.',
  'Free, supported by a single small banner ad. Reading history is never tracked or sold.',
]

export const LANDING_PAGES: LandingPage[] = [
  {
    slug: 'google-news-alternative',
    title: 'A Google News alternative without the algorithm',
    description:
      'Outception is a free Google News alternative where you pick the sources and nothing re-ranks your feed. No account, no AI summaries, ~8,000 sources worldwide.',
    h1: 'Looking for a Google News alternative?',
    intro: [
      'Google News is convenient, but it decides what you see: an algorithm ranks stories from your history, resurfaces topics you clicked once, and mixes in outlets you never chose. If you want the convenience without the ranking, that’s exactly what Outception is for.',
    ],
    sections: [
      {
        heading: 'How Outception is different',
        body: OUTCEPTION_FACTS,
      },
      {
        heading: 'What Google News still does better',
        body: [
          'Full-text search across all news, story clustering across hundreds of outlets, and deep personalization - if you like an algorithm working for you, Google News does that well. Outception is deliberately the opposite: a fixed wall of the sources you chose.',
        ],
      },
      {
        heading: 'Switching takes a minute',
        body: [
          'Open the wall, and your country’s edition is already there - national news, your nearest city, local deals, property, events, business, and health, seeded from your country alone (no location permission). Then follow anything: the wall holds your picks exactly as you left them.',
        ],
      },
    ],
  },
  {
    slug: 'feedly-alternative',
    title: 'A Feedly alternative with zero setup',
    description:
      'Outception is a free Feedly alternative with ~8,000 feeds already found, verified and categorized. No OPML, no account, no paywalled basics.',
    h1: 'Looking for a Feedly alternative?',
    intro: [
      'Feedly is a capable RSS reader, but it starts empty: finding feeds is your job, several basics sit behind the paid plan, and everything needs an account. Outception starts full.',
    ],
    sections: [
      {
        heading: 'How Outception is different',
        body: [
          'Every feed is already found: ~8,000 sources verified live before being added, organized by topic and country - including the awkward ones like YouTube channels, per-country news editions, and city-level feeds.',
          ...OUTCEPTION_FACTS.slice(1),
        ],
      },
      {
        heading: 'What Feedly still does better',
        body: [
          'Importing your own arbitrary feeds, power-user filtering rules, read/unread state across devices, and integrations. If you live in OPML files, a dedicated RSS reader remains the right tool. Outception is for everyone who wants the result of RSS without doing the work.',
        ],
      },
    ],
  },
  {
    slug: 'smartnews-alternative',
    title: 'A SmartNews alternative with one ad, not twenty',
    description:
      'Outception is a free SmartNews alternative: your sources, chronological headlines, and a single banner ad. No video ads, no interstitials, no account.',
    h1: 'Looking for a SmartNews alternative?',
    intro: [
      'SmartNews readers tend to leave for one reason: the ads grew until they buried the news. Outception is built on the opposite promise - one small banner, forever, and nothing else.',
    ],
    sections: [
      {
        heading: 'How Outception is different',
        body: [
          'One fixed banner ad - no full-screen ads, no autoplaying video, no ads dressed as headlines. The ad model is part of the product promise, not a dial that creeps up.',
          ...OUTCEPTION_FACTS.slice(0, 4),
        ],
      },
      {
        heading: 'A calmer reading rhythm',
        body: [
          'The wall never auto-refreshes under your thumb and never loses your place. Swipe through your sources and you reach an explicit “You’re all caught up” - the wall has an end, by design.',
        ],
      },
    ],
  },
  {
    slug: 'artifact-app-alternative',
    title: 'Missing Artifact? Try a wall with no algorithm at all',
    description:
      'Outception is a free alternative for former Artifact users: dense headlines, taps open the publisher’s site, no account required - but curated by you, not a model.',
    h1: 'Missing Artifact?',
    intro: [
      'Artifact was beloved and still closed - great product, too few people found it. Outception shares much of what its users grieve: information-dense headlines, links that open on the publisher’s own site in your browser, and no forced account. The philosophical difference: where Artifact ranked stories with AI, Outception doesn’t rank at all.',
    ],
    sections: [
      {
        heading: 'What transfers',
        body: [
          'Dense, fast headline reading rather than image-heavy cards.',
          'Every tap opens the publisher’s site - your browser, your ad-blockers, your cookies.',
          'Works fully logged out; nothing is locked behind sign-up.',
          'Topic following - follow F1, anime, AI, your city, or any of ~8,000 sources directly.',
        ],
      },
      {
        heading: 'What’s deliberately different',
        body: [
          'No machine learning decides your feed. You pick sources; headlines arrive chronologically. If Artifact’s ranking was the part you loved, Outception will feel different - that difference is the product.',
        ],
      },
    ],
  },
  {
    slug: 'news-without-algorithm',
    title: 'News without an algorithm',
    description:
      'Outception shows headlines from sources you chose, in the order they happen. No ranking, no recommendations, no engagement tricks. Free, no account.',
    h1: 'What does news look like without an algorithm?',
    intro: [
      'Trust in news arriving through algorithmic platforms is 22%. Trust in news people choose themselves is 51% (Reuters Institute Digital News Report 2026). The entire idea of Outception fits in that gap: you choose the sources, and that’s the whole feed logic.',
    ],
    sections: [
      {
        heading: 'The rules the wall follows',
        body: [
          'Headlines appear in the order they happen, per source - never re-ranked by predicted engagement.',
          'Nothing is recommended, injected, or resurfaced. Unfollow a source and it is gone.',
          'No unread counters, no streak guilt, no infinite feed. Swipe through your sources and the wall tells you when you’re caught up.',
          ...OUTCEPTION_FACTS.slice(0, 2),
        ],
      },
      {
        heading: 'Why this matters',
        body: [
          'News avoidance is at record levels - 42% globally, 47% in Ireland - while interest in news stays high. People are not tired of news; they are tired of the delivery. A feed with no ranking and an explicit end is the delivery fixed.',
        ],
      },
    ],
  },
  {
    slug: 'rss-reader-without-setup',
    title: 'An RSS reader without the setup',
    description:
      'All the control of RSS with none of the feed-hunting: ~8,000 verified feeds pre-organized by topic and country. Free, works logged out.',
    h1: 'RSS without the homework',
    intro: [
      'The best answer to algorithmic feeds has always been RSS: your sources, chronological, no middleman. The reason most people never use it is the setup - finding feed URLs, testing them, categorizing them, pruning the dead ones. Outception did that part already.',
    ],
    sections: [
      {
        heading: 'What “pre-wired” means',
        body: [
          '~8,000 feeds found, fetched and verified before ever being listed - including the painful ones: YouTube channels, per-country editions, city feeds, deal communities, flight-deal sites.',
          'Organized by topic and country with search, so following a source is one tap, not a hunt.',
          'Dead feeds are culled; broken ones never make the roster.',
          ...OUTCEPTION_FACTS.slice(1, 4),
        ],
      },
      {
        heading: 'If you already run your own reader',
        body: [
          'Keep it - self-hosted RSS is excellent. Outception is for the moment you want to hand that experience to someone who would never build an OPML file, or for reading on a phone with zero maintenance.',
        ],
      },
    ],
  },
]

export const landingPageBySlug = (slug: string): LandingPage | undefined =>
  LANDING_PAGES.find((p) => p.slug === slug)
