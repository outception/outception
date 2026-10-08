import { redirect } from 'next/navigation'

/** The wall is the public one for everyone; this address only ever led
 * to a second copy of it. */
export default function Page() {
  redirect('/')
}
