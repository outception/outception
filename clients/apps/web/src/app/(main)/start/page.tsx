import { redirect } from 'next/navigation'

/** Where a signed-in reader lands from `/`: their wall. */
export default function Page() {
  redirect('/account/news')
}
