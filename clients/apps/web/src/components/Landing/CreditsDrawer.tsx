'use client'

import { useCredits } from '@/hooks/queries/news'
import { useT } from '@/providers/translate'
import { safeExternalHref } from '@outception-com/news-core'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@outception-com/ui/components/ui/dialog'
import { useState } from 'react'

/** The credits drawer: every upstream the tables, the weather and the live
 * cards are built on, with its terms. One data file on the server feeds
 * this and the app's settings row. */
export const CreditsDrawer = () => {
  const t = useT()
  const [open, setOpen] = useState(false)
  const { data, isLoading } = useCredits(open)
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="cursor-pointer"
      >
        <Text variant="caption" color="muted">
          {t('news.trust.credits')}
        </Text>
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="paper-search max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl border-0 p-6 text-black md:p-10 dark:text-white">
          <DialogTitle className="sr-only">
            {t('news.trust.creditsTitle')}
          </DialogTitle>
          <Box flexDirection="column" rowGap="l">
            <Box flexDirection="column" rowGap="xs">
              <Text variant="heading-xs" as="h2" serif>
                {t('news.trust.creditsTitle')}
              </Text>
              <Text variant="caption" color="muted">
                {t('news.trust.creditsIntro')}
              </Text>
            </Box>
            {isLoading ? (
              <Text variant="caption" color="muted">
                {t('news.card.loading')}
              </Text>
            ) : null}
            <Box as="ul" flexDirection="column" rowGap="m">
              {(data?.credits ?? []).map((credit) => (
                <Box
                  as="li"
                  key={credit.id}
                  flexDirection="column"
                  rowGap="none"
                >
                  <a
                    href={safeExternalHref(credit.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="headline-link"
                  >
                    <Text variant="body" as="span" serif>
                      {credit.name}
                    </Text>
                  </a>
                  <Text variant="caption" color="muted" as="span">
                    {credit.terms}
                    {' · '}
                    {t('news.trust.usedFor', { what: credit.used_for })}
                  </Text>
                </Box>
              ))}
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
    </>
  )
}
