'use client'

import Link from 'next/link'
import LogoIcon from '../Brand/logos/LogoIcon'

export default function InternalServerError({ digest }: { digest?: string }) {
  // The wall's own page colour, not a sunset. A crash is the one screen a
  // reader never chose to see, so it should look like the app they were
  // already in. The literals are the default edition's page - grey by day, the
  // same grey inverted by night - and they matter: `global-error` replaces the
  // whole document, so the edition's tokens may not be there to read.
  return (
    <div className="flex h-screen w-full flex-col items-center justify-center bg-[var(--color-paper,#eeeeee)] px-12 text-center dark:bg-[var(--color-paper-night,#191617)]">
      <div className="paper-panel flex max-w-lg flex-col items-center justify-center gap-y-8 rounded-2xl px-12 py-14">
        <div className="flex flex-col items-center justify-center gap-y-1">
          <h1 className="text-2xl font-medium text-black dark:text-white">
            Something went wrong
          </h1>
          <p className="dark:text-outception-300 -mb-1 max-w-md text-center text-base text-balance text-gray-700">
            Sorry, we&rsquo;re having an issue on our end. Please try again
            later or reach out to support if the issue persists.
          </p>
        </div>
        <Link href="/" aria-label="Outception home" prefetch={false}>
          <LogoIcon className="text-black dark:text-white" size={32} />
        </Link>
        {digest && (
          <pre className="dark:text-outception-400 font-mono text-xs whitespace-break-spaces text-gray-500">
            Debugging information: {digest}
          </pre>
        )}
      </div>
    </div>
  )
}
