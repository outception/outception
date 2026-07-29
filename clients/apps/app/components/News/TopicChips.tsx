import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useT } from '@/providers/LocaleProvider'
import {
  NEWS_COLUMN_KEYS,
  NEWS_GROUPED_COLUMNS,
  NEWS_TOPIC_GROUPS,
} from '@outception-com/i18n'
import type { StyleProp, ViewStyle } from 'react-native'
import { RosterChip } from './RosterRow'

const capitalize = (id: string) => id.charAt(0).toUpperCase() + id.slice(1)

/** The topic filter: six broad group chips plus a chip per column no group
 * claims. Selecting a group filters to it AND auto-expands its fine-grained
 * sub-topics in a row below (no chevrons, no floating menus — the sub-topics
 * appear exactly when they become relevant). Tapping a sub-topic narrows the
 * filter from the whole group to just that column. `topics` therefore mixes
 * group ids and column ids; SourceRoster resolves both. */
export const TopicChips = ({
  present,
  topics,
  onChange,
  rowStyle,
}: {
  /** Columns that actually occur in the source catalogue. */
  present: ReadonlySet<string>
  topics: string[]
  onChange: (topics: string[]) => void
  rowStyle?: StyleProp<ViewStyle>
}) => {
  const theme = useTheme()
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
    // "just this one" — swap the group id for the column.
    if (topics.includes(g.id))
      onChange([...topics.filter((x) => x !== g.id), c])
    else if (topics.includes(c)) onChange(topics.filter((x) => x !== c))
    else onChange([...topics, c])
  }

  // A selected group's sub-topics render below (multi-column groups only).
  const expanded = groups.filter((g) => g.columns.length > 1 && groupEngaged(g))

  return (
    <>
      <Box
        flexDirection="row"
        flexWrap="wrap"
        alignItems="center"
        gap="spacing-8"
        paddingHorizontal="spacing-12"
        paddingVertical="spacing-8"
        style={expanded.length > 0 ? undefined : rowStyle}
      >
        <Touchable onPress={() => onChange([])} disabled={topics.length === 0}>
          <Text
            variant="caption"
            color="subtext"
            style={{ opacity: topics.length === 0 ? 0.4 : 1 }}
          >
            {t('news.search.all')}
          </Text>
        </Touchable>
        <Box
          width={1}
          height={16}
          marginHorizontal="spacing-4"
          style={{ backgroundColor: theme.colors.border, opacity: 0.6 }}
        />
        {groups.map((g) => (
          <RosterChip
            key={g.id}
            label={label(g.id)}
            active={groupEngaged(g)}
            onPress={() => toggleGroup(g)}
          />
        ))}
        {orphans.map((c) => (
          <RosterChip
            key={c}
            label={label(c)}
            active={topics.includes(c)}
            onPress={() =>
              onChange(
                topics.includes(c)
                  ? topics.filter((x) => x !== c)
                  : [...topics, c],
              )
            }
          />
        ))}
      </Box>

      {expanded.map((g, i) => (
        <Box
          key={g.id}
          flexDirection="row"
          flexWrap="wrap"
          alignItems="center"
          gap="spacing-6"
          paddingLeft="spacing-24"
          paddingRight="spacing-12"
          paddingBottom="spacing-8"
          style={i === expanded.length - 1 ? rowStyle : undefined}
        >
          {g.columns.map((c) => (
            <RosterChip
              key={c}
              label={label(c)}
              // With the whole group selected every sub-topic is included;
              // narrowing lights up only the picked ones.
              active={topics.includes(g.id) || topics.includes(c)}
              onPress={() => toggleSub(g, c)}
            />
          ))}
        </Box>
      ))}
    </>
  )
}
