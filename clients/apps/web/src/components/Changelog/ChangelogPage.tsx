import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import Link from 'next/link'

export interface ChangelogRelease {
  heading: string
  lines: string[]
  notes: string[]
}

/** The release notes as `## ` sections with `- ` lines, nothing more. */
export const parseChangelog = (markdown: string): ChangelogRelease[] => {
  const releases: ChangelogRelease[] = []
  let current: ChangelogRelease | null = null
  for (const raw of markdown.split('\n')) {
    const line = raw.trimEnd()
    if (line.startsWith('## ')) {
      current = { heading: line.slice(3).trim(), lines: [], notes: [] }
      releases.push(current)
    } else if (current && line.startsWith('- ')) {
      current.lines.push(line.slice(2).trim())
    } else if (current && line.trim() && !line.startsWith('#')) {
      current.notes.push(line.trim())
    }
  }
  return releases
}

export const ChangelogPage = ({
  releases,
  labels,
}: {
  releases: ChangelogRelease[]
  labels: { title: string; intro: string; back: string }
}) => (
  <Box justifyContent="center" paddingHorizontal="l" paddingVertical="3xl">
    <Box
      as="article"
      flexDirection="column"
      rowGap="xl"
      maxWidth={720}
      width="100%"
    >
      <Box flexDirection="column" rowGap="s">
        <Text variant="heading-m" as="h1" serif>
          {labels.title}
        </Text>
        <Text color="muted">{labels.intro}</Text>
      </Box>
      {releases.map((release) => (
        <Box
          as="section"
          key={release.heading}
          flexDirection="column"
          rowGap="s"
        >
          <Text variant="heading-xs" as="h2" serif>
            {release.heading}
          </Text>
          {release.notes.map((note) => (
            <Text key={note.slice(0, 32)} color="muted">
              {note}
            </Text>
          ))}
          <Box as="ul" flexDirection="column" rowGap="xs">
            {release.lines.map((line) => (
              <Box as="li" key={line.slice(0, 48)} display="block">
                <Text>{line}</Text>
              </Box>
            ))}
          </Box>
        </Box>
      ))}
      <Link href="/" className="headline-link">
        <Text variant="caption" as="span">
          {labels.back}
        </Text>
      </Link>
    </Box>
  </Box>
)
