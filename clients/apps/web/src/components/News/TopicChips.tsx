'use client'

import { useT } from '@/providers/locale'
import {
  NEWS_COLUMN_KEYS,
  NEWS_GROUPED_COLUMNS,
  NEWS_TOPIC_GROUPS,
} from '@outception-com/i18n'
import { twMerge } from 'tailwind-merge'

const capitalize = (id: string) => id.charAt(0).toUpperCase() + id.slice(1)

const chipClass = (active: boolean) =>
  twMerge(
    'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
    active
      ? 'text-white [background:var(--color-brand-700)]'
      : 'paper-hover text-gray-500 dark:text-neutral-400',
  )

/** The topic filter: six broad group chips plus a chip per column no group
 * claims. Selecting a group filters to it AND auto-expands its fine-grained
 * sub-topics in a row below; picking a sub-topic narrows the filter from the
 * whole group to just that column. `topics` therefore mixes group ids and
 * column ids; NewsSearchDialog resolves both. Mirrors the mobile TopicChips. */
export const TopicChips = ({
  present,
  topics,
  onChange,
  templatesActive = false,
  onToggleTemplates,
}: {
  present: ReadonlySet<string>
  topics: string[]
  onChange: (topics: string[]) => void
  templatesActive?: boolean
  onToggleTemplates?: () => void
}) => {
  const t = useT()

  const label = (id: string) =>
    id in NEWS_COLUMN_KEYS
      ? t(NEWS_COLUMN_KEYS[id as keyof typeof NEWS_COLUMN_KEYS])
      : capitalize(id)

  const groups = NEWS_TOPIC_GROUPS.map((g) => ({
    id: g.id as string,
    columns: g.columns.filter((c) => present.has(c)),
  })).filter((g) => g.columns.length > 0)
  const orphans = Array.from(present)
    .filter((c) => !NEWS_GROUPED_COLUMNS.has(c))
    .sort()

  const groupEngaged = (g: { id: string; columns: string[] }) =>
    topics.includes(g.id) || g.columns.some((c) => topics.includes(c))

  const toggleGroup = (g: { id: string; columns: string[] }) =>
    onChange(
      groupEngaged(g)
        ? topics.filter((x) => x !== g.id && !g.columns.includes(x))
        : [...topics, g.id],
    )

  const toggleSub = (g: { id: string; columns: string[] }, c: string) => {
    // Narrowing: with the whole group selected, picking a sub-topic means
    // "just this one" - swap the group id for the column.
    if (topics.includes(g.id))
      onChange([...topics.filter((x) => x !== g.id), c])
    else if (topics.includes(c)) onChange(topics.filter((x) => x !== c))
    else onChange([...topics, c])
  }

  const expanded = groups.filter((g) => g.columns.length > 1 && groupEngaged(g))

  return (
    <>
      <div className="rule-hairline flex flex-wrap items-center gap-1.5 px-3 py-2">
        {onToggleTemplates ? (
          // The starter-decks entry leads the row: deliberately louder than
          // the topic filters - it opens a different view, not a filter.
          <button
            type="button"
            onClick={onToggleTemplates}
            aria-pressed={templatesActive}
            className={twMerge(
              'rounded-md px-2.5 py-1 text-xs font-bold transition-colors',
              templatesActive
                ? 'text-white [background:var(--color-brand-700)]'
                : 'text-white [background:var(--color-brand-500)] hover:[background:var(--color-brand-600)]',
            )}
          >
            {t('news.templates.chip')}
          </button>
        ) : null}
        {/* Always clickable: "All" is also the way back to the full list
            from the Templates view (onChange closes it). */}
        <button
          type="button"
          onClick={() => onChange([])}
          className={chipClass(topics.length === 0 && !templatesActive)}
        >
          {t('news.search.all')}
        </button>
        <span className="ink-fill mx-1 h-4 w-px opacity-15" />
        {groups.map((g) => (
          <button
            key={g.id}
            type="button"
            onClick={() => toggleGroup(g)}
            aria-pressed={groupEngaged(g)}
            className={chipClass(groupEngaged(g))}
          >
            {label(g.id)}
          </button>
        ))}
        {orphans.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() =>
              onChange(
                topics.includes(c)
                  ? topics.filter((x) => x !== c)
                  : [...topics, c],
              )
            }
            aria-pressed={topics.includes(c)}
            className={chipClass(topics.includes(c))}
          >
            {label(c)}
          </button>
        ))}
      </div>

      {expanded.map((g) => (
        <div
          key={g.id}
          className="rule-hairline flex flex-wrap items-center gap-1 py-1.5 pr-3 pl-8"
        >
          {g.columns.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => toggleSub(g, c)}
              aria-pressed={topics.includes(g.id) || topics.includes(c)}
              className={chipClass(topics.includes(g.id) || topics.includes(c))}
            >
              {label(c)}
            </button>
          ))}
        </div>
      ))}
    </>
  )
}
