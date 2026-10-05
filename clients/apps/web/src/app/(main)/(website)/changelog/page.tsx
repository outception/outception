import {
  ChangelogPage,
  parseChangelog,
} from '@/components/Changelog/ChangelogPage'
import LandingLayout from '@/components/Landing/LandingLayout'
import { getTranslations } from '@outception-com/i18n'
import type { Metadata } from 'next'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

// Read once at build: the notes live in the app's own tree so the production
// image carries them.
export const dynamic = 'force-static'

const notes = () =>
  readFileSync(join(process.cwd(), 'content', 'changelog.md'), 'utf8')

export function generateMetadata(): Metadata {
  const strings = getTranslations().news.changelog
  return { title: strings.title, description: strings.intro }
}

export default function Page() {
  const strings = getTranslations().news.changelog
  return (
    <LandingLayout>
      <ChangelogPage releases={parseChangelog(notes())} labels={strings} />
    </LandingLayout>
  )
}
