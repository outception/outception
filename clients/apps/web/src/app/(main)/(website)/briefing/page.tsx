import { redirect } from 'next/navigation'

/** The house default briefing; the pill links to the reader's own. */
export default function Page() {
  redirect('/briefing/news-junkie')
}
