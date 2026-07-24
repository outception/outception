'use client'

import { PaperBackground } from '@/components/Layout/PaperBackground'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit'
import Link from 'next/link'
import LogoIcon from '../Brand/logos/LogoIcon'

/** 404 page. Uses the same themed newsprint backdrop as the wall
 * (`PaperBackground` → the active edition's `.paper-page` gradient), so it
 * follows the reader's edition and tone — light/dark green on the default
 * Phosphor edition — instead of a fixed colour. */
const PageNotFound = () => {
  return (
    <>
      <PaperBackground />
      <Box
        minHeight="100vh"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        paddingHorizontal="xl"
        textAlign="center"
      >
        <div className="paper-panel flex max-w-lg flex-col items-center gap-y-8 rounded-2xl px-12 py-14">
          <Box flexDirection="column" alignItems="center" rowGap="xs">
            <Text variant="heading-m" as="h1">
              Page not found
            </Text>
            <Text variant="body" color="muted">
              Sorry, but the page you&rsquo;re looking for doesn&rsquo;t exist
              or has been moved.
            </Text>
          </Box>
          <Link href="/" aria-label="Outception home" prefetch={false}>
            <LogoIcon className="text-black dark:text-white" size={32} />
          </Link>
        </div>
      </Box>
    </>
  )
}

export default PageNotFound
