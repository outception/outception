import { redirect } from 'next/navigation'

/** The account's front door: the reader's own products. */
export default function Page() {
  return redirect('/launches/mine')
}
