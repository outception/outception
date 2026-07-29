'use client'

import { useNewsTemplates } from '@/hooks/queries/news'
import { useT } from '@/providers/locale'
import type { NewsSourceMeta, NewsTemplate } from '@/utils/news'
import { Check } from 'lucide-react'
import { useMemo, useSyncExternalStore } from 'react'
import {
  followAll,
  getActiveTemplatesServerSnapshot,
  getActiveTemplatesSnapshot,
  replaceAll,
  setActiveTemplates,
  subscribe,
  unfollowAll,
} from './newsPrefsStore'
import { SourceBadge } from './SourceBadge'

const PREVIEW_BADGES = 6

// Explicit key maps keep t() fully typed against the locale schema - the API
// only ships template ids.
const NAME_KEYS = {
  developer: 'news.templates.names.developer',
  investor: 'news.templates.names.investor',
  'news-junkie': 'news.templates.names.news-junkie',
  'sports-fan': 'news.templates.names.sports-fan',
  'movie-buff': 'news.templates.names.movie-buff',
  'music-lover': 'news.templates.names.music-lover',
  gamer: 'news.templates.names.gamer',
  'science-nerd': 'news.templates.names.science-nerd',
  'foodie-traveler': 'news.templates.names.foodie-traveler',
  'comedy-fun': 'news.templates.names.comedy-fun',
  'fitness-buff': 'news.templates.names.fitness-buff',
  fashionista: 'news.templates.names.fashionista',
  petrolhead: 'news.templates.names.petrolhead',
  'crypto-trader': 'news.templates.names.crypto-trader',
  'space-explorer': 'news.templates.names.space-explorer',
  'ai-insider': 'news.templates.names.ai-insider',
  'true-crime': 'news.templates.names.true-crime',
  'history-buff': 'news.templates.names.history-buff',
  bookworm: 'news.templates.names.bookworm',
  'pop-culture': 'news.templates.names.pop-culture',
  'esports-fan': 'news.templates.names.esports-fan',
  outdoors: 'news.templates.names.outdoors',
  'anime-manga': 'news.templates.names.anime-manga',
  'football-fan': 'news.templates.names.football-fan',
  'cricket-fan': 'news.templates.names.cricket-fan',
  'fight-fan': 'news.templates.names.fight-fan',
  'deal-hunter': 'news.templates.names.deal-hunter',
  'personal-finance': 'news.templates.names.personal-finance',
  founder: 'news.templates.names.founder',
  'home-garden': 'news.templates.names.home-garden',
  photographer: 'news.templates.names.photographer',
  academia: 'news.templates.names.academia',
  researcher: 'news.templates.names.researcher',
  'clean-energy': 'news.templates.names.clean-energy',
  'my-country': 'news.templates.names.my-country',
} as const

const BLURB_KEYS = {
  developer: 'news.templates.blurbs.developer',
  investor: 'news.templates.blurbs.investor',
  'news-junkie': 'news.templates.blurbs.news-junkie',
  'sports-fan': 'news.templates.blurbs.sports-fan',
  'movie-buff': 'news.templates.blurbs.movie-buff',
  'music-lover': 'news.templates.blurbs.music-lover',
  gamer: 'news.templates.blurbs.gamer',
  'science-nerd': 'news.templates.blurbs.science-nerd',
  'foodie-traveler': 'news.templates.blurbs.foodie-traveler',
  'comedy-fun': 'news.templates.blurbs.comedy-fun',
  'fitness-buff': 'news.templates.blurbs.fitness-buff',
  fashionista: 'news.templates.blurbs.fashionista',
  petrolhead: 'news.templates.blurbs.petrolhead',
  'crypto-trader': 'news.templates.blurbs.crypto-trader',
  'space-explorer': 'news.templates.blurbs.space-explorer',
  'ai-insider': 'news.templates.blurbs.ai-insider',
  'true-crime': 'news.templates.blurbs.true-crime',
  'history-buff': 'news.templates.blurbs.history-buff',
  bookworm: 'news.templates.blurbs.bookworm',
  'pop-culture': 'news.templates.blurbs.pop-culture',
  'esports-fan': 'news.templates.blurbs.esports-fan',
  outdoors: 'news.templates.blurbs.outdoors',
  'anime-manga': 'news.templates.blurbs.anime-manga',
  'football-fan': 'news.templates.blurbs.football-fan',
  'cricket-fan': 'news.templates.blurbs.cricket-fan',
  'fight-fan': 'news.templates.blurbs.fight-fan',
  'deal-hunter': 'news.templates.blurbs.deal-hunter',
  'personal-finance': 'news.templates.blurbs.personal-finance',
  founder: 'news.templates.blurbs.founder',
  'home-garden': 'news.templates.blurbs.home-garden',
  photographer: 'news.templates.blurbs.photographer',
  academia: 'news.templates.blurbs.academia',
  researcher: 'news.templates.blurbs.researcher',
  'clean-energy': 'news.templates.blurbs.clean-energy',
  'my-country': 'news.templates.blurbs.my-country',
} as const

type TemplateId = keyof typeof NAME_KEYS

/** One starter-deck card: name, blurb, a strip of source logos and a one-tap
 * "Follow all". Fully followed templates show a check instead. */
const TemplateCard = ({
  template,
  bySourceId,
  active,
  onToggle,
}: {
  template: NewsTemplate
  bySourceId: Map<string, NewsSourceMeta>
  active: boolean
  onToggle: () => void
}) => {
  const t = useT()
  const sources = template.sources
    .map((sid) => bySourceId.get(sid))
    .filter((s): s is NewsSourceMeta => Boolean(s))
  if (sources.length === 0) return null
  const nameKey = NAME_KEYS[template.id as TemplateId]
  const blurbKey = BLURB_KEYS[template.id as TemplateId]
  if (!nameKey || !blurbKey) return null
  // Newsprint idiom like the source/language rows: hairline-ruled sections
  // on the shared paper, serif names, meta-kicker micro-labels - no card
  // boxes inside the glass dialog.
  return (
    <div className="rule-hairline paper-hover flex flex-col gap-1.5 px-4 py-3">
      <div className="flex items-center gap-2">
        <span className="font-serif text-black dark:text-white">
          {t(nameKey)}
        </span>
        <span className="meta-kicker ml-auto">
          {t('news.templates.sourceCount', { count: sources.length })}
        </span>
      </div>
      <span className="text-xs text-gray-500 dark:text-neutral-400">
        {t(blurbKey)}
      </span>
      <div className="mt-1 flex items-center gap-2">
        <span className="inline-flex items-center gap-1">
          {sources.slice(0, PREVIEW_BADGES).map((s) => (
            <SourceBadge
              key={s.id}
              id={s.id}
              name={s.name}
              logo={s.logo}
              size={22}
            />
          ))}
          {sources.length > PREVIEW_BADGES ? (
            <span className="meta-kicker">
              +{sources.length - PREVIEW_BADGES}
            </span>
          ) : null}
        </span>
        <button
          type="button"
          onClick={onToggle}
          aria-pressed={active}
          className="ml-auto inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-semibold text-white transition-colors [background:var(--color-brand-700)] hover:[background:var(--color-brand-800)]"
        >
          {active ? (
            <>
              <Check className="h-3.5 w-3.5" />
              {t('news.templates.inDeck', { count: sources.length })}
            </>
          ) : (
            t('news.templates.followAll', { count: sources.length })
          )}
        </button>
      </div>
    </div>
  )
}

/** The Templates view inside the Sources dialog: every persona bundle the
 * server resolved for this visitor's country. */
export const TemplateGallery = ({
  sources,
  open,
}: {
  sources: NewsSourceMeta[]
  open: boolean
}) => {
  const t = useT()
  const { data } = useNewsTemplates(open)
  const active = useSyncExternalStore(
    subscribe,
    getActiveTemplatesSnapshot,
    getActiveTemplatesServerSnapshot,
  )
  const bySourceId = useMemo(
    () => new Map(sources.map((s) => [s.id, s])),
    [sources],
  )
  const templates = useMemo(() => data?.templates ?? [], [data?.templates])
  // Union of every deck's resolvable sources - what "Select all" follows and
  // "Deselect all" unfollows, with the template toggles kept in sync.
  const allSourceIds = useMemo(
    () =>
      Array.from(new Set(templates.flatMap((tpl) => tpl.sources))).filter(
        (sid) => bySourceId.has(sid),
      ),
    [templates, bySourceId],
  )
  // Templates are combinable toggles: the FIRST one replaces the deck, extra
  // ones union in, and toggling one off removes its sources - except those a
  // still-active template also claims.
  const toggle = (template: NewsTemplate) => {
    if (active.includes(template.id)) {
      const remaining = active.filter((id) => id !== template.id)
      const kept = new Set(
        templates
          .filter((other) => remaining.includes(other.id))
          .flatMap((other) => other.sources),
      )
      unfollowAll(template.sources.filter((sid) => !kept.has(sid)))
      setActiveTemplates(remaining)
    } else {
      if (active.length === 0) replaceAll(template.sources)
      else followAll(template.sources)
      setActiveTemplates([...active, template.id])
    }
  }
  return (
    <div className="flex flex-col">
      <div className="rule-hairline flex flex-col px-4 py-2">
        <span className="font-serif text-black dark:text-white">
          {t('news.templates.title')}
        </span>
        <span className="text-xs text-gray-500 dark:text-neutral-400">
          {t('news.templates.subtitle')}
        </span>
      </div>
      {/* The same select/deselect-all pair the source list shows, acting on
          every deck at once. */}
      <div className="rule-hairline flex items-center gap-3 px-3 py-1.5">
        <button
          type="button"
          onClick={() => {
            followAll(allSourceIds)
            setActiveTemplates(templates.map((tpl) => tpl.id))
          }}
          disabled={allSourceIds.length === 0}
          className="rounded-full px-2 py-1 text-xs font-medium text-gray-500 transition-colors hover:text-black active:text-white active:[background:var(--color-brand-700)] disabled:opacity-40 dark:text-neutral-400 dark:hover:text-white"
        >
          {t('news.search.selectAll')}
        </button>
        <button
          type="button"
          onClick={() => {
            unfollowAll(allSourceIds)
            setActiveTemplates([])
          }}
          disabled={allSourceIds.length === 0}
          className="rounded-full px-2 py-1 text-xs font-medium text-gray-500 transition-colors hover:text-black active:text-white active:[background:var(--color-brand-700)] disabled:opacity-40 dark:text-neutral-400 dark:hover:text-white"
        >
          {t('news.search.deselectAll')}
        </button>
        <span className="meta-kicker ml-auto">{allSourceIds.length}</span>
      </div>
      {templates.map((template) => (
        <TemplateCard
          key={template.id}
          template={template}
          bySourceId={bySourceId}
          active={active.includes(template.id)}
          onToggle={() => toggle(template)}
        />
      ))}
    </div>
  )
}
