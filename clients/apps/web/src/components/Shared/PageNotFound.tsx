'use client'

import Link from 'next/link'
import LogoIcon from '../Brand/logos/LogoIcon'

const PageNotFound = () => {
  return (
    <div className="flex h-screen w-full flex-col items-center justify-center bg-[radial-gradient(130%_130%_at_25%_20%,#f7ead0_0%,#e8923f_45%,#d8531f_100%)] px-12 text-center dark:bg-[radial-gradient(130%_130%_at_25%_20%,#2a1812_0%,#5a2410_45%,#0c0806_100%)]">
      <div className="glass-panel flex max-w-lg flex-col items-center justify-center gap-y-8 rounded-3xl px-12 py-14">
        <div className="flex flex-col items-center justify-center gap-y-1">
          <h1 className="text-2xl font-medium text-black dark:text-white">
            Page not found
          </h1>
          <p className="dark:text-outception-300 -mb-1 max-w-md text-center text-base text-balance text-gray-700">
            Sorry, but the page you&rsquo;re looking for doesn&rsquo;t exist or
            has been moved.
          </p>
        </div>
        <Link href="/" aria-label="Outception home" prefetch={false}>
          <LogoIcon className="text-black dark:text-white" size={32} />
        </Link>
      </div>
    </div>
  )
}

export default PageNotFound
