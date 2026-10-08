import {
  ChangelogPage,
  parseChangelog,
} from '@/components/Changelog/ChangelogPage'
import LandingLayout from '@/components/Landing/LandingLayout'
import { getTranslations } from '@outception-com/i18n'
import type { Metadata } from 'next'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

// Rendered per request like every other page: the security policy carries a
// fresh nonce each time, and a page built ahead of time has none, so its
// scripts would be refused. The notes are read and parsed once per server
// process (they live in the app's own tree, so the image carries them).
let releases: ReturnType<typeof parseChangelog> | null = null
const notes = () =>
  (releases ??= parseChangelog(
    readFileSync(join(process.cwd(), 'content', 'changelog.md'), 'utf8'),
  ))

export function generateMetadata(): Metadata {
  const strings = getTranslations().news.changelog
  return { title: strings.title, description: strings.intro }
}

export default function Page() {
  const strings = getTranslations().news.changelog
  return (
    <LandingLayout>
      <ChangelogPage releases={notes()} labels={strings} />
    </LandingLayout>
  )
}
