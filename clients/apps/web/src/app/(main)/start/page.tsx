import { redirect } from 'next/navigation'

/** Where a sign-in returns to by default: the wall, the same one for
 * everyone. The account area is reached through the person icon. */
export default function Page() {
  redirect('/')
}
